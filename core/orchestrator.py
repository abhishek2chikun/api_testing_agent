"""
Main orchestration logic for the test generation pipeline.
Coordinates between Jira, LLM, GitHub, and test execution services.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from integrations.jira.client import fetch_issue, post_comment
from integrations.jira.contract_parser import extract_contract
from services.test_generator.generator import generate_tests
from integrations.github.client import commit_files_to_branch
from services.test_runner.runner import run_pytests_in_docker, run_maven_tests_in_docker

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
        
        # Step 3: Generate Tests using LLM (Python/pytest or Java/RestAssured)
        framework = 'pytest' if language.lower() == 'python' else 'RestAssured'
        logging.info('[%s] Step 3/5: Generating %s tests with LLM', issue_key, framework)
        logging.info('[%s]   └─ Preparing prompt with OpenAPI spec + Epic details...', issue_key)
        
        generated_files = generate_tests(issue_key, epic, contract, language=language)
        
        logging.info('[%s] ✓ Generated %d test files:', issue_key, len(generated_files))
        for file_path in generated_files.keys():
            logging.info('[%s]   └─ %s', issue_key, file_path)
        
        # Step 4: Save Test Files Locally
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
    
    return summary


