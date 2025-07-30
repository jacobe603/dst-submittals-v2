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
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from queue import Queue

from flask import Flask, render_template, request, jsonify, send_file, session, Response
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logger import get_logger, set_correlation_id
from src.config import Config
from src.exceptions import DSTError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dst-submittals-dev-key')
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

logger = get_logger('web_interface')

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
ALLOWED_EXTENSIONS = {'doc', 'docx', 'pdf', 'zip'}

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

def run_dst_processing(documents_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Run the DST submittals processing with given options"""
    correlation_id = set_correlation_id()
    
    # Initialize progress tracking
    progress_manager.start_operation(correlation_id)
    
    try:
        # Import processing modules using the correct names from main script
        from tag_extractor import TagExtractor
        from enhanced_doc_extractor import enhance_tag_mapping
        from high_quality_pdf_converter import DocumentPDFConverter
        from title_page_generator import TitlePageGenerator
        from create_final_pdf import FinalPDFAssembler
        
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
        
        extractor = TagExtractor(documents_path)
        tag_mapping = extractor.extract_all_tags()
        
        progress_manager.update_progress(correlation_id, 'tag_extraction', 15, 
                                       'Processing tag mappings...',
                                       f'Found {len([t for t in tag_mapping.values() if t])} tagged documents')
        
        # Enhance tag mapping
        enhanced_mapping = enhance_tag_mapping(tag_mapping, documents_path)
        
        tag_count = len([t for t in tag_mapping.values() if t])
        equipment_count = len(enhanced_mapping.get('tag_groups', {}))
        
        progress_manager.update_progress(correlation_id, 'tag_extraction', 20, 
                                       'Organizing equipment groups...',
                                       f'Identified {equipment_count} equipment groups: {list(enhanced_mapping.get("tag_groups", {}).keys())}')
        
        logger.info(f"Tag mapping: {tag_mapping}")
        logger.info(f"Enhanced mapping tag_groups: {enhanced_mapping.get('tag_groups', {})}")
        
        # Import config and save enhanced mapping to file (like main script does)
        from src.config import Config
        config = Config()
        
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
        
        # Step 2: Convert to PDF
        progress_manager.update_progress(correlation_id, 'pdf_conversion', 25, 
                                       'Converting documents to PDF...',
                                       f'Starting conversion of {len(tag_mapping)} documents')
        
        # Update file progress tracking
        progress_manager.update_file_progress(correlation_id, 0, len(tag_mapping))
        
        converter = DocumentPDFConverter(documents_path)
        pdf_mapping = converter.convert_all_documents(tag_mapping)
        
        # Update progress with conversion results
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
        logger.info(f"Assembler tag groups: {list(assembler.tag_groups.keys())}")
        
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
    def generate():
        client_queue = progress_manager.get_client_queue(correlation_id)
        
        # Send initial connection event
        yield f"data: {json.dumps({'type': 'connected', 'correlation_id': correlation_id})}\n\n"
        
        # Keep connection alive and send updates
        while True:
            try:
                # Wait for update with timeout
                update = client_queue.get(timeout=30)
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
            'env_vars': {}
        }
        
        # Parse environment variables from form
        env_vars = [
            'DST_OFFICETOPDF_PATH',
            'DST_CONVERTED_PDFS_DIR',
            'DST_TITLE_PAGES_DIR',
            'DST_TAG_MAPPING_FILE',
            'DST_PDF_CONVERSION_MAPPING_FILE',
            'DST_MAX_WORKERS',
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
                
                # If it's a zip file, extract it
                if filename.lower().endswith('.zip'):
                    extract_dir = os.path.join(temp_dir, 'extracted')
                    os.makedirs(extract_dir, exist_ok=True)
                    if extract_zip_file(filepath, extract_dir):
                        # Use extracted directory for processing
                        temp_dir = extract_dir
                    else:
                        return jsonify({
                            'success': False, 
                            'error': f'Failed to extract zip file: {filename}'
                        })
        
        # Start DST processing in background thread
        def process_in_background():
            try:
                run_dst_processing(temp_dir, options)
            finally:
                # Clean up temporary directory
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup temp directory {temp_dir}: {cleanup_error}")
        
        # Get correlation ID for this request
        correlation_id = set_correlation_id()
        
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
        'officetopdf_path': config.officetopdf_path,
        'max_workers': config.max_workers,
        'conversion_timeout': config.conversion_timeout
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
    print(f"Access at: http://{args.host}:{args.port}")
    
    app.run(host=args.host, port=args.port, debug=args.debug)