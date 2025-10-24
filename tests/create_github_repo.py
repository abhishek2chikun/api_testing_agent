#!/usr/bin/env python3
"""
Script to create a GitHub repository for storing generated tests.
This only needs to be run once to set up your GitHub integration.
"""
import os
import sys
from dotenv import load_dotenv
from github import Github

def create_repo():
    """Create a GitHub repository for the API testing agent."""
    print("="*60)
    print("GitHub Repository Creator")
    print("="*60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    github_token = os.getenv('GITHUB_TOKEN')
    repo_full_name = os.getenv('REPO_FULL_NAME', '').strip()
    
    # Remove common mistakes
    if repo_full_name.endswith('.git'):
        repo_full_name = repo_full_name[:-4]
    if repo_full_name.startswith('git@github.com:'):
        repo_full_name = repo_full_name.replace('git@github.com:', '')
    if repo_full_name.startswith('https://github.com/'):
        repo_full_name = repo_full_name.replace('https://github.com/', '')
    
    if not github_token:
        print("❌ GITHUB_TOKEN not set in .env file")
        print("   Please add your GitHub Personal Access Token")
        return False
    
    if not repo_full_name or '/' not in repo_full_name:
        print("❌ REPO_FULL_NAME not properly configured")
        print("   Current value:", repo_full_name or "Not set")
        print("   Expected format: username/repo-name")
        print("   Example: abhishek2chikun/api_testing_demo")
        return False
    
    username, repo_name = repo_full_name.split('/', 1)
    
    print(f"GitHub Token: {github_token[:10]}...")
    print(f"Username: {username}")
    print(f"Repository Name: {repo_name}")
    print()
    
    try:
        # Connect to GitHub
        gh = Github(github_token)
        user = gh.get_user()
        print(f"✓ Connected as: {user.login}")
        print()
        
        # Check if repo already exists
        try:
            existing_repo = gh.get_repo(repo_full_name)
            print(f"✓ Repository already exists: {existing_repo.html_url}")
            print(f"  Description: {existing_repo.description or 'No description'}")
            print(f"  Private: {existing_repo.private}")
            print()
            print("You're all set! No need to create it.")
            return True
        except:
            pass  # Repo doesn't exist, we'll create it
        
        # Ask for confirmation
        print(f"About to create repository: {repo_full_name}")
        print(f"  Name: {repo_name}")
        print(f"  Owner: {username}")
        print(f"  Visibility: Private (recommended)")
        print()
        
        response = input("Create this repository? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Cancelled.")
            return False
        
        print()
        print("Creating repository...")
        
        # Create the repository
        repo = user.create_repo(
            name=repo_name,
            description="Auto-generated API tests from Jira Epics using AI",
            private=True,  # Make it private by default
            auto_init=True  # Initialize with README
        )
        
        print()
        print("="*60)
        print("✅ Repository created successfully!")
        print("="*60)
        print()
        print(f"Repository URL: {repo.html_url}")
        print(f"Clone URL: {repo.clone_url}")
        print(f"Default Branch: {repo.default_branch}")
        print()
        print("You can now push generated tests with:")
        print(f"  python3 test_orchestrator_flow.py EPIC-KEY --github")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("❌ Failed to create repository")
        print(f"Error: {str(e)}")
        print()
        
        if "Bad credentials" in str(e):
            print("Your GITHUB_TOKEN appears to be invalid or expired.")
            print("Create a new token at: https://github.com/settings/tokens")
        elif "already exists" in str(e).lower():
            print(f"Repository {repo_full_name} already exists!")
            print("You're good to go.")
            return True
        else:
            print("Please check:")
            print("  1. Your GITHUB_TOKEN is valid")
            print("  2. Token has 'repo' permission")
            print("  3. Repository name doesn't already exist")
        
        return False

if __name__ == '__main__':
    print()
    print("This script will create a GitHub repository for storing")
    print("auto-generated API tests from your Jira Epics.")
    print()
    
    try:
        success = create_repo()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

