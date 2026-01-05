#!/usr/bin/env python3
"""
Simple launcher script for the Flask web application
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("Starting SUMO Traffic Control Web App...")
    print("Open your browser and navigate to: http://localhost:5001")
    print("Press Ctrl+C to stop the server")
    
    try:
        # Run without debug mode for cleaner output
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down web server...")
        sys.exit(0)