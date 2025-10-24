"""
GitHub API client for repository operations.
Handles branch creation and file commits.
"""
from github import Github
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_FULL_NAME = os.getenv('REPO_FULL_NAME')

def commit_files_to_branch(issue_key: str, files: dict) -> str:
    """
    Create a new branch and commit generated test files.
    
    Creates a new branch named: auto/tests/{issue_key}/{timestamp}
    Commits all files in the files dict to this branch.
    
    Args:
        issue_key: Jira issue key (used in branch name)
        files: Dict of {file_path: file_content} to commit
        
    Returns:
        str: Name of the created branch
        
    Raises:
        Exception: If GitHub API operations fail
    """
    # Validate configuration
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN not set in environment. Please configure your GitHub Personal Access Token.")
    
    if not REPO_FULL_NAME:
        raise ValueError("REPO_FULL_NAME not set in environment. Please configure as 'username/repo-name'.")
    
    # Clean up common mistakes
    repo_name = REPO_FULL_NAME
    
    # Remove git@ prefix if present
    if repo_name.startswith('git@github.com:'):
        repo_name = repo_name.replace('git@github.com:', '')
        logging.warning(f"Removed 'git@github.com:' prefix from REPO_FULL_NAME")
    
    # Remove .git suffix if present
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
        logging.warning(f"Removed '.git' suffix from REPO_FULL_NAME")
    
    # Remove https://github.com/ prefix if present
    if repo_name.startswith('https://github.com/'):
        repo_name = repo_name.replace('https://github.com/', '')
        logging.warning(f"Removed 'https://github.com/' prefix from REPO_FULL_NAME")
    
    if '/' not in repo_name:
        raise ValueError(
            f"REPO_FULL_NAME must be in 'username/repo-name' format, got: '{REPO_FULL_NAME}'\n"
            f"Correct format: 'abhishek2chikun/api_testing_demo'\n"
            f"Not: 'api_testing_demo' or 'api_testing_demo.git'"
        )
    
    # Update to use cleaned name
    repo_full_name = repo_name
    
    logging.info(f"[{issue_key}]   └─ Connecting to GitHub repo: {repo_full_name}")
    
    try:
        gh = Github(GITHUB_TOKEN)
        repo = gh.get_repo(repo_full_name)
    except Exception as e:
        logging.error(f"[{issue_key}] Failed to access GitHub repository: {repo_full_name}")
        logging.error(f"[{issue_key}] Error: {str(e)}")
        logging.error(f"[{issue_key}] ")
        logging.error(f"[{issue_key}] The repository doesn't exist or is not accessible.")
        logging.error(f"[{issue_key}] ")
        logging.error(f"[{issue_key}] To create the repository:")
        logging.error(f"[{issue_key}]   1. Go to: https://github.com/new")
        logging.error(f"[{issue_key}]   2. Repository name: {repo_full_name.split('/')[1]}")
        logging.error(f"[{issue_key}]   3. Make it Public or Private")
        logging.error(f"[{issue_key}]   4. Click 'Create repository'")
        logging.error(f"[{issue_key}] ")
        logging.error(f"[{issue_key}] Then run this command again.")
        raise
    
    # Get default branch reference (try main, master, or initialize empty repo)
    main_branch = None
    try:
        main_branch = repo.get_branch('main')
        logging.info(f"[{issue_key}]   └─ Using 'main' branch as base")
    except:
        try:
            main_branch = repo.get_branch('master')
            logging.info(f"[{issue_key}]   └─ Using 'master' branch as base")
        except:
            # Repository is empty, initialize it with a README
            logging.info(f"[{issue_key}]   └─ Repository is empty, initializing with README...")
            try:
                repo.create_file(
                    "README.md",
                    "Initialize repository",
                    "# API Testing Agent\n\nAuto-generated API tests from Jira Epics.\n",
                    branch='main'
                )
                logging.info(f"[{issue_key}]   └─ Created initial commit on 'main' branch")
                main_branch = repo.get_branch('main')
            except Exception as e:
                logging.error(f"[{issue_key}] Failed to initialize repository: {e}")
                raise
    
    # Create unique branch name with timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    branch_name = f"auto/tests/{issue_key}/{timestamp}"
    
    # Create new branch from main
    repo.create_git_ref(
        ref=f"refs/heads/{branch_name}",
        sha=main_branch.commit.sha
    )
    
    # Commit each file to the branch
    for path, content in files.items():
        try:
            # Try to create new file
            repo.create_file(
                path,
                f"Add generated tests for {issue_key}",
                content,
                branch=branch_name
            )
        except Exception:
            # File exists, update it
            existing = repo.get_contents(path, ref=branch_name)
            repo.update_file(
                path,
                f"Update generated tests for {issue_key}",
                content,
                existing.sha,
                branch=branch_name
            )
    
    return branch_name


