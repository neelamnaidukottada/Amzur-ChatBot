#!/usr/bin/env python
"""Startup script that runs the FastAPI app with proper path configuration."""

import sys
import os

# Set the current directory and add backend to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Now we can import and run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
