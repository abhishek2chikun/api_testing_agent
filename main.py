"""
Main entry point for the API Testing Agent service.
Can run the FastAPI app or start the polling runner via CLI flags.
"""
import argparse
import uvicorn
from core.webhooks import app
from core.epic_runner import run_polling_runner

def main():
    parser = argparse.ArgumentParser(description='API Testing Agent Service')
    parser.add_argument('--runner', dest='runner', choices=['on', 'off'], default='off', help='Start polling runner')
    parser.add_argument('--language', dest='language', choices=['python', 'java'], default='python', help='Test language for runner')
    parser.add_argument('--jenkins', dest='jenkins', choices=['yes', 'no'], default='no', help='Push to GitHub (triggers Jenkins) in runner mode')
    parser.add_argument('--port', dest='port', type=int, default=8002, help='HTTP port for FastAPI app')

    args = parser.parse_args()

    if args.runner == 'on':
        run_polling_runner(language=args.language, push_to_github=(args.jenkins == 'yes'))
        return

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=args.port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
