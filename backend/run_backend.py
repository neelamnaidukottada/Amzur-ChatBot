#!/usr/bin/env python
"""Simple backend startup script."""
import os
import sys

# Set working directory to backend folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

# Run the server
if __name__ == "__main__":
    from uvicorn import run
    from app.main import app
    
    print("🚀 Starting ChatBot Backend...")
    print("📍 http://127.0.0.1:8000")
    print("Press CTRL+C to stop\n")
    
    run(app, host="127.0.0.1", port=8000)
