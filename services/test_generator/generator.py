"""
Main test generation orchestration using LLM.
Coordinates prompt building and LLM interaction.
"""
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from config.loader import get_config_value
from services.test_generator.prompts import PYTEST_PROMPT_TEMPLATE, JAVA_PROMPT_TEMPLATE

load_dotenv()

# Initialize OpenAI client (new API v1.0+)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_tests(issue_key: str, epic: dict, contract: dict, language: str = 'python') -> dict:
    """
    Generate API tests using LLM based on Epic requirements.
    
    Args:
        issue_key: Jira issue key
        epic: Full Epic JSON from Jira
        contract: Extracted API contract (OpenAPI spec, endpoints, or description)
        language: Target test language ('python' or 'java')
        
    Returns:
        dict: Generated test files as {file_path: file_content}
    """
    # Select appropriate prompt template
    if language.lower() == 'java':
        prompt_template = JAVA_PROMPT_TEMPLATE
    else:
        prompt_template = PYTEST_PROMPT_TEMPLATE
    
    # Extract Epic details
    fields = epic.get('fields', {})
    epic_summary = fields.get('summary', 'N/A')
    epic_description = fields.get('description', '')
    
    # If description is ADF format, it's already converted to text by contract_parser
    # But we get the normalized version from the contract extraction process
    from integrations.jira.contract_parser import normalize_description
    epic_description = normalize_description(epic_description) if epic_description else 'No description provided'
    
    # Format contract details for the prompt
    contract_details = format_contract_for_prompt(contract)
    
    # Build prompt with Epic context and contract
    prompt = prompt_template.format(
        issue_key=issue_key,
        epic_summary=epic_summary,
        epic_description=epic_description,
        contract_details=contract_details
    )
    
    # Call LLM
    generated_text = call_llm(prompt)
    
    # Parse test files from LLM output
    files = parse_test_files(generated_text)
    
    return files

def format_contract_for_prompt(contract: dict) -> str:
    """
    Format contract data into a readable string for the LLM prompt.
    
    Args:
        contract: Extracted contract (OpenAPI spec, endpoints, or description)
        
    Returns:
        str: Formatted contract details
    """
    if 'openapi_spec' in contract:
        # Full OpenAPI spec is available
        spec = contract['openapi_spec']
        details = f"""TYPE: OpenAPI Specification
URL: {contract.get('openapi_url', 'N/A')}
VERSION: {spec.get('openapi', spec.get('swagger', 'N/A'))}
TITLE: {spec.get('info', {}).get('title', 'N/A')}
DESCRIPTION: {spec.get('info', {}).get('description', 'N/A')}

FULL OPENAPI SPEC:
```json
{format_openapi_spec(spec)}
```

NOTE: Use this OpenAPI specification to generate comprehensive tests. 
Include Schemathesis property tests that validate all endpoints against the schema.
"""
        return details
    
    elif 'openapi_url' in contract:
        # Only URL is available (spec not fetched)
        return f"""TYPE: OpenAPI Specification (URL only - spec not fetched)
URL: {contract['openapi_url']}

NOTE: Fetch the OpenAPI spec from this URL and generate comprehensive tests.
"""
    
    elif 'endpoints' in contract:
        # Manual endpoint definitions
        endpoints = contract['endpoints']
        endpoint_list = '\n'.join([f"  - {ep['method']} {ep['path']}" for ep in endpoints])
        return f"""TYPE: Endpoint Definitions
TOTAL ENDPOINTS: {len(endpoints)}

ENDPOINTS:
{endpoint_list}

NOTE: Generate tests for each endpoint listed above. Include tests for:
- Valid requests with proper data
- Invalid data and validation errors
- Authentication/authorization if applicable
- Error cases (404, 500, etc.)
"""
    
    else:
        # Plain description fallback
        description = contract.get('description', 'No contract information available')
        return f"""TYPE: Plain Description

DESCRIPTION:
{description}

NOTE: Based on the description above, infer reasonable API endpoints and generate appropriate tests.
"""

def format_openapi_spec(spec: dict, max_length: int = 8000) -> str:
    """
    Format OpenAPI spec for inclusion in prompt.
    Truncate if too long to avoid token limits.
    
    Args:
        spec: OpenAPI specification dict
        max_length: Maximum character length
        
    Returns:
        str: JSON-formatted spec (potentially truncated)
    """
    import json
    
    # Create a simplified version with just the essential parts
    simplified = {
        'openapi': spec.get('openapi', spec.get('swagger')),
        'info': spec.get('info', {}),
        'servers': spec.get('servers', []),
        'paths': spec.get('paths', {}),
        'components': {
            'schemas': spec.get('components', {}).get('schemas', spec.get('definitions', {}))
        }
    }
    
    formatted = json.dumps(simplified, indent=2)
    
    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length] + '\n... (truncated)'
    
    return formatted

def call_llm(prompt: str, model: str = None) -> str:
    """
    Call OpenAI LLM for test generation using the new API (v1.0+).
    
    Args:
        prompt: Formatted prompt with Epic details
        model: OpenAI model to use (default: gpt-4o-mini)
        
    Returns:
        str: LLM-generated response text
    """
    # Choose model from config default if not provided
    model_name = model or get_config_value('openai.generation_model', 'gpt-4o-mini')

    messages = [
        {
            "role": "system",
            "content": "You are a senior test engineer that outputs code files delimited by markers."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    # Use new OpenAI API (v1.0+)
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.0,
        max_tokens=4000  # Increased for longer test files
    )
    
    return response.choices[0].message.content

def parse_test_files(text: str) -> dict:
    """
    Parse test files from LLM output using markers.
    
    Expected format:
    ---TESTFILE: path/to/file.py---
    file contents here
    ---ENDTESTFILE---
    
    Args:
        text: LLM-generated text with file markers
        
    Returns:
        dict: Parsed files as {file_path: file_content}
    """
    files = {}
    
    # Regex pattern to extract files between markers
    pattern = r"---TESTFILE:\s*(?P<path>.*?)\s*---\n(?P<content>.*?)(?=---ENDTESTFILE---)"
    
    for match in re.finditer(pattern, text, re.DOTALL):
        path = match.group('path').strip()
        content = match.group('content').rstrip()
        files[path] = content
    
    # Fallback: if no markers found, save entire output
    if not files:
        files['generated_tests.txt'] = text
    
    return files


