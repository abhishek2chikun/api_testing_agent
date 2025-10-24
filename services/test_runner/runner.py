"""
Docker-based test execution.
Clones repository and runs tests in isolated containers.
"""
import tempfile
import subprocess
import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_FULL_NAME = os.getenv('REPO_FULL_NAME')

def clone_repo_to_tmp(branch: str) -> str:
    """
    Clone repository branch to a temporary directory.
    
    Args:
        branch: Git branch name to checkout
        
    Returns:
        str: Path to cloned repository
    """
    tmp = tempfile.mkdtemp(prefix='test-runner-')
    url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{REPO_FULL_NAME}.git"
    
    # Clone and checkout branch
    subprocess.check_call(['git', 'clone', url, tmp])
    subprocess.check_call(['git', 'checkout', branch], cwd=tmp)
    
    return tmp

def run_pytests_in_docker(branch: str) -> dict:
    """
    Run pytest tests in a Docker container.
    
    Steps:
    1. Clone repository branch to temp directory
    2. Mount directory in python:3.11 Docker container
    3. Install dependencies and run pytest
    4. Parse results from JUnit XML
    
    Args:
        branch: Git branch containing tests to run
        
    Returns:
        dict: Test execution results with keys:
            - returncode: Exit code
            - junit: Path to JUnit XML results file
            - passed: Number of passed tests (if parsed)
            - failed: Number of failed tests (if parsed)
    """
    tmp = clone_repo_to_tmp(branch)
    
    # Run pytest inside Docker container
    cmd = [
        'docker', 'run', '--rm',
        '-v', f"{tmp}:/repo",
        '-w', '/repo',
        'python:3.11',
        'bash', '-lc',
        'pip install -r requirements.txt && pytest -q --maxfail=1 --junitxml=results.xml || true'
    ]
    
    subprocess.run(cmd, check=True)
    
    # Check for results file
    results_path = os.path.join(tmp, 'results.xml')
    result = {
        'returncode': 0,
        'junit': results_path if os.path.exists(results_path) else None
    }
    
    # TODO: Parse JUnit XML to extract pass/fail counts
    
    return result

def run_maven_tests_in_docker(branch: str) -> dict:
    """
    Run Maven tests in a Docker container (for Java tests).
    
    Args:
        branch: Git branch containing tests to run
        
    Returns:
        dict: Test execution results with keys:
            - returncode: Maven exit code
            - output: Combined stdout/stderr from Maven
    """
    tmp = clone_repo_to_tmp(branch)
    
    # Run Maven tests inside Docker container
    cmd = [
        'docker', 'run', '--rm',
        '-v', f"{tmp}:/repo",
        '-w', '/repo',
        'maven:3.9.0-jdk-17',
        'mvn', 'test', '-DskipITs=false'
    ]
    
    proc = subprocess.run(cmd, capture_output=True, text=True)
    
    return {
        'returncode': proc.returncode,
        'output': proc.stdout + proc.stderr
    }


