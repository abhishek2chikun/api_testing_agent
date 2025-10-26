"""
Main orchestration logic for the test generation pipeline.
Coordinates between Jira, LLM, GitHub, and test execution services.
"""
import logging
import os
import json
import hashlib
import copy
from datetime import datetime
from pathlib import Path
from integrations.jira.client import fetch_issue, post_comment
from integrations.jira.contract_parser import extract_contract
from services.test_generator.generator import generate_tests
from integrations.github.client import commit_files_to_branch
from services.test_runner.runner import run_pytests_in_docker, run_maven_tests_in_docker
from services.test_generator.gating import check_epic_eligibility
from config.loader import get_config_value
from services.test_generator.reviewer import review_and_fix_tests
from services.test_generator.refiner import refine_tests_with_notes

logging.basicConfig(level=logging.INFO)

def process_epic(
    issue_key: str, 
    language: str = 'python',
    save_to_github: bool = True, 
    save_locally: bool = True
):
    """
    Main orchestration workflow for processing a Jira Epic.
    
    Steps:
    1. Fetch Epic details from Jira
    2. Extract & fetch API contract (OpenAPI spec robustly)
    3. Generate tests using LLM (Python/pytest or Java/RestAssured)
    4. Save generated test files locally
    5. Push to GitHub repository (triggers Jenkins pipeline)
    
    Args:
        issue_key: Jira issue key (e.g., 'EPIC-123')
        language: Test framework - 'python' (pytest) or 'java' (RestAssured)
        save_to_github: Whether to commit tests to GitHub (default: True, triggers Jenkins)
        save_locally: Whether to save tests locally (default: True)
    
    Returns:
        dict: Results with 'output_dir' and 'github_branch' (if pushed)
    """
    logging.info('[%s] ============================================================', issue_key)
    logging.info('[%s] Starting Test Generation Pipeline', issue_key)
    logging.info('[%s] Language: %s (%s)', issue_key, language.upper(), 
                 'pytest' if language == 'python' else 'RestAssured')
    logging.info('[%s] ============================================================', issue_key)
    
    results = {'output_dir': None, 'github_branch': None}
    gate_result = None
    ai2_generated_files_snapshot = None
    review_json = None
    refined = {}
    threshold = float(get_config_value('openai.review_threshold', 0.7))
    avg = None
    
    try:
        # Step 1: Fetch Epic from Jira
        logging.info('[%s] Step 1/5: Fetching Epic from Jira', issue_key)
        epic = fetch_issue(issue_key)
        epic_summary = epic.get('fields', {}).get('summary', 'N/A')
        logging.info('[%s] ✓ Epic fetched: %s', issue_key, epic_summary)
        
        # Step 2: Extract & Fetch OpenAPI Specification (Robustly)
        logging.info('[%s] Step 2/5: Extracting and fetching OpenAPI specification', issue_key)
        contract = extract_contract(epic, fetch_openapi=True)
        
        # Log what we found
        if 'openapi_spec' in contract:
            spec = contract['openapi_spec']
            logging.info('[%s] ✓ OpenAPI spec fetched successfully!', issue_key)
            logging.info('[%s]   └─ URL: %s', issue_key, contract.get('openapi_url'))
            logging.info('[%s]   └─ Version: %s', issue_key, spec.get('openapi', spec.get('swagger', 'N/A')))
            logging.info('[%s]   └─ Title: %s', issue_key, spec.get('info', {}).get('title', 'N/A'))
            logging.info('[%s]   └─ Paths: %d endpoints', issue_key, len(spec.get('paths', {})))
        elif 'openapi_url' in contract:
            logging.warning('[%s] ⚠ OpenAPI URL found but spec could not be fetched', issue_key)
            logging.warning('[%s]   URL: %s', issue_key, contract.get('openapi_url'))
        elif 'endpoints' in contract:
            logging.info('[%s] ✓ Extracted %d manual endpoints from Epic', issue_key, len(contract['endpoints']))
        else:
            logging.info('[%s] ✓ Using Epic description for test generation', issue_key)
        
        # Eligibility Gate (LLM) before generation
        try:
            gating_model = get_config_value('openai.gating_model', 'gpt-4o-mini')
            logging.info('[%s] Eligibility gate using model: %s', issue_key, gating_model)
            gate = check_epic_eligibility(issue_key, epic, contract, model=gating_model)
            gate_result = gate
            logging.info('[%s]   └─ Gate result: %s', issue_key, gate)
            logging.debug('[%s]   └─ Gate should_proceed=%s reason=%s', issue_key, gate.get('should_proceed'), gate.get('reason'))

            # Normalize key for user-requested spelling as well
            gate_json_for_comment = {
                'should_prcodeed': bool(gate.get('should_proceed')),  # preserves requested misspelling
                'reason': gate.get('reason', '')
            }

            if not gate.get('should_proceed'):
                msg = (
                    '🛑 Eligibility gate failed. Not proceeding with test generation.\n\n'
                    f"```\n{gate_json_for_comment}\n```"
                )
                try:
                    post_comment(issue_key, msg)
                except Exception as e:
                    logging.warning('[%s] Could not post gate result to Jira: %s', issue_key, str(e))
                logging.info('[%s] Skipping generation due to gate decision.', issue_key)
                return {'output_dir': None, 'github_branch': None, 'skipped': True}
        except Exception as e:
            logging.warning('[%s] Eligibility gate error (continuing): %s', issue_key, str(e))

        # Step 3: Generate Tests using LLM (Python/pytest or Java/RestAssured)
        framework = 'pytest' if language.lower() == 'python' else 'RestAssured'
        logging.info('[%s] Step 3/5: Generating %s tests with LLM', issue_key, framework)
        logging.info('[%s]   └─ Preparing prompt with OpenAPI spec + Epic details...', issue_key)
        
        generated_files = generate_tests(issue_key, epic, contract, language=language)
        ai2_generated_files_snapshot = copy.deepcopy(generated_files)
        
        logging.info('[%s] ✓ Generated %d test files:', issue_key, len(generated_files))
        for file_path in generated_files.keys():
            logging.info('[%s]   └─ %s', issue_key, file_path)

        # Review & Fix Layer (LLM)
        try:
            review_json, corrected = review_and_fix_tests(issue_key, epic, contract, generated_files)
            score = float(review_json.get('score', 0.0))
            logging.info('[%s] Review score: %.2f (syntax_ok=%s, coverage=%.2f, criteria=%.2f)',
                         issue_key,
                         score,
                         review_json.get('syntax_ok'),
                         float(review_json.get('coverage_score', 0.0)),
                         float(review_json.get('criteria_score', 0.0)))
            if review_json.get('notes'):
                notes_preview = str(review_json.get('notes'))
                logging.debug('[%s] Review notes (first 500 chars): %s', issue_key, notes_preview[:500])
            if corrected:
                logging.info('[%s] Applying reviewer corrections to %d files', issue_key, len(corrected))
                generated_files.update(corrected)

            # Threshold-based refinement pass
            avg = (float(review_json.get('coverage_score', 0.0)) + float(review_json.get('criteria_score', 0.0)) + (1.0 if review_json.get('syntax_ok') else 0.0)) / 3.0
            logging.info('[%s] Review average=%.3f threshold=%.3f (<= triggers refine: %s)', issue_key, avg, threshold, avg <= threshold)
            if avg <= threshold:
                logging.info('[%s] Refinement triggered due to average <= threshold', issue_key)
                try:
                    files_before_refine = copy.deepcopy(generated_files)
                    refined = refine_tests_with_notes(issue_key, epic, contract, generated_files, review_json.get('notes', ''))
                    applied = False
                    if refined:
                        logging.info('[%s] Applied refinement changes to %d files', issue_key, len(refined))
                        generated_files.update(refined)
                        applied = True
                    # Build refinement metadata summary (always when triggered)
                    refine_changes = []
                    # Compute diffs between before and after
                    for path, after in generated_files.items():
                        before = files_before_refine.get(path)
                        if before is None and path in (refined or {}):
                            refine_changes.append({
                                'path': path,
                                'change': 'added',
                            })
                        elif before is not None and after != before:
                            refine_changes.append({
                                'path': path,
                                'change': 'modified',
                                'before_sha256': hashlib.sha256(before.encode('utf-8')).hexdigest(),
                                'after_sha256': hashlib.sha256(after.encode('utf-8')).hexdigest(),
                                'before_lines': len(before.splitlines()),
                                'after_lines': len(after.splitlines())
                            })
                    refined_meta = {
                        'triggered': True,
                        'applied': applied,
                        'threshold': threshold,
                        'average_score': round(avg, 4),
                        'coverage_score': review_json.get('coverage_score'),
                        'criteria_score': review_json.get('criteria_score'),
                        'syntax_ok': review_json.get('syntax_ok'),
                        'changes': refine_changes
                    }
                except Exception as ref_e:
                    logging.warning('[%s] Refinement layer error (continuing): %s', issue_key, str(ref_e))
            else:
                logging.info('[%s] Refinement skipped (avg=%.3f > threshold=%.3f)', issue_key, avg, threshold)
        except Exception as e:
            logging.warning('[%s] Review layer error (continuing): %s', issue_key, str(e))

        # Consolidated AI metadata (gate, testcases, reviewer, refiner)
        try:
            # If refined_meta not created (no trigger), create default structure
            if 'refined_meta' not in locals():
                refined_meta = {
                    'triggered': False,
                    'applied': False,
                    'threshold': threshold,
                    'average_score': round(avg, 4) if avg is not None else None,
                    'coverage_score': review_json.get('coverage_score') if review_json else None,
                    'criteria_score': review_json.get('criteria_score') if review_json else None,
                    'syntax_ok': review_json.get('syntax_ok') if review_json else None,
                    'changes': []
                }

            ai_metadata = {
                'issue_key': issue_key,
                'language': language,
                'gate': gate_result,
                'test_cases': ai2_generated_files_snapshot,  # AI-2 raw output before review/refine
                'reviewer': review_json,
                'review_average': round(avg, 4) if avg is not None else None,
                'review_threshold': threshold,
                'refiner_output': refined,
                'refinement_metadata': refined_meta,
            }
            generated_files['metadata.json'] = json.dumps(ai_metadata, indent=2)
            logging.info('[%s] Wrote AI metadata file metadata.json', issue_key)
        except Exception as e:
            logging.warning('[%s] Failed to build AI metadata: %s', issue_key, str(e))
        
        # Step 4: Save Test Files Locally (with review report)
        if save_locally:
            logging.info('[%s] Step 4/5: Saving test files locally', issue_key)
            output_dir = save_tests_locally(issue_key, generated_files, language)
            results['output_dir'] = output_dir
            logging.info('[%s] ✓ Tests saved to: %s', issue_key, output_dir)
        
        # Step 5: Push to GitHub (Triggers Jenkins Pipeline)
        if save_to_github:
            logging.info('[%s] Step 5/5: Pushing tests to GitHub repository', issue_key)
            logging.info('[%s]   └─ This will trigger Jenkins pipeline for test execution', issue_key)
            
            branch = commit_files_to_branch(issue_key, generated_files)
            results['github_branch'] = branch
            
            logging.info('[%s] ✓ Tests pushed to GitHub branch: %s', issue_key, branch)
            logging.info('[%s]   └─ Jenkins pipeline will be triggered automatically', issue_key)
            
            # Post success to Jira
            try:
                summary = format_github_commit_summary(issue_key, branch, output_dir, language, len(generated_files))
                post_comment(issue_key, summary)
                logging.info('[%s] ✓ Posted commit info to Jira Epic', issue_key)
            except Exception as e:
                logging.warning('[%s] Could not post to Jira: %s', issue_key, str(e))
        
        logging.info('[%s] ============================================================', issue_key)
        logging.info('[%s] ✅ Pipeline Completed Successfully!', issue_key)
        logging.info('[%s] ============================================================', issue_key)
        
        return results
        
    except Exception as e:
        error_msg = f"Pipeline failed: {str(e)}"
        logging.error('[%s] ❌ %s', issue_key, error_msg)
        
        # Try to post error to Jira
        try:
            post_comment(issue_key, f"❌ **Test generation failed**\n\n```\n{str(e)}\n```")
        except Exception as jira_error:
            logging.error('[%s] Could not post error to Jira: %s', issue_key, jira_error)
        
        raise

def save_tests_locally(issue_key: str, generated_files: dict, language: str = 'python') -> str:
    """
    Save generated test files to local output directory.
    
    Creates directory structure: output/{epic_id}_{datetime}/
    
    Args:
        issue_key: Jira issue key (e.g., 'EPIC-123')
        generated_files: Dict of {file_path: file_content}
        language: Test framework used ('python' or 'java')
        
    Returns:
        str: Path to created output directory
    """
    # Create output directory name: output/EPIC-123_20231023_143022/
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('output') / f"{issue_key}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logging.info('[%s]   └─ Creating directory: %s', issue_key, output_dir)
    
    # Save each generated file
    for file_path, content in generated_files.items():
        # Create full path (preserve directory structure from LLM)
        full_path = output_dir / file_path
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        full_path.write_text(content, encoding='utf-8')
        logging.info('[%s]     ✓ %s (%d bytes)', issue_key, file_path, len(content))
    
    # Create a summary file
    framework = 'pytest' if language == 'python' else 'RestAssured'
    summary_path = output_dir / 'GENERATION_INFO.txt'
    summary_content = f"""Test Generation Summary
=====================
Epic Key: {issue_key}
Framework: {framework} ({language})
Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Files: {len(generated_files)}

Generated Files:
"""
    for file_path in generated_files.keys():
        summary_content += f"  - {file_path}\n"
    
    summary_content += f"""
Next Steps:
-----------
1. Review generated tests in: {output_dir}
2. Tests have been pushed to GitHub (if configured)
3. Jenkins pipeline will run tests automatically
"""
    
    summary_path.write_text(summary_content, encoding='utf-8')
    logging.info('[%s]     ✓ GENERATION_INFO.txt', issue_key)

    # metadata.json will be created later in orchestrator after LLM passes
    
    return str(output_dir)

def format_github_commit_summary(
    issue_key: str,
    branch: str, 
    output_dir: str = None, 
    language: str = 'python',
    file_count: int = 0
) -> str:
    """
    Format GitHub commit summary for Jira comment.
    
    Args:
        issue_key: Jira issue key
        branch: GitHub branch name
        output_dir: Local output directory path (optional)
        language: Test framework used
        file_count: Number of generated files
        
    Returns:
        str: Formatted summary for Jira comment
    """
    framework = 'pytest' if language == 'python' else 'RestAssured'
    
    summary = f"""🤖 **Automated Test Generation Complete**

**Epic:** {issue_key}
**Framework:** {framework} ({language.upper()})
**Generated Files:** {file_count}
**GitHub Branch:** `{branch}`

✅ Tests have been generated and pushed to GitHub repository.

🔄 **Next Steps:**
- Jenkins pipeline will automatically run the tests
- Test results will be posted once execution completes
- Review the generated tests in the GitHub branch

📁 View tests: [GitHub Branch]
"""
    
    if output_dir:
        summary += f"\n📂 Local copy saved to: `{output_dir}`"
    
    # Add review note if present
    summary += "\n\n🧪 Review Layer: Executability, Coverage, Criteria checked."
    
    return summary


