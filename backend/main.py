#!/usr/bin/env python3
"""
Main entry point for the Market Maker API server.
"""
import uvicorn
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get project root and add to Python path
project_root = Path(__file__).parent.parent
project_root_str = str(project_root)

# Add project root to Python path
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# Set PYTHONPATH environment variable for subprocesses (uvicorn reload)
os.environ['PYTHONPATH'] = project_root_str + os.pathsep + os.environ.get('PYTHONPATH', '')

# Change to project root directory so imports work correctly
os.chdir(project_root_str)

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting Market Maker API server on {host}:{port}")
    print(f"API documentation available at http://localhost:{port}/docs")
    print(f"Project root: {project_root_str}")
    
    uvicorn.run(
        "backend.api:app",  # Use string import for proper reload support
        host=host,
        port=port,
        reload=True,  # Auto-reload on code changes (disable in production)
        reload_dirs=[project_root_str],  # Watch project root for changes
        log_level="info"
    )

