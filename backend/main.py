#!/usr/bin/env python3
"""
Main entry point for the Market Maker API server.
"""
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting Market Maker API server on {host}:{port}")
    print(f"API documentation available at http://localhost:{port}/docs")
    
    uvicorn.run(
        "backend.api:app",
        host=host,
        port=port,
        reload=True,  # Auto-reload on code changes (disable in production)
        log_level="info"
    )

