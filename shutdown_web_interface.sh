#!/bin/bash

echo "DST Submittals Generator - Web Interface Shutdown"
echo "================================================"
echo

# Check if the server is running before attempting to shut it down
if ! curl -s http://127.0.0.1:5001/status > /dev/null 2>&1; then
    echo
    echo "Server is not running."
    exit 0
fi

echo
echo "Attempting to gracefully shutdown the web interface..."

# Try to shutdown via HTTP endpoint first
if curl -X POST http://127.0.0.1:5001/shutdown > /dev/null 2>&1; then
    echo
    echo "Shutdown request sent successfully."
    echo "The server should shutdown gracefully."
    exit 0
fi

echo
echo "Could not reach server via HTTP. Trying alternative methods..."

# Try to find and kill Python processes running web_interface.py
echo "Searching for Python processes..."

# Check for different Python executable names
python_found=0
for python_cmd in python3 python python3.9 python3.10 python3.11 python3.12; do
    if command -v $python_cmd &> /dev/null; then
        pids=$(pgrep -f "web_interface.py")
        if [ ! -z "$pids" ]; then
            echo "Found web_interface.py processes with PIDs: $pids"
            python_found=1
            
            # Try to terminate the processes gracefully first
            for pid in $pids; do
                echo "Terminating process $pid"
                kill $pid
                sleep 2
                
                # Check if process is still running and force kill if necessary
                if kill -0 $pid 2>/dev/null; then
                    echo "Force killing process $pid"
                    kill -9 $pid
                fi
            done
        fi
    fi
done

if [ $python_found -eq 0 ]; then
    echo "No web_interface.py processes found."
fi

# Also try killing processes on port 5000
port_pids=$(lsof -ti:5000)
if [ ! -z "$port_pids" ]; then
    echo "Found processes using port 5000: $port_pids"
    for pid in $port_pids; do
        echo "Terminating process using port 5000: $pid"
        kill $pid
        sleep 1
        
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            echo "Force killing process $pid"
            kill -9 $pid
        fi
    done
fi

echo
echo "Shutdown attempts completed."
echo
