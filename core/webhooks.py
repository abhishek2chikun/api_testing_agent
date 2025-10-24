"""
Webhook handlers for external service integrations.
Receives webhooks from Jira and triggers the test generation pipeline.
"""
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
import logging
from core.orchestrator import process_epic

logging.basicConfig(level=logging.INFO)
app = FastAPI(
    title="API Testing Agent",
    description="Automated API test generation and execution service",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "API Testing Agent"}

@app.post('/jira/webhook')
async def jira_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Jira webhook endpoint. Receives Epic updates and triggers test generation.
    
    Expected payload format:
    {
        "issue": {
            "key": "EPIC-123",
            ...
        }
    }
    """
    payload = await request.json()
    # Extract issue key from webhook payload
    issue_key = payload.get('issue', {}).get('key')
    if not issue_key:
        raise HTTPException(status_code=400, detail='No issue key found in payload')
    
    logging.info('Webhook received for issue: %s', issue_key)
    # Process in background to avoid blocking webhook response
    background_tasks.add_task(process_epic, issue_key)
    return {'status': 'accepted', 'issue': issue_key}


