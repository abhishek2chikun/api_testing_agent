#!/usr/bin/env python3
"""
Script to push Jenkinsfile to GitHub repository.
This sets up Jenkins integration for automated test execution.
"""
import os
import sys
from dotenv import load_dotenv
from github import Github

def setup_jenkins_integration():
    """Push Jenkinsfile to GitHub repository main branch."""
    print("="*60)
    print("Jenkins Integration Setup")
    print("="*60)
    print()
    
    # Load environment variables
    load_dotenv()
    
    github_token = os.getenv('GITHUB_TOKEN')
    repo_full_name = os.getenv('REPO_FULL_NAME', '').strip()
    
    # Clean up repo name
    if repo_full_name.endswith('.git'):
        repo_full_name = repo_full_name[:-4]
    if repo_full_name.startswith('git@github.com:'):
        repo_full_name = repo_full_name.replace('git@github.com:', '')
    
    if not github_token or not repo_full_name:
        print("❌ GitHub configuration not found")
        print("   Please run: python3 test_github_config.py")
        return False
    
    print(f"Repository: {repo_full_name}")
    print()
    
    try:
        # Connect to GitHub
        gh = Github(github_token)
        repo = gh.get_repo(repo_full_name)
        print(f"✓ Connected to repository: {repo.html_url}")
        print()
        
        # Read Jenkinsfile
        if not os.path.exists('Jenkinsfile'):
            print("❌ Jenkinsfile not found in current directory")
            return False
        
        with open('Jenkinsfile', 'r') as f:
            jenkinsfile_content = f.read()
        
        print(f"✓ Read Jenkinsfile ({len(jenkinsfile_content)} bytes)")
        print()
        
        # Check if Jenkinsfile already exists in repo
        try:
            existing_file = repo.get_contents('Jenkinsfile', ref='main')
            print("ℹ️  Jenkinsfile already exists in repository")
            print()
            
            response = input("Update existing Jenkinsfile? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("Cancelled.")
                return False
            
            # Update existing file
            repo.update_file(
                'Jenkinsfile',
                'Update Jenkinsfile for auto-detection of Python/Java tests',
                jenkinsfile_content,
                existing_file.sha,
                branch='main'
            )
            print("✓ Updated Jenkinsfile in repository")
            
        except:
            # File doesn't exist, create it
            repo.create_file(
                'Jenkinsfile',
                'Add Jenkinsfile for Jenkins pipeline automation',
                jenkinsfile_content,
                branch='main'
            )
            print("✓ Created Jenkinsfile in repository")
        
        print()
        print("="*60)
        print("✅ Jenkins Integration Setup Complete!")
        print("="*60)
        print()
        print("Next Steps:")
        print("1. Set up Jenkins (see JENKINS_SETUP.md for detailed guide)")
        print("2. Create Multibranch Pipeline job in Jenkins")
        print("3. Configure GitHub webhook for instant triggers")
        print("4. Test by running:")
        print(f"   python3 test_orchestrator_flow.py EPIC-KEY --github")
        print()
        print(f"Repository: {repo.html_url}")
        print(f"Jenkinsfile: {repo.html_url}/blob/main/Jenkinsfile")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("❌ Failed to setup Jenkins integration")
        print(f"Error: {str(e)}")
        return False

if __name__ == '__main__':
    try:
        success = setup_jenkins_integration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

