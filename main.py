"""
Main entry point for the API Testing Agent service.
Runs the FastAPI application with uvicorn.
"""
import uvicorn
from core.webhooks import app

def main():
    """Start the FastAPI application."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
