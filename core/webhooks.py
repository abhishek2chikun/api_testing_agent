"""
Webhook handlers for external service integrations.
Receives webhooks from Jira and triggers the test generation pipeline.
"""
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
import logging
from core.orchestrator import process_epic
from config.loader import get_config_value

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
    # Optional filter: process only issues with matching project prefix
    expected_prefix = str(get_config_value('runner.prefix_jira_name', '')).strip()
    if expected_prefix and not issue_key.startswith(expected_prefix + '-'):
        logging.info('Ignoring issue %s due to prefix filter: expected %s-*', issue_key, expected_prefix)
        return {'status': 'ignored', 'issue': issue_key}
    # Process in background to avoid blocking webhook response
    background_tasks.add_task(process_epic, issue_key)
    return {'status': 'accepted', 'issue': issue_key}


