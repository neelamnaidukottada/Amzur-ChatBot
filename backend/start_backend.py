#!/usr/bin/env python3
"""Backend startup script with proper path handling."""
import os
import sys

# Set working directory to script location
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Add current directory to Python path
sys.path.insert(0, script_dir)

if __name__ == "__main__":
    import uvicorn
    from app.main import app
    
    print("[*] Starting ChatBot Backend...")
    print("[*] http://127.0.0.1:8000")
    print("[*] Press CTRL+C to stop\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
