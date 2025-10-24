#!/usr/bin/env python3
"""
Test script to verify GitHub configuration.
Run this before enabling GitHub push to ensure your setup is correct.
"""
import os
import sys
from dotenv import load_dotenv
from github import Github

def test_github_config():
    """Test GitHub configuration and connectivity."""
    print("="*60)
    print("GitHub Configuration Test")
    print("="*60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    github_token = os.getenv('GITHUB_TOKEN')
    repo_full_name = os.getenv('REPO_FULL_NAME')
    
    # Test 1: Check if variables are set
    print("1️⃣  Checking environment variables...")
    if not github_token:
        print("❌ GITHUB_TOKEN not set in .env file")
        print("   Please add: GITHUB_TOKEN=ghp_your_token_here")
        return False
    
    if not repo_full_name:
        print("❌ REPO_FULL_NAME not set in .env file")
        print("   Please add: REPO_FULL_NAME=username/repo-name")
        return False
    
    print(f"✓ GITHUB_TOKEN: {github_token[:10]}...")
    print(f"✓ REPO_FULL_NAME: {repo_full_name}")
    print()
    
    # Test 2: Validate format
    print("2️⃣  Validating REPO_FULL_NAME format...")
    if '/' not in repo_full_name:
        print(f"❌ REPO_FULL_NAME must be in 'username/repo-name' format")
        print(f"   Current value: '{repo_full_name}'")
        print(f"   Example: 'abhishek2panigrahi/api_testing_demo'")
        return False
    
    username, repo_name = repo_full_name.split('/', 1)
    print(f"✓ Username: {username}")
    print(f"✓ Repository: {repo_name}")
    print()
    
    # Test 3: Test GitHub connectivity
    print("3️⃣  Testing GitHub API connectivity...")
    try:
        gh = Github(github_token)
        user = gh.get_user()
        print(f"✓ Connected as: {user.login}")
        print(f"  Name: {user.name}")
        print(f"  Email: {user.email or 'Not public'}")
        print()
    except Exception as e:
        print(f"❌ Failed to connect to GitHub API")
        print(f"   Error: {str(e)}")
        print(f"   Please check your GITHUB_TOKEN")
        return False
    
    # Test 4: Test repository access
    print("4️⃣  Testing repository access...")
    try:
        repo = gh.get_repo(repo_full_name)
        print(f"✓ Repository found: {repo.full_name}")
        print(f"  Description: {repo.description or 'No description'}")
        print(f"  Default branch: {repo.default_branch}")
        print(f"  Private: {repo.private}")
        print()
    except Exception as e:
        print(f"❌ Failed to access repository: {repo_full_name}")
        print(f"   Error: {str(e)}")
        print()
        print("   Possible issues:")
        print("   1. Repository doesn't exist")
        print("   2. Repository name is incorrect")
        print("   3. Token doesn't have access to this repository")
        print()
        print("   To create a new repository:")
        print(f"   - Go to: https://github.com/new")
        print(f"   - Or use existing repo with correct username/repo-name")
        return False
    
    # Test 5: Check write permissions
    print("5️⃣  Checking write permissions...")
    try:
        permissions = repo.permissions
        if not permissions.push:
            print("❌ Token doesn't have write access to repository")
            print("   Please ensure your token has 'repo' scope")
            return False
        print("✓ Write access confirmed")
        print()
    except Exception as e:
        print(f"⚠  Could not verify permissions: {str(e)}")
        print()
    
    # Success!
    print("="*60)
    print("✅ All tests passed!")
    print("="*60)
    print()
    print("Your GitHub integration is ready to use.")
    print(f"Tests will be pushed to: {repo_full_name}")
    print()
    print("To test with a Jira Epic:")
    print(f"  python3 test_orchestrator_flow.py EPIC-KEY --github")
    print()
    return True

if __name__ == '__main__':
    try:
        success = test_github_config()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

