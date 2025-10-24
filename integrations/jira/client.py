"""
Jira API client for interacting with Jira REST API.
Handles authentication and API calls for fetching issues and posting comments.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

JIRA_BASE = os.getenv('JIRA_BASE')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_TOKEN = os.getenv('JIRA_TOKEN')

def fetch_issue(issue_key: str) -> dict:
    """
    Fetch issue details from Jira.
    
    Args:
        issue_key: Jira issue key (e.g., 'EPIC-123')
        
    Returns:
        dict: Full issue JSON response from Jira API
        
    Raises:
        requests.HTTPError: If API request fails
    """
    url = f"{JIRA_BASE}/rest/api/3/issue/{issue_key}"
    response = requests.get(
        url,
        auth=(JIRA_USER, JIRA_TOKEN),
        headers={"Accept": "application/json"}
    )
    response.raise_for_status()
    return response.json()

def post_comment(issue_key: str, body: str) -> dict:
    """
    Post a comment to a Jira issue using ADF (Atlassian Document Format).
    
    Args:
        issue_key: Jira issue key (e.g., 'EPIC-123')
        body: Comment text (plain text will be converted to ADF)
        
    Returns:
        dict: Comment creation response from Jira API
        
    Raises:
        requests.HTTPError: If API request fails
    """
    # Remove trailing slash from JIRA_BASE to avoid double slashes
    base_url = JIRA_BASE.rstrip('/')
    url = f"{base_url}/rest/api/3/issue/{issue_key}/comment"
    
    # Convert plain text to ADF format (Jira API v3 requirement)
    adf_body = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": body
                    }
                ]
            }
        ]
    }
    
    response = requests.post(
        url,
        auth=(JIRA_USER, JIRA_TOKEN),
        json={"body": adf_body},
        headers={"Accept": "application/json", "Content-Type": "application/json"}
    )
    response.raise_for_status()
    return response.json()


