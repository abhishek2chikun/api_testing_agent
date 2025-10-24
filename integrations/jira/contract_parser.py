"""
API contract extraction from Jira Epic descriptions.
Parses Epic descriptions to find OpenAPI specs or endpoint definitions.
Handles both plain text and Atlassian Document Format (ADF).
Fetches and parses OpenAPI specifications when URLs are found.
"""
import re
import requests
import logging
from typing import Dict, List, Union, Optional

logging.basicConfig(level=logging.INFO)

def extract_contract(epic_json: dict, fetch_openapi: bool = True) -> dict:
    """
    Extract API contract information from Jira Epic.
    
    Supports multiple formats:
    1. OpenAPI/Swagger URL in description (can fetch and parse spec)
    2. Inline endpoint definitions (e.g., "POST /users")
    3. Plain text description as fallback
    
    Args:
        epic_json: Full Jira issue JSON response
        fetch_openapi: If True, fetch and parse OpenAPI spec from URL
        
    Returns:
        dict: Extracted contract with one of:
            - {'openapi_url': str, 'openapi_spec': dict} - if OpenAPI fetched
            - {'openapi_url': str} - if OpenAPI URL found but not fetched
            - {'endpoints': List[dict]} - if endpoint definitions found
            - {'description': str} - fallback to description text
    """
    desc_field = epic_json.get('fields', {}).get('description')
    
    # Convert description to plain text (handles ADF format from Jira API v3)
    desc = normalize_description(desc_field)
    
    if not desc:
        return {'description': ''}
    
    # Try to find OpenAPI/Swagger URL
    openapi_url = extract_openapi_url(desc)
    if openapi_url:
        contract = {'openapi_url': openapi_url}
        
        # Fetch and parse OpenAPI spec if requested
        if fetch_openapi:
            openapi_spec = fetch_openapi_spec(openapi_url)
            if openapi_spec:
                contract['openapi_spec'] = openapi_spec
                logging.info(f"Successfully fetched OpenAPI spec from {openapi_url}")
            else:
                logging.warning(f"Failed to fetch OpenAPI spec from {openapi_url}")
        
        return contract
    
    # Try to find endpoint definitions
    endpoints = extract_endpoints(desc)
    if endpoints:
        return {'endpoints': endpoints}
    
    # Fallback: return description
    return {'description': desc}

def normalize_description(desc_field: Union[str, dict, None]) -> str:
    """
    Normalize Jira description field to plain text.
    
    Jira API v3 returns descriptions in Atlassian Document Format (ADF),
    which is a JSON structure. This function extracts plain text from ADF
    or returns the string as-is if it's already plain text.
    
    Args:
        desc_field: Description field from Jira API (can be str, dict, or None)
        
    Returns:
        str: Plain text description
    """
    if not desc_field:
        return ''
    
    # If it's already a string, return it
    if isinstance(desc_field, str):
        return desc_field
    
    # If it's a dict (ADF format), extract text
    if isinstance(desc_field, dict):
        return extract_text_from_adf(desc_field)
    
    # Fallback: convert to string
    return str(desc_field)

def extract_text_from_adf(adf: dict) -> str:
    """
    Extract plain text from Atlassian Document Format (ADF).
    
    ADF is a JSON structure used by Jira API v3 for rich text content.
    This function recursively extracts all text nodes.
    
    Args:
        adf: ADF document structure
        
    Returns:
        str: Extracted plain text
    """
    if not isinstance(adf, dict):
        return ''
    
    text_parts = []
    
    # Check for text content in current node
    if 'text' in adf:
        text_parts.append(adf['text'])
    
    # Recursively process content array
    if 'content' in adf and isinstance(adf['content'], list):
        for item in adf['content']:
            text_parts.append(extract_text_from_adf(item))
    
    # Join with appropriate separators
    result = ' '.join(filter(None, text_parts))
    
    # Add newline after paragraphs and headings
    node_type = adf.get('type', '')
    if node_type in ['paragraph', 'heading']:
        result += '\n'
    
    return result

def extract_openapi_url(text: str) -> Union[str, None]:
    """
    Extract OpenAPI/Swagger URL from text.
    
    Matches URLs containing:
    - /openapi.json, /openapi.yaml
    - /swagger.json, /swagger.yaml  
    - /openapi (without extension)
    - /swagger (without extension)
    - /docs, /api-docs (common patterns)
    
    Args:
        text: Text to search for OpenAPI URL
        
    Returns:
        str: OpenAPI URL if found, None otherwise
    """
    if not text or not isinstance(text, str):
        return None
    
    # Pattern matches URLs with openapi/swagger in path
    # Handles both with and without file extensions
    pattern = r'(https?://[^\s]+?(?:/(?:openapi|swagger|api-docs|docs)(?:\.(?:json|yaml|yml))?(?:/|(?=\s)|$)))'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        url = match.group(1).rstrip('/')
        # Try appending .json if no extension
        if not url.endswith(('.json', '.yaml', '.yml')):
            # For localhost or common patterns, try .json first
            logging.info(f"Found OpenAPI URL without extension: {url}, will try {url}.json first")
        return url
    
    return None

def extract_endpoints(text: str) -> List[Dict[str, str]]:
    """
    Extract HTTP endpoint definitions from text.
    
    Looks for lines like:
    - GET /users
    - POST /users
    - PUT /users/{id}
    - DELETE /users/{id}
    
    Args:
        text: Text to search for endpoint definitions
        
    Returns:
        List[dict]: List of endpoints with 'method' and 'path' keys
    """
    if not text or not isinstance(text, str):
        return []
    
    lines = text.splitlines()
    endpoints = []
    
    for line in lines:
        line = line.strip()
        # Check if line starts with HTTP method
        if line.upper().startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'PATCH ')):
            parts = line.split()
            if len(parts) >= 2:
                endpoints.append({
                    'method': parts[0].upper(),
                    'path': parts[1]
                })
    
    return endpoints

def fetch_openapi_spec(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Fetch and parse OpenAPI specification from URL.
    
    Tries multiple strategies:
    1. Direct URL as-is
    2. Append .json if no extension
    3. Append .yaml if .json fails
    
    Args:
        url: URL to OpenAPI/Swagger specification (JSON or YAML)
        timeout: Request timeout in seconds
        
    Returns:
        dict: Parsed OpenAPI specification, or None if fetch fails
    """
    # List of URLs to try
    urls_to_try = [url]
    
    # If URL doesn't end with known extension, try adding extensions
    if not url.endswith(('.json', '.yaml', '.yml')):
        urls_to_try.append(f"{url}.json")
        urls_to_try.append(f"{url}.yaml")
    
    last_error = None
    
    for try_url in urls_to_try:
        try:
            logging.info(f"Fetching OpenAPI spec from: {try_url}")
            response = requests.get(try_url, timeout=timeout)
            response.raise_for_status()
            
            # Try to parse as JSON first
            try:
                spec = response.json()
                logging.info(f"Successfully parsed OpenAPI spec as JSON from {try_url}")
                return spec
            except ValueError:
                # If JSON fails, try YAML
                try:
                    import yaml
                    spec = yaml.safe_load(response.text)
                    logging.info(f"Successfully parsed OpenAPI spec as YAML from {try_url}")
                    return spec
                except Exception as e:
                    logging.error(f"Failed to parse OpenAPI spec as YAML: {e}")
                    last_error = e
                    continue
        
        except requests.exceptions.RequestException as e:
            logging.debug(f"Failed to fetch from {try_url}: {e}")
            last_error = e
            continue
        except Exception as e:
            logging.debug(f"Unexpected error fetching from {try_url}: {e}")
            last_error = e
            continue
    
    # All attempts failed
    logging.error(f"Failed to fetch OpenAPI spec from any URL variant. Last error: {last_error}")
    return None


