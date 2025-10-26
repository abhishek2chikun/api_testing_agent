"""
LLM-based review and fix layer for generated test files.

Goals:
- Validate syntax/executability and fix trivial issues (quotes, imports, missing fixtures)
- Check coverage vs Jira epic requirements and acceptance criteria
- Minimize hallucinations; ensure tests align with contract/description
- Score coverage/criteria/syntax and optionally return corrected files

Output JSON:
{
  "score": 0.0-1.0,
  "syntax_ok": true/false,
  "coverage_score": 0.0-1.0,
  "criteria_score": 0.0-1.0,
  "notes": "...",
  "files": { "path": "updated content" }   # optional if changes suggested or score < threshold
}
"""
import json
import os
from typing import Dict, Tuple

from dotenv import load_dotenv
from openai import OpenAI
from config.loader import get_config_value

load_dotenv()

_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def _build_review_prompt(issue_key: str, epic: Dict, contract: Dict, files: Dict[str, str]) -> str:
    fields = epic.get('fields', {})
    summary = fields.get('summary', '')
    description = fields.get('description', '')
    # Contract summary for context
    contract_hint = []
    if 'openapi_url' in contract:
        contract_hint.append(f"OPENAPI_URL: {contract['openapi_url']}")
    if 'openapi_spec' in contract:
        spec = contract['openapi_spec']
        title = spec.get('info', {}).get('title', 'N/A')
        version = spec.get('openapi', spec.get('swagger', 'N/A'))
        contract_hint.append(f"OPENAPI: {title} (v{version})")
        contract_hint.append(f"PATHS: {len(spec.get('paths', {}))}")
    if 'endpoints' in contract:
        contract_hint.append(f"ENDPOINTS_LISTED: {len(contract['endpoints'])}")

    files_blob = []
    for path, content in files.items():
        files_blob.append(f"---TESTFILE: {path}---\n{content}\n---ENDTESTFILE---")

    files_text = "\n\n".join(files_blob)

    threshold = get_config_value('openai.review_threshold', 0.7)
    return (
        "You are a meticulous test reviewer and fixer. Review the provided pytest/Java tests against the Jira Epic.\n"
        "Tasks:\n"
        "1) Ensure files are syntactically correct and executable; fix quotes/imports/fixtures/typos.\n"
        "2) Check tests cover the requirements from the Epic and acceptance criteria; add missing tests.\n"
        "3) Remove hallucinations or mismatched endpoints.\n\n"
        "Output strictly a compact JSON with keys: \n"
        "{\n  \"score\": float (0-1),\n  \"syntax_ok\": bool,\n  \"coverage_score\": float,\n  \"criteria_score\": float,\n  \"notes\": string (detailed, with concrete missing/incorrect items),\n  \"files\": {\"path\": \"corrected content\"} (optional; include only if changes are needed)\n}\n\n"
        f"If score < {threshold}, return corrected files in 'files'.\n\n"
        f"ISSUE_KEY: {issue_key}\n"
        f"SUMMARY: {summary}\n"
        f"EPIC_DESCRIPTION:\n{description}\n\n"
        f"CONTRACT_HINTS: {', '.join(contract_hint)}\n\n"
        f"FILES TO REVIEW:\n{files_text}\n"
    )


def review_and_fix_tests(issue_key: str, epic: Dict, contract: Dict, files: Dict[str, str]) -> Tuple[Dict, Dict[str, str]]:
    """
    Run LLM review. Returns (review_json, updated_files).
    updated_files is either empty (no changes) or contains corrected files.
    """
    model = get_config_value('openai.review_model', get_config_value('openai.generation_model', 'gpt-4o-mini'))
    prompt = _build_review_prompt(issue_key, epic, contract, files)
    resp = _client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": "Return valid JSON only. If changes required, include corrected files."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=6000,
    )
    content = (resp.choices[0].message.content or "{}").strip()
    if content.startswith("```") and content.endswith("```"):
        content = content.strip("`\n")
    try:
        data = json.loads(content)
    except Exception:
        data = {"score": 0.0, "syntax_ok": False, "coverage_score": 0.0, "criteria_score": 0.0, "notes": content[:4000]}

    updated_files = data.get("files") or {}
    return data, updated_files


