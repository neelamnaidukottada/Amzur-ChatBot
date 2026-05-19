#!/usr/bin/env python
"""Simple backend startup script."""
import os
import sys
import logging

# Set working directory to backend folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Run the server
if __name__ == "__main__":
    from uvicorn import run
    from app.main import app
    
    print("\n" + "="*60)
    print("🚀 Starting ChatBot Backend...")
    print("📍 Server: http://127.0.0.1:8000")
    print("📍 Docs: http://127.0.0.1:8000/docs")
    print("📍 Diagnostic: http://127.0.0.1:8000/api/diagnostic")
    print("="*60 + "\n")
    
    logger.info("🚀 Backend server starting on http://127.0.0.1:8000")
    logger.info("✅ All routers loaded (auth, chat, data, research, tictactoe)")
    
    run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        log_level="info"
    )
