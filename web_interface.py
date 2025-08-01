#!/usr/bin/env python3
"""
DST Submittals Generator - Web Interface

A Flask-based web interface for the DST Submittals Generator that allows
users to upload files via drag-and-drop and configure processing options.
"""

import os
import sys
import json
import shutil
import tempfile
import zipfile
import threading
import time
import signal
import atexit
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from queue import Queue

from flask import Flask, render_template, request, jsonify, send_file, session, Response
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logger import (get_logger, set_correlation_id, log_file_upload, log_tag_extraction, 
                        log_pdf_structure, log_file_conversion, log_json_snapshot, 
                        log_file_manifest, log_processing_stage)
from src.config import Config
from src.exceptions import DSTError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dst-submittals-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

logger = get_logger('web_interface')

# Global variables for server management
server_thread = None
progress_manager = None
shutdown_event = threading.Event()
active_processes = []

def cleanup_server():
    """Clean up server resources on shutdown"""
    global progress_manager, active_processes
    
    logger.info("Starting server cleanup...")
    
    # Signal shutdown to all components
    shutdown_event.set()
    
    # Clean up progress manager
    if progress_manager:
        logger.info("Cleaning up progress manager...")
        try:
            # Close all client queues
            for correlation_id in list(progress_manager.clients.keys()):
                progress_manager.complete_operation(correlation_id, False, 
                                                  "Server shutting down")
        except Exception as e:
            logger.warning(f"Error cleaning up progress manager: {e}")
    
    # Wait for active processes to complete or force cleanup
    if active_processes:
        logger.info(f"Waiting for {len(active_processes)} active processes to complete...")
        start_time = time.time()
        timeout = 30  # 30 seconds timeout
        
        while active_processes and (time.time() - start_time) < timeout:
            time.sleep(0.5)
            # Remove completed processes
            active_processes[:] = [p for p in active_processes if p.is_alive()]
            
        # Force terminate remaining processes
        for process in active_processes:
            if process.is_alive():
                logger.warning(f"Force terminating process: {process.name}")
                try:
                    process.terminate()
                    process.join(timeout=5)
                except Exception as e:
                    logger.error(f"Error terminating process: {e}")
    
    # Clean up temporary directories
    try:
        temp_base = tempfile.gettempdir()
        for item in os.listdir(temp_base):
            if item.startswith('dst_web_'):
                temp_dir = os.path.join(temp_base, item)
                if os.path.isdir(temp_dir):
                    logger.info(f"Cleaning up temp directory: {temp_dir}")
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        logger.warning(f"Could not remove temp directory {temp_dir}: {e}")
    except Exception as e:
        logger.warning(f"Error during temp directory cleanup: {e}")
    
    logger.info("Server cleanup completed")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name} ({signum}), initiating graceful shutdown...")
    
    cleanup_server()
    
    logger.info("Graceful shutdown complete")
    sys.exit(0)

# Register signal handlers for graceful shutdown
if os.name != 'nt':  # Unix/Linux systems
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
else:  # Windows systems
    signal.signal(signal.SIGINT, signal_handler)
    # Windows doesn't support SIGTERM the same way
    try:
        signal.signal(signal.SIGTERM, signal_handler)
    except ValueError:
        pass  # SIGTERM may not be available on Windows

# Register cleanup function to run on normal exit
atexit.register(cleanup_server)

class ProgressManager:
    """Manages real-time progress updates for processing operations"""
    
    def __init__(self):
        self.progress_data = {}
        self.clients = {}
        
    def start_operation(self, correlation_id: str) -> None:
        """Initialize progress tracking for an operation"""
        self.progress_data[correlation_id] = {
            'step': 'initializing',
            'progress': 0,
            'message': 'Starting operation...',
            'details': [],
            'start_time': time.time(),
            'current_file': None,
            'files_processed': 0,
            'total_files': 0,
            'errors': []
        }
        self.clients[correlation_id] = Queue()
        
    def update_progress(self, correlation_id: str, step: str, progress: int, 
                       message: str, details: str = None, current_file: str = None) -> None:
        """Update progress for an operation"""
        if correlation_id not in self.progress_data:
            return
            
        data = self.progress_data[correlation_id]
        data.update({
            'step': step,
            'progress': min(100, max(0, progress)),
            'message': message,
            'timestamp': time.time()
        })
        
        if details:
            data['details'].append({
                'timestamp': time.time(),
                'message': details
            })
            
        if current_file:
            data['current_file'] = current_file
            
        # Send update to client
        if correlation_id in self.clients:
            try:
                self.clients[correlation_id].put({
                    'type': 'progress',
                    'data': data.copy()
                }, block=False)
            except:
                pass  # Client might have disconnected
                
    def update_file_progress(self, correlation_id: str, files_processed: int, 
                           total_files: int, current_file: str = None) -> None:
        """Update file processing progress"""
        if correlation_id not in self.progress_data:
            return
            
        self.progress_data[correlation_id].update({
            'files_processed': files_processed,
            'total_files': total_files,
            'current_file': current_file
        })
        
    def add_error(self, correlation_id: str, error_message: str, file_name: str = None) -> None:
        """Add an error to the progress tracking"""
        if correlation_id not in self.progress_data:
            return
            
        error_info = {
            'timestamp': time.time(),
            'message': error_message,
            'file': file_name
        }
        
        self.progress_data[correlation_id]['errors'].append(error_info)
        
        # Send error update to client
        if correlation_id in self.clients:
            try:
                self.clients[correlation_id].put({
                    'type': 'error',
                    'data': error_info
                }, block=False)
            except:
                pass
                
    def complete_operation(self, correlation_id: str, success: bool, 
                          final_message: str, result_data: Dict = None) -> None:
        """Mark operation as complete"""
        if correlation_id not in self.progress_data:
            return
            
        data = self.progress_data[correlation_id]
        data.update({
            'step': 'completed' if success else 'failed',
            'progress': 100 if success else data.get('progress', 0),
            'message': final_message,
            'completed': True,
            'success': success,
            'end_time': time.time(),
            'duration': time.time() - data['start_time']
        })
        
        if result_data:
            data['result'] = result_data
            
        # Send completion update to client
        if correlation_id in self.clients:
            try:
                self.clients[correlation_id].put({
                    'type': 'complete',
                    'data': data.copy()
                }, block=False)
            except:
                pass
                
    def get_client_queue(self, correlation_id: str) -> Queue:
        """Get the queue for a specific client"""
        if correlation_id not in self.clients:
            self.clients[correlation_id] = Queue()
        return self.clients[correlation_id]
        
    def cleanup_operation(self, correlation_id: str) -> None:
        """Clean up resources for completed operation"""
        if correlation_id in self.progress_data:
            del self.progress_data[correlation_id]
        if correlation_id in self.clients:
            del self.clients[correlation_id]

# Global progress manager
progress_manager = ProgressManager()

# Configuration for upload
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'web_outputs'
ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf', 'jpg', 'jpeg', 'png'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_zip_file(zip_path: str, extract_to: str) -> bool:
    """Extract zip file to specified directory"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        return True
    except Exception as e:
        logger.error(f"Failed to extract zip file: {e}")
        return False

def convert_documents_with_progress(documents_path: str, tag_mapping: Dict[str, str], correlation_id: str) -> Dict[str, str]:
    """Convert documents to PDF with real-time progress updates"""
    from src.high_quality_pdf_converter import DocumentPDFConverter
    
    converter = DocumentPDFConverter(documents_path)
    pdf_mapping = {}
    
    # Get list of files to convert (exclude None values)
    files_to_convert = [(filename, tag) for filename, tag in tag_mapping.items() if tag is not None]
    total_files = len(files_to_convert)
    
    logger.info(f"[CONVERSION] Starting conversion of {total_files} files")
    
    if total_files == 0:
        return pdf_mapping
    
    # Convert each file individually with progress updates
    for i, (filename, tag) in enumerate(files_to_convert):
        # Calculate dynamic progress (25% to 60% range = 35% total)
        progress_percentage = 25 + (35 * i / total_files)
        
        logger.info(f"[CONVERSION] Processing file {i+1}/{total_files}: {filename} (Progress: {progress_percentage}%)")
        
        progress_manager.update_progress(
            correlation_id, 
            'pdf_conversion', 
            int(progress_percentage),
            f'Converting {filename}...',
            f'Processing file {i+1}/{total_files}: {filename}'
        )
        
        # Add small delay to make progress updates visible during testing
        import time
        time.sleep(0.5)
        
        # Convert individual file
        try:
            converted_filename, pdf_path = converter.convert_and_filter(filename)
            if converted_filename and pdf_path:
                pdf_mapping[converted_filename] = pdf_path
                logger.info(f"[CONVERSION] Successfully converted: {filename}")
            else:
                logger.warning(f"[CONVERSION] Failed to convert: {filename}")
                
        except Exception as e:
            logger.error(f"[CONVERSION] Error converting {filename}: {e}")
            # Continue with other files even if one fails
    
    # Final progress update for this phase
    successful_conversions = len([p for p in pdf_mapping.values() if p])
    progress_manager.update_progress(
        correlation_id,
        'pdf_conversion',
        58,  # Just before the final 60% update
        f'Conversion phase completed: {successful_conversions}/{total_files} successful',
        f'Completed processing all {total_files} documents'
    )
    
    logger.info(f"[CONVERSION] Completed. {successful_conversions}/{total_files} successful")
    return pdf_mapping

def run_dst_processing(documents_path: str, options: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """Run the DST submittals processing with given options"""
    # Use the provided correlation ID instead of generating a new one
    set_correlation_id(correlation_id)
    logger.info(f"[PROCESSING] Using correlation ID: {correlation_id}")
    
    # Progress tracking should already be initialized by the caller
    
    try:
        # Import processing modules using the correct names from main script
        from src.tag_extractor import TagExtractor
        from src.enhanced_doc_extractor import enhance_tag_mapping
        from src.high_quality_pdf_converter import DocumentPDFConverter
        from src.title_page_generator import TitlePageGenerator
        from src.create_final_pdf import FinalPDFAssembler
        
        # Set environment variables based on options
        progress_manager.update_progress(correlation_id, 'setup', 5, 
                                       'Configuring processing environment...',
                                       'Setting up environment variables and options')
        
        if options.get('no_pricing_filter'):
            os.environ['DST_NO_PRICING_FILTER'] = 'true'
        
        # Set other environment variables
        for env_var, value in options.get('env_vars', {}).items():
            if value:
                os.environ[env_var] = str(value)
        
        # Generate output filename (just the filename, not full path)
        provided_filename = options.get('output_filename', '').strip()
        logger.info(f"Provided filename from options: '{provided_filename}'")
        
        if provided_filename:
            # Use provided filename, ensure it has .pdf extension
            if not provided_filename.lower().endswith('.pdf'):
                provided_filename += '.pdf'
            output_filename = provided_filename
        else:
            # Generate default filename
            output_filename = f"DST_Submittal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
        logger.info(f"Final output filename: '{output_filename}'")
        
        # Run the processing pipeline following the main script pattern
        logger.info(f"Starting DST processing for: {documents_path}")
        
        # Step 1: Extract tags
        progress_manager.update_progress(correlation_id, 'tag_extraction', 10, 
                                       'Scanning documents for equipment tags...',
                                       f'Analyzing documents in {documents_path}')
        
        # Get extraction options for performance optimization
        tagged_filenames = options.get('tagged_filenames', False)
        no_pricing_filter = options.get('no_pricing_filter', False)
        
        # Initialize TagExtractor with filename mode setting
        # When tagged_filenames=True: Fast extraction from filenames only (no file I/O)
        # When tagged_filenames=False: Traditional content-based extraction (slower)
        extractor = TagExtractor(documents_path, use_filename_tags=tagged_filenames)
        tag_mapping = extractor.extract_all_tags()
        
        progress_manager.update_progress(correlation_id, 'tag_extraction', 15, 
                                       'Processing tag mappings...',
                                       f'Found {len([t for t in tag_mapping.values() if t])} tagged documents')
        
        # Check for existing user-edited structure before regenerating
        from src.config import Config
        config = Config()
        existing_user_edits = None
        
        if os.path.exists(config.tag_mapping_file):
            try:
                with open(config.tag_mapping_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                
                # Check if structure has user edits (indicated by last_updated timestamp)
                if ('pdf_structure' in existing_data and 
                    existing_data.get('metadata', {}).get('last_updated')):
                    existing_user_edits = existing_data
                    logger.info("Found existing user-edited structure - will preserve customizations")
                else:
                    logger.info("No user edits detected - will generate fresh structure")
            except Exception as e:
                logger.warning(f"Could not load existing structure: {e}")
        
        # Enhance tag mapping with pricing filter option and optimizations
        # When tagged_filenames=True: Only scans Item Summary files for pricing (fast)
        # When tagged_filenames=False: Scans all files for pricing content (thorough)
        enhanced_mapping = enhance_tag_mapping(tag_mapping, documents_path, no_pricing_filter, tagged_filenames, existing_user_edits)
        
        tag_count = len([t for t in tag_mapping.values() if t])
        equipment_count = len(enhanced_mapping.get('tag_groups', {}))
        
        progress_manager.update_progress(correlation_id, 'tag_extraction', 20, 
                                       'Organizing equipment groups...',
                                       f'Identified {equipment_count} equipment groups: {list(enhanced_mapping.get("tag_groups", {}).keys())}')
        
        logger.info(f"Tag mapping: {tag_mapping}")
        logger.info(f"Enhanced mapping tag_groups: {enhanced_mapping.get('tag_groups', {})}")
        
        # Save enhanced mapping to file (config already imported above)
        
        logger.info(f"Saving enhanced mapping to: {config.tag_mapping_file}")
        with open(config.tag_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_mapping, f, indent=2, ensure_ascii=False)
        
        if tag_count == 0:
            progress_manager.complete_operation(correlation_id, False, 
                                              'No equipment tags found in documents')
            return {
                'success': False,
                'error': 'No equipment tags found in documents',
                'correlation_id': correlation_id
            }
        
        # Step 2: Convert to PDF with dynamic progress tracking
        progress_manager.update_progress(correlation_id, 'pdf_conversion', 25, 
                                       'Converting documents to PDF...',
                                       f'Starting conversion of {len(tag_mapping)} documents')
        
        # Convert documents with real-time progress updates
        pdf_mapping = convert_documents_with_progress(documents_path, tag_mapping, correlation_id)
        
        # Final progress update for conversion phase
        successful_conversions = len([p for p in pdf_mapping.values() if p])
        progress_manager.update_progress(correlation_id, 'pdf_conversion', 60, 
                                       'PDF conversion completed',
                                       f'Successfully converted {successful_conversions}/{len(tag_mapping)} documents')
        
        logger.info(f"PDF conversion completed. Mapping: {pdf_mapping}")
        logger.info(f"Total conversions: {successful_conversions}")
        
        # Verify converted files exist and report issues
        conversion_errors = []
        for original_file, converted_path in pdf_mapping.items():
            if converted_path:
                exists = os.path.exists(converted_path)
                logger.info(f"Converted file: {original_file} -> {converted_path} (exists: {exists})")
                if not exists:
                    error_msg = f"Converted file missing: {original_file}"
                    conversion_errors.append(error_msg)
                    progress_manager.add_error(correlation_id, error_msg, original_file)
            else:
                error_msg = f"Conversion failed: {original_file}"
                conversion_errors.append(error_msg)
                progress_manager.add_error(correlation_id, error_msg, original_file)
                logger.warning(error_msg)
        
        # Step 3: Generate title pages
        tags = list(enhanced_mapping.get('tag_groups', {}).keys())
        progress_manager.update_progress(correlation_id, 'title_generation', 65, 
                                       'Generating title pages...',
                                       f'Creating title pages for {len(tags)} equipment groups')
        
        title_generator = TitlePageGenerator()
        title_pages = title_generator.create_all_title_pages(tags)
        
        progress_manager.update_progress(correlation_id, 'title_generation', 75, 
                                       'Title pages completed',
                                       f'Generated {len(title_pages)} title pages')
        
        # Save PDF mapping to file (like main script does)
        
        logger.info(f"Saving PDF mapping to: {config.pdf_conversion_mapping_file}")
        with open(config.pdf_conversion_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(pdf_mapping, f, indent=2, ensure_ascii=False)
        
        # Step 4: Assemble final PDF  
        progress_manager.update_progress(correlation_id, 'pdf_assembly', 80, 
                                       'Assembling final PDF document...',
                                       'Combining all documents and title pages')
        
        assembler = FinalPDFAssembler(documents_path)
        
        # Debug: Check what the assembler loaded
        logger.info(f"Assembler loaded PDF mapping: {assembler.pdf_mapping}")
        logger.info(f"Assembler loaded PDF structure with {len(assembler.pdf_structure)} items")
        
        final_pdf_path = assembler.create_final_pdf(output_filename)
        
        progress_manager.update_progress(correlation_id, 'pdf_assembly', 90, 
                                       'PDF assembly completed',
                                       f'Final document created: {output_filename}')
        
        # Ensure the generated PDF is in our output folder
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        # Check where the PDF was actually created
        logger.info(f"Final PDF created at: {final_pdf_path}")
        logger.info(f"Expected output path: {output_path}")
        
        if os.path.exists(final_pdf_path):
            if final_pdf_path != output_path:
                # Move file to our output folder
                shutil.move(final_pdf_path, output_path)
                logger.info(f"Moved PDF from {final_pdf_path} to {output_path}")
        else:
            # Check if file was created in current directory
            current_dir_path = os.path.join(os.getcwd(), output_filename)
            if os.path.exists(current_dir_path):
                shutil.move(current_dir_path, output_path)
                logger.info(f"Moved PDF from current directory to {output_path}")
            else:
                logger.error(f"Generated PDF not found at {final_pdf_path} or {current_dir_path}")
                return {
                    'success': False,
                    'error': f'Generated PDF file not found at expected location: {final_pdf_path}',
                    'correlation_id': correlation_id
                }
        
        # Verify the file exists in our output folder
        if not os.path.exists(output_path):
            logger.error(f"Final PDF not found in output folder: {output_path}")
            # List what files do exist for debugging
            if os.path.exists(OUTPUT_FOLDER):
                existing_files = os.listdir(OUTPUT_FOLDER)
                logger.error(f"Files in output folder: {existing_files}")
            
            return {
                'success': False,
                'error': f'Generated PDF file could not be moved to output folder. Expected: {output_path}',
                'correlation_id': correlation_id,
                'debug_info': {
                    'final_pdf_path': final_pdf_path,
                    'output_path': output_path,
                    'output_folder_exists': os.path.exists(OUTPUT_FOLDER),
                    'files_in_output': os.listdir(OUTPUT_FOLDER) if os.path.exists(OUTPUT_FOLDER) else []
                }
            }
        
        progress_manager.update_progress(correlation_id, 'completed', 100, 
                                       'Processing completed successfully!',
                                       f'Generated {output_filename} with {equipment_count} equipment groups')
        
        result = {
            'success': True,
            'output_file': output_filename,
            'output_path': output_path,
            'tags_found': tag_count,
            'equipment_groups': equipment_count,
            'correlation_id': correlation_id
        }
        
        # Mark operation as complete
        progress_manager.complete_operation(correlation_id, True, 
                                          'DST Submittal PDF generated successfully!', 
                                          result)
        
        logger.info(f"Returning success response: {result}")
        return result
        
    except Exception as e:
        error_msg = f"Processing failed: {str(e)}"
        logger.error(error_msg)
        
        # Mark operation as failed
        progress_manager.complete_operation(correlation_id, False, error_msg)
        
        return {
            'success': False,
            'error': str(e),
            'correlation_id': correlation_id
        }

@app.route('/')
def index():
    """Main page with upload interface"""
    return render_template('index.html')

@app.route('/progress/<correlation_id>')
def progress_stream(correlation_id):
    """Server-Sent Events endpoint for real-time progress updates"""
    logger.info(f"[SSE] Client connected to progress stream for: {correlation_id}")
    
    def generate():
        client_queue = progress_manager.get_client_queue(correlation_id)
        logger.info(f"[SSE] Got client queue for: {correlation_id}")
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'correlation_id': correlation_id})}\n\n"
        logger.info(f"[SSE] Sent connection event for: {correlation_id}")
        
        # Keep connection alive and send updates
        while True:
            try:
                # Wait for update with timeout
                update = client_queue.get(timeout=30)
                logger.info(f"[SSE] Sending update for {correlation_id}: {update.get('type', 'unknown')}")
                yield f"data: {json.dumps(update)}\n\n"
                
                # If operation completed, close connection after a delay
                if update.get('type') == 'complete':
                    time.sleep(2)  # Give client time to process final update
                    break
                    
            except:
                # Timeout - send keepalive
                yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': time.time()})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream',
                   headers={'Cache-Control': 'no-cache',
                           'Connection': 'keep-alive',
                           'Access-Control-Allow-Origin': '*'})

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and processing"""
    temp_dir = None
    
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': 'No files selected'})
        
        # Get processing options
        output_filename_from_form = request.form.get('output_filename', '')
        logger.info(f"Form data received: {dict(request.form)}")
        logger.info(f"Output filename from form: '{output_filename_from_form}'")
        
        options = {
            'output_filename': output_filename_from_form,
            'no_pricing_filter': request.form.get('no_pricing_filter') == 'true',
            'tagged_filenames': request.form.get('tagged_filenames') == 'true',
            'env_vars': {}
        }
        
        # Parse environment variables from form
        env_vars = [
            'DST_OFFICETOPDF_PATH',
            'DST_CONVERTED_PDFS_DIR',
            'DST_TITLE_PAGES_DIR',
            'DST_TAG_MAPPING_FILE',
            'DST_PDF_CONVERSION_MAPPING_FILE',
            'DST_CONVERSION_TIMEOUT',
            'DST_LIBREOFFICE_TIMEOUT'
        ]
        
        for var in env_vars:
            value = request.form.get(var, '').strip()
            if value:
                options['env_vars'][var] = value
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix='dst_web_')
        session['temp_dir'] = temp_dir
        
        # Process uploaded files
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(temp_dir, filename)
                file.save(filepath)
                
                # ZIP file extraction disabled - functionality not working properly
                # if filename.lower().endswith('.zip'):
                #     extract_dir = os.path.join(temp_dir, 'extracted')
                #     os.makedirs(extract_dir, exist_ok=True)
                #     if extract_zip_file(filepath, extract_dir):
                #         # Use extracted directory for processing
                #         temp_dir = extract_dir
                #     else:
                #         return jsonify({
                #             'success': False, 
                #             'error': f'Failed to extract zip file: {filename}'
                #         })
        
        # Get correlation ID for this request
        correlation_id = set_correlation_id()
        logger.info(f"[UPLOAD] Generated correlation ID: {correlation_id}")
        
        # Initialize progress tracking for this operation
        progress_manager.start_operation(correlation_id)
        logger.info(f"[UPLOAD] Started progress tracking for: {correlation_id}")
        
        # Start DST processing in background thread
        def process_in_background():
            current_thread = threading.current_thread()
            current_thread.name = f"DST-Processing-{correlation_id[:8]}"
            
            # Add to active processes list for tracking
            active_processes.append(current_thread)
            
            try:
                # Check if server is shutting down
                if shutdown_event.is_set():
                    logger.info(f"Skipping processing for {correlation_id} - server shutting down")
                    return
                    
                run_dst_processing(temp_dir, options, correlation_id)
            except Exception as e:
                logger.error(f"Processing failed for {correlation_id}: {e}")
                progress_manager.complete_operation(
                    correlation_id, 
                    success=False, 
                    final_message=f"Processing failed: {str(e)}"
                )
            finally:
                # Remove from active processes
                if current_thread in active_processes:
                    try:
                        active_processes.remove(current_thread)
                    except ValueError:
                        pass  # Already removed
                
                # Clean up temporary directory
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp directory {temp_dir}: {cleanup_error}")
        
        # Start processing in background
        processing_thread = threading.Thread(target=process_in_background)
        processing_thread.daemon = True
        processing_thread.start()
        
        # Return immediately with correlation ID for progress tracking
        return jsonify({
            'success': True,
            'correlation_id': correlation_id,
            'message': 'Processing started',
            'progress_url': f'/progress/{correlation_id}'
        })
        
    except RequestEntityTooLarge:
        return jsonify({'success': False, 'error': 'File too large (max 500MB)'})
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    """Download generated PDF file"""
    try:
        secure_name = secure_filename(filename)
        filepath = os.path.join(OUTPUT_FOLDER, secure_name)
        
        logger.info(f"Download request for: {filename}")
        logger.info(f"Looking for file at: {filepath}")
        logger.info(f"File exists: {os.path.exists(filepath)}")
        
        if os.path.exists(filepath):
            logger.info(f"Sending file: {filepath}")
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            # List files in output folder for debugging
            if os.path.exists(OUTPUT_FOLDER):
                files_in_folder = os.listdir(OUTPUT_FOLDER)
                logger.error(f"File not found. Files in {OUTPUT_FOLDER}: {files_in_folder}")
            else:
                logger.error(f"Output folder does not exist: {OUTPUT_FOLDER}")
            
            return jsonify({
                'error': f'File not found: {filename}',
                'filepath': filepath,
                'folder_exists': os.path.exists(OUTPUT_FOLDER)
            }), 404
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    """Get application status and configuration"""
    config = Config()
    return jsonify({
        'status': 'ready',
        'version': config.VERSION,
        'officetopdf_path': config.officetopdf_path,
        'conversion_timeout': config.conversion_timeout,
        'active_processes': len(active_processes),
        'shutdown_initiated': shutdown_event.is_set()
    })

@app.route('/extract-tags', methods=['POST'])
def extract_tags():
    """
    Extract tags and generate PDF structure without running full processing.
    
    This endpoint provides fast tag extraction with two modes:
    1. Filename-based: Extract tags from filenames only (fast, no file I/O)
    2. Content-based: Traditional extraction from file content (slower but flexible)
    
    Performance optimizations when using filename mode:
    - Only Item Summary files are scanned for pricing content
    - 80%+ of files skip content scanning entirely
    - Provides 5-10x speed improvement for large document sets
    """
    temp_dir = None
    correlation_id = set_correlation_id()
    
    # Start diagnostic logging
    log_processing_stage('extract_tags_start', 'started', {
        'correlation_id': correlation_id,
        'endpoint': '/extract-tags'
    })
    
    try:
        if 'files' not in request.files:
            log_processing_stage('extract_tags_validation', 'failed', {'error': 'No files uploaded'})
            return jsonify({'success': False, 'error': 'No files uploaded'})
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            log_processing_stage('extract_tags_validation', 'failed', {'error': 'No files selected'})
            return jsonify({'success': False, 'error': 'No files selected'})
        
        # Get processing options
        no_pricing_filter = request.form.get('no_pricing_filter') == 'true'
        tagged_filenames = request.form.get('tagged_filenames', 'true') == 'true'
        
        # Log processing options
        processing_options = {
            'no_pricing_filter': no_pricing_filter,
            'tagged_filenames': tagged_filenames,
            'file_count': len(files)
        }
        log_processing_stage('extract_tags_options', 'configured', processing_options)
        
        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix='dst_extract_')
        log_processing_stage('extract_tags_temp_dir', 'created', {'temp_dir': temp_dir})
        
        # Process uploaded files with detailed logging
        uploaded_files = []
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                original_name = file.filename
                filename = secure_filename(file.filename)
                filepath = os.path.join(temp_dir, filename)
                file.save(filepath)
                
                # Get file size
                file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                
                # Log file upload details
                log_file_upload(original_name, filename, file_size, filepath)
                uploaded_files.append({
                    'original': original_name,
                    'secured': filename,
                    'size': file_size,
                    'path': filepath
                })
                
                # ZIP file extraction disabled - functionality not working properly
                # if filename.lower().endswith('.zip'):
                #     extract_dir = os.path.join(temp_dir, 'extracted')
                #     os.makedirs(extract_dir, exist_ok=True)
                #     if extract_zip_file(filepath, extract_dir):
                #         # Use extracted directory for processing
                #         temp_dir = extract_dir
                #         log_processing_stage('zip_extraction', 'success', {
                #             'zip_file': filename,
                #             'extract_dir': extract_dir
                #         })
                #         # Log manifest of extracted files
                #         if os.path.exists(extract_dir):
                #             extracted_files = [f for f in os.listdir(extract_dir) if os.path.isfile(os.path.join(extract_dir, f))]
                #             log_file_manifest(extract_dir, extracted_files)
                #     else:
                #         log_processing_stage('zip_extraction', 'failed', {'zip_file': filename})
                #         return jsonify({
                #             'success': False, 
                #             'error': f'Failed to extract zip file: {filename}'
                #         })
        
        # Log final file manifest
        if os.path.exists(temp_dir):
            final_files = [f for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
            log_file_manifest(temp_dir, final_files)
        
        # Extract tags only (no PDF conversion)
        from src.tag_extractor import TagExtractor
        from src.enhanced_doc_extractor import enhance_tag_mapping
        from src.config import Config
        
        logger.info(f"Extracting tags from: {temp_dir} (filename mode: {tagged_filenames})")
        log_processing_stage('tag_extraction', 'started', {
            'temp_dir': temp_dir,
            'filename_mode': tagged_filenames,
            'file_count': len(final_files) if 'final_files' in locals() else 0
        })
        
        # Initialize TagExtractor with filename mode setting
        extractor = TagExtractor(temp_dir, use_filename_tags=tagged_filenames)
        tag_mapping = extractor.extract_all_tags()
        
        # Log tag extraction results
        successful_extractions = len([t for t in tag_mapping.values() if t])
        failed_extractions = len([t for t in tag_mapping.values() if not t])
        log_processing_stage('tag_extraction', 'completed', {
            'successful_extractions': successful_extractions,
            'failed_extractions': failed_extractions,
            'total_files': len(tag_mapping)
        })
        
        # Log JSON snapshot of tag mapping
        log_json_snapshot('tag_mapping', tag_mapping, correlation_id)
        
        # Generate enhanced mapping with complete PDF structure and optimizations
        log_processing_stage('structure_generation', 'started', {'tag_count': successful_extractions})
        enhanced_mapping = enhance_tag_mapping(tag_mapping, temp_dir, no_pricing_filter, tagged_filenames)
        
        # Log PDF structure details
        log_pdf_structure(
            enhanced_mapping['pdf_structure'], 
            enhanced_mapping['metadata'], 
            processing_options
        )
        
        # Save to config file
        config = Config()
        with open(config.tag_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_mapping, f, indent=2, ensure_ascii=False)
        
        log_processing_stage('structure_generation', 'completed', {
            'structure_items': len(enhanced_mapping['pdf_structure']),
            'equipment_groups': len(enhanced_mapping.get('tag_groups', {})),
            'config_file': config.tag_mapping_file
        })
        
        # Log JSON snapshot of final structure
        log_json_snapshot('enhanced_mapping', enhanced_mapping, correlation_id)
        
        logger.info(f"Tag extraction complete. Found {successful_extractions} tagged files")
        
        result = {
            'success': True,
            'pdf_structure': enhanced_mapping['pdf_structure'],
            'metadata': enhanced_mapping['metadata'],
            'tags_found': successful_extractions,
            'equipment_groups': len(enhanced_mapping.get('tag_groups', {}))
        }
        
        log_processing_stage('extract_tags_complete', 'success', result)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Tag extraction failed: {e}")
        log_processing_stage('extract_tags_complete', 'failed', {'error': str(e)})
        return jsonify({'success': False, 'error': str(e)})
    
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                log_processing_stage('cleanup', 'success', {'temp_dir': temp_dir})
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {cleanup_error}")
                log_processing_stage('cleanup', 'failed', {'temp_dir': temp_dir, 'error': str(cleanup_error)})

@app.route('/get-structure')
def get_structure():
    """Get the current PDF structure from the JSON file"""
    try:
        from src.config import Config
        config = Config()
        
        # Try to load the enhanced mapping file
        if os.path.exists(config.tag_mapping_file):
            with open(config.tag_mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Return the PDF structure if it exists, otherwise create a basic one
            if 'pdf_structure' in data:
                return jsonify({
                    'success': True,
                    'pdf_structure': data['pdf_structure'],
                    'metadata': data.get('metadata', {}),
                    'file_exists': True
                })
            else:
                # Legacy format - create basic structure from tag_groups
                pdf_structure = []
                position = 1
                
                tag_groups = data.get('tag_groups', {})
                for tag in sorted(tag_groups.keys()):
                    # Add title page
                    pdf_structure.append({
                        "type": "title_page",
                        "tag": tag,
                        "title": tag,
                        "position": position,
                        "include": True
                    })
                    position += 1
                    
                    # Add documents
                    for filename in sorted(tag_groups[tag]):
                        pdf_structure.append({
                            "type": "document",
                            "tag": tag,
                            "filename": filename,
                            "display_title": filename,
                            "file_type": "Unknown",
                            "converted_path": f"converted_pdfs/{os.path.splitext(filename)[0]}.pdf",
                            "position": position,
                            "include": True
                        })
                        position += 1
                
                return jsonify({
                    'success': True,
                    'pdf_structure': pdf_structure,
                    'metadata': {
                        'total_items': len(pdf_structure),
                        'processing_complete': False,
                        'legacy_format': True
                    },
                    'file_exists': True
                })
        else:
            return jsonify({
                'success': False,
                'error': 'No PDF structure file found. Please process files first.',
                'file_exists': False
            })
            
    except Exception as e:
        logger.error(f"Failed to get PDF structure: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'file_exists': False
        }), 500

@app.route('/update-structure', methods=['POST'])
def update_structure():
    """Update the PDF structure in the JSON file"""
    try:
        from src.config import Config
        config = Config()
        
        # Get the updated structure from the request
        request_data = request.get_json()
        if not request_data or 'pdf_structure' not in request_data:
            return jsonify({
                'success': False,
                'error': 'No PDF structure provided in request'
            }), 400
        
        pdf_structure = request_data['pdf_structure']
        
        # Load existing data
        existing_data = {}
        if os.path.exists(config.tag_mapping_file):
            with open(config.tag_mapping_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        
        # Update the structure and recalculate metadata
        existing_data['pdf_structure'] = pdf_structure
        existing_data['metadata'] = {
            'total_tags': len([item for item in pdf_structure if item["type"] == "title_page"]),
            'total_documents': len([item for item in pdf_structure if item["type"] == "document"]),
            'total_cut_sheets': len([item for item in pdf_structure if item["type"] == "cut_sheet"]),
            'total_items': len(pdf_structure),
            'processing_complete': True,
            'last_updated': datetime.now().isoformat()
        }
        
        # Save the updated structure
        with open(config.tag_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Updated PDF structure with {len(pdf_structure)} items")
        
        return jsonify({
            'success': True,
            'message': f'PDF structure updated with {len(pdf_structure)} items',
            'metadata': existing_data['metadata']
        })
        
    except Exception as e:
        logger.error(f"Failed to update PDF structure: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def chrome_devtools():
    """Handler for Chrome DevTools requests to prevent 404 errors"""
    return jsonify({'error': 'Not supported'}), 404

@app.route('/debug-log')
def debug_log():
    """Get recent log entries for debugging"""
    try:
        from src.config import Config
        config = Config()
        
        # Read log file if it exists
        if os.path.exists(config.log_file_path):
            # Get last 1000 lines of log file
            with open(config.log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get last 1000 lines or all lines if less than 1000
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
            
            # Parse JSON log entries
            log_entries = []
            for line in recent_lines:
                line = line.strip()
                if line:
                    try:
                        log_entry = json.loads(line)
                        log_entries.append(log_entry)
                    except json.JSONDecodeError:
                        # Handle non-JSON log lines (fallback)
                        log_entries.append({
                            'timestamp': 'unknown',
                            'level': 'INFO',
                            'message': line,
                            'correlation_id': 'unknown'
                        })
            
            # Filter by correlation ID if provided
            correlation_id = request.args.get('correlation_id')
            if correlation_id:
                log_entries = [entry for entry in log_entries 
                             if entry.get('correlation_id') == correlation_id]
            
            # Filter by operation if provided
            operation = request.args.get('operation')
            if operation:
                log_entries = [entry for entry in log_entries 
                             if operation in entry.get('message', '').lower() or
                                operation in str(entry.get('extra', {})).lower()]
            
            # Get only recent entries (last 2 hours by default)
            from datetime import datetime, timedelta
            hours_back = int(request.args.get('hours', 2))
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            
            filtered_entries = []
            for entry in log_entries:
                try:
                    # Parse timestamp
                    timestamp_str = entry.get('timestamp', '')
                    if timestamp_str and timestamp_str != 'unknown':
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if timestamp >= cutoff_time:
                            filtered_entries.append(entry)
                    else:
                        # Include entries without valid timestamps
                        filtered_entries.append(entry)
                except:
                    # Include entries with parsing errors
                    filtered_entries.append(entry)
            
            return jsonify({
                'success': True,
                'log_file': config.log_file_path,
                'total_entries': len(log_entries),
                'filtered_entries': len(filtered_entries),
                'entries': filtered_entries[-200:],  # Return last 200 entries
                'filters': {
                    'correlation_id': correlation_id,
                    'operation': operation,
                    'hours_back': hours_back
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Log file not found: {config.log_file_path}',
                'log_file': config.log_file_path
            })
            
    except Exception as e:
        logger.error(f"Failed to read debug log: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/shutdown', methods=['POST'])
def shutdown_server():
    """Gracefully shutdown the server"""
    logger.info("Shutdown requested via /shutdown endpoint")
    
    # Check if there are active processes
    active_count = len(active_processes)
    
    if active_count > 0:
        logger.info(f"Initiating graceful shutdown with {active_count} active processes")
        shutdown_event.set()
        
        return jsonify({
            'success': True,
            'message': f'Graceful shutdown initiated. Waiting for {active_count} active processes to complete.',
            'active_processes': active_count
        })
    else:
        logger.info("No active processes, shutting down immediately")
        
        # Run cleanup in a separate thread to allow response to be sent
        def delayed_shutdown():
            time.sleep(0.5)  # Give time for response to be sent
            cleanup_server()
            # Try multiple shutdown methods for better compatibility
            try:
                # Method 1: Werkzeug shutdown (older versions)
                shutdown_func = request.environ.get('werkzeug.server.shutdown')
                if shutdown_func:
                    shutdown_func()
                    return
            except:
                pass
            
            try:
                # Method 2: Signal-based shutdown
                import os
                import signal
                os.kill(os.getpid(), signal.SIGTERM)
            except:
                pass
            
            try:
                # Method 3: System exit (last resort)
                import sys
                sys.exit(0)
            except:
                pass
            
        shutdown_thread = threading.Thread(target=delayed_shutdown)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Server shutting down immediately',
            'active_processes': 0
        })

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'success': False, 'error': 'File too large (max 500MB)'}), 413

@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='DST Submittals Generator Web Interface')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    print(f"DST Submittals Generator Web Interface")
    print(f"======================================")
    print(f"Access at: http://{args.host}:{args.port}")
    print(f"")
    print(f"Shutdown options:")
    print(f"  - Press Ctrl+C for graceful shutdown")
    print(f"  - Run shutdown_web_interface.bat")
    print(f"  - POST to http://{args.host}:{args.port}/shutdown")
    print(f"")
    print(f"Starting server...")
    
    try:
        logger.info(f"Starting web interface on {args.host}:{args.port}")
        
        # Run the Flask app
        app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
        
    except KeyboardInterrupt:
        logger.info("Received Ctrl+C, initiating graceful shutdown...")
        print("\nShutting down gracefully...")
        cleanup_server()
        print("Shutdown complete.")
        
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"Server error: {e}")
        cleanup_server()
        
    finally:
        logger.info("Web interface stopped")
        print("Web interface stopped.")