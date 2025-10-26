"""
Eligibility gate using OpenAI to decide if an Epic has sufficient info
to proceed with automated test generation.

Output JSON shape:
  {"should_proceed": true/false, "reason": "..."}
"""
import json
import os
from typing import Dict

from dotenv import load_dotenv
from openai import OpenAI

from integrations.jira.contract_parser import normalize_description, extract_openapi_url

load_dotenv()

_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def _build_gate_prompt(issue_key: str, epic: Dict, contract: Dict) -> str:
    fields = epic.get('fields', {})
    summary = fields.get('summary', '')
    description_raw = fields.get('description')
    description = normalize_description(description_raw) if description_raw else ''

    openapi_url = contract.get('openapi_url') or extract_openapi_url(description)
    endpoints_present = bool(contract.get('endpoints'))

    return (
        "You are a strict API readiness checker. "
        "Decide if the Jira Epic contains enough information to begin automated API test generation.\n\n"
        f"ISSUE_KEY: {issue_key}\n"
        f"SUMMARY: {summary}\n"
        f"DESCRIPTION: {description[:2000]}\n\n"
        "Signals available:\n"
        f"- openapi_url_present: {bool(openapi_url)}\n"
        f"- endpoints_listed: {endpoints_present}\n"
        "- If openapi_url_present, it should be accessible and return a valid OpenAPI/Swagger document.\n"
        "- Endpoints should be concrete and actionable.\n\n"
        "Return ONLY a compact JSON object with two fields and nothing else: \n"
        "{\n  \"should_proceed\": true|false,\n  \"reason\": \"short explanation\"\n}\n\n"
        "Decision policy:\n"
        "- If openapi_url_present and likely accessible OR endpoints_listed with sufficient detail, return should_proceed=true.\n"
        "- Otherwise, should_proceed=false with a concrete reason (e.g., missing OpenAPI URL, endpoints absent/unclear).\n"
    )


def check_epic_eligibility(issue_key: str, epic: Dict, contract: Dict, model: str = 'gpt-4o-mini') -> Dict:
    prompt = _build_gate_prompt(issue_key, epic, contract)
    resp = _client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "Return minimal valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=200,
    )
    content = resp.choices[0].message.content or "{}"
    # Be defensive against wrapping code fences
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content.strip("`\n")
    try:
        data = json.loads(content)
    except Exception:
        # Fallback: map common textual yes/no
        lowered = content.lower()
        should = 'true' in lowered or 'yes' in lowered
        data = {"should_proceed": should, "reason": content[:200]}
    # Normalize keys
    if 'should_prcodeed' in data:
        data['should_proceed'] = data.pop('should_prcodeed')
    return {
        "should_proceed": bool(data.get("should_proceed")),
        "reason": data.get("reason", "")[:500]
    }


