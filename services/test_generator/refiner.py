"""
LLM-based refinement layer that takes review notes + epic + current tests
and returns corrected test files.

Input:
- issue_key: str
- epic: dict (Jira epic)
- contract: dict (openapi/endpoints/description)
- files: {path: content}
- notes: str (detailed reviewer notes)

Output:
- {path: corrected_content}
"""
import json
import os
from typing import Dict

from dotenv import load_dotenv
from openai import OpenAI
from config.loader import get_config_value

load_dotenv()

_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def _build_refine_prompt(issue_key: str, epic: Dict, contract: Dict, files: Dict[str, str], notes: str) -> str:
    fields = epic.get('fields', {})
    summary = fields.get('summary', '')
    description = fields.get('description', '')

    contract_hint = []
    if 'openapi_url' in contract:
        contract_hint.append(f"OPENAPI_URL: {contract['openapi_url']}")
    if 'openapi_spec' in contract:
        spec = contract['openapi_spec']
        title = spec.get('info', {}).get('title', 'N/A')
        version = spec.get('openapi', spec.get('swagger', 'N/A'))
        contract_hint.append(f"OPENAPI: {title} (v{version})")
    if 'endpoints' in contract:
        contract_hint.append(f"ENDPOINTS_LISTED: {len(contract['endpoints'])}")

    files_blob = []
    for path, content in files.items():
        files_blob.append(f"---TESTFILE: {path}---\n{content}\n---ENDTESTFILE---")
    files_text = "\n\n".join(files_blob)

    return (
        "You are a test code fixer. Using the reviewer notes, correct the provided tests so they are executable,"
        " aligned with the Epic and acceptance criteria, and free of hallucinations.\n\n"
        "Return only a JSON object with a single key 'files' mapping file paths to corrected content.\n"
        "Do not include any analysis text outside JSON.\n\n"
        f"ISSUE_KEY: {issue_key}\n"
        f"SUMMARY: {summary}\n"
        f"EPIC_DESCRIPTION:\n{description}\n\n"
        f"CONTRACT_HINTS: {', '.join(contract_hint)}\n\n"
        f"REVIEWER_NOTES (detailed):\n{notes}\n\n"
        f"CURRENT_FILES:\n{files_text}\n"
    )


def refine_tests_with_notes(issue_key: str, epic: Dict, contract: Dict, files: Dict[str, str], notes: str) -> Dict[str, str]:
    model = get_config_value('openai.review_model', get_config_value('openai.generation_model', 'gpt-4o-mini'))
    prompt = _build_refine_prompt(issue_key, epic, contract, files, notes)
    resp = _client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "Return valid JSON only with a 'files' object mapping paths to contents."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8000,
    )
    content = (resp.choices[0].message.content or "{}").strip()
    if content.startswith("```") and content.endswith("```"):
        content = content.strip("`\n")
    try:
        data = json.loads(content)
        return data.get('files') or {}
    except Exception:
        return {}


