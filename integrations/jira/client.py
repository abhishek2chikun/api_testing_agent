"""
Jira API client for interacting with Jira REST API.
Handles authentication and API calls for fetching issues and posting comments.
Includes search/query helpers for polling runners.
"""
import os
import requests
from dotenv import load_dotenv
from typing import Dict, List, Optional

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

def search_issues(jql: str, max_results: int = 50, fields: Optional[List[str]] = None, start_at: int = 0) -> Dict:
    """
    Search Jira issues using JQL. Uses the new /rest/api/3/search/jql API with robust fallbacks.
    Returns the raw search response with issues, total, etc.
    """
    base_url = (JIRA_BASE or "").rstrip('/')
    common_headers = {"Accept": "application/json"}
    field_str = ",".join(fields) if fields else None

    # Attempt 1: New GET endpoint /search/jql (per Atlassian change notice)
    try:
        url_new = f"{base_url}/rest/api/3/search/jql"
        params_new = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        if field_str:
            params_new["fields"] = field_str
        resp = requests.get(url_new, auth=(JIRA_USER, JIRA_TOKEN), headers=common_headers, params=params_new)
        if resp.status_code == 200:
            return resp.json()
        # If 410/404, fall through to legacy
    except requests.exceptions.RequestException:
        pass

    # Attempt 2: Legacy GET endpoint /search with jql param
    try:
        url_old_get = f"{base_url}/rest/api/3/search"
        params_old = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        if field_str:
            params_old["fields"] = field_str
        resp = requests.get(url_old_get, auth=(JIRA_USER, JIRA_TOKEN), headers=common_headers, params=params_old)
        if resp.status_code == 200:
            return resp.json()
    except requests.exceptions.RequestException:
        pass

    # Attempt 3: Legacy POST endpoint /search with JSON body
    url_old_post = f"{base_url}/rest/api/3/search"
    body = {
        "jql": jql,
        "maxResults": max_results,
        "startAt": start_at
    }
    if fields:
        body["fields"] = fields
    resp = requests.post(url_old_post, auth=(JIRA_USER, JIRA_TOKEN), headers={**common_headers, "Content-Type": "application/json"}, json=body)
    resp.raise_for_status()
    return resp.json()

def find_recent_epics_by_prefix(prefix_jira_name: str, limit: int = 10) -> List[Dict]:
    """
    Find recent Epics by project prefix (e.g., 'KAN').
    Filters out Done/Closed categories.
    """
    project = prefix_jira_name
    jql = (
        f"project = {project} AND issuetype = Epic "
        f"AND statusCategory != Done ORDER BY updated DESC"
    )
    data = search_issues(jql=jql, max_results=limit, fields=["summary", "description", "updated"])  
    return data.get("issues", [])


