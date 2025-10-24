#!/usr/bin/env python3
"""
Test script to verify Jenkins integration with the last committed branch.
This script helps you test if Jenkins is properly set up and can run your tests.
"""
import os
import sys
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def check_jenkins_connection(jenkins_url, username=None, api_token=None):
    """Check if Jenkins is running and accessible."""
    print("="*60)
    print("🔧 Jenkins Connection Test")
    print("="*60)
    print()
    
    print(f"Jenkins URL: {jenkins_url}")
    print()
    
    try:
        # Try to access Jenkins
        auth = (username, api_token) if username and api_token else None
        response = requests.get(f"{jenkins_url}/api/json", auth=auth, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Jenkins is running!")
            print(f"   Version: {data.get('version', 'Unknown')}")
            print()
            return True
        elif response.status_code == 403:
            print("❌ Jenkins is running but authentication failed")
            print("   Please check your JENKINS_USER and JENKINS_TOKEN")
            return False
        else:
            print(f"⚠️  Jenkins responded with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Jenkins")
        print(f"   Make sure Jenkins is running at: {jenkins_url}")
        print()
        print("To start Jenkins:")
        print("  - macOS: brew services start jenkins-lts")
        print("  - Docker: docker run -p 8080:8080 jenkins/jenkins:lts")
        print("  - Linux: sudo systemctl start jenkins")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def check_job_exists(jenkins_url, job_name, username=None, api_token=None):
    """Check if the multibranch pipeline job exists."""
    print("="*60)
    print("📋 Checking Jenkins Job")
    print("="*60)
    print()
    
    auth = (username, api_token) if username and api_token else None
    
    try:
        response = requests.get(
            f"{jenkins_url}/job/{job_name}/api/json",
            auth=auth,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Job '{job_name}' exists!")
            print(f"   Type: {data.get('_class', 'Unknown')}")
            print()
            
            # List branches
            if 'jobs' in data:
                branches = [job['name'] for job in data['jobs']]
                print(f"   Found {len(branches)} branch(es):")
                for branch in branches[:5]:  # Show first 5
                    print(f"     - {branch}")
                if len(branches) > 5:
                    print(f"     ... and {len(branches) - 5} more")
                print()
            
            return True
        elif response.status_code == 404:
            print(f"❌ Job '{job_name}' not found")
            print()
            print("To create the job:")
            print("  1. Go to Jenkins → New Item")
            print("  2. Enter name: API-Testing-Agent")
            print("  3. Select: Multibranch Pipeline")
            print("  4. Configure GitHub source")
            print("  5. Set branch filter: auto/tests/*")
            print()
            return False
        else:
            print(f"⚠️  Error checking job: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def get_latest_test_branch(jenkins_url, job_name, username=None, api_token=None):
    """Get the latest auto/tests/* branch."""
    auth = (username, api_token) if username and api_token else None
    
    try:
        response = requests.get(
            f"{jenkins_url}/job/{job_name}/api/json",
            auth=auth,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'jobs' in data:
                # Filter for auto/tests branches
                test_branches = [
                    job for job in data['jobs'] 
                    if job['name'].startswith('auto%2Ftests%2F') or 
                       job['name'].startswith('auto/tests/')
                ]
                
                if test_branches:
                    # Return the most recent one
                    return test_branches[0]['name']
        
        return None
    except:
        return None

def check_build_status(jenkins_url, job_name, branch_name, username=None, api_token=None):
    """Check the build status of a specific branch."""
    print("="*60)
    print("🔨 Build Status")
    print("="*60)
    print()
    
    auth = (username, api_token) if username and api_token else None
    
    # URL encode branch name
    encoded_branch = branch_name.replace('/', '%2F')
    
    try:
        response = requests.get(
            f"{jenkins_url}/job/{job_name}/job/{encoded_branch}/api/json",
            auth=auth,
            timeout=5
        )
        
        if response.status_code == 404:
            print(f"⚠️  Branch '{branch_name}' not found in Jenkins")
            print()
            print("Possible reasons:")
            print("  1. Branch hasn't been scanned yet")
            print("  2. Branch doesn't match filter (auto/tests/*)")
            print("  3. Jenkins needs manual scan")
            print()
            print("Try manually scanning:")
            print(f"  {jenkins_url}/job/{job_name}/build")
            return None
        
        if response.status_code != 200:
            print(f"❌ Error getting branch info: HTTP {response.status_code}")
            return None
        
        data = response.json()
        
        # Get last build
        last_build = data.get('lastBuild')
        if not last_build:
            print("ℹ️  No builds found for this branch yet")
            print()
            print("Branch is configured but hasn't been built.")
            print("Trigger a build manually or wait for automatic scan.")
            return None
        
        build_number = last_build.get('number')
        build_url = last_build.get('url')
        
        # Get build details
        build_response = requests.get(f"{build_url}api/json", auth=auth, timeout=5)
        build_data = build_response.json()
        
        result = build_data.get('result', 'IN_PROGRESS')
        building = build_data.get('building', False)
        duration = build_data.get('duration', 0) / 1000  # Convert to seconds
        
        print(f"Branch: {branch_name}")
        print(f"Build: #{build_number}")
        print(f"URL: {build_url}")
        print()
        
        if building:
            print("Status: 🔄 IN PROGRESS")
            print()
            return 'BUILDING'
        elif result == 'SUCCESS':
            print("Status: ✅ SUCCESS")
            print(f"Duration: {duration:.1f}s")
            print()
            
            # Try to get test results
            try:
                test_response = requests.get(
                    f"{build_url}testReport/api/json",
                    auth=auth,
                    timeout=5
                )
                if test_response.status_code == 200:
                    test_data = test_response.json()
                    passed = test_data.get('passCount', 0)
                    failed = test_data.get('failCount', 0)
                    skipped = test_data.get('skipCount', 0)
                    total = passed + failed + skipped
                    
                    print("Test Results:")
                    print(f"  ✅ Passed: {passed}")
                    print(f"  ❌ Failed: {failed}")
                    print(f"  ⊘ Skipped: {skipped}")
                    print(f"  Total: {total}")
                    print()
            except:
                pass
            
            return 'SUCCESS'
        elif result == 'FAILURE':
            print("Status: ❌ FAILURE")
            print(f"Duration: {duration:.1f}s")
            print()
            return 'FAILURE'
        elif result == 'UNSTABLE':
            print("Status: ⚠️  UNSTABLE (some tests failed)")
            print(f"Duration: {duration:.1f}s")
            print()
            return 'UNSTABLE'
        else:
            print(f"Status: {result}")
            print()
            return result
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def trigger_build(jenkins_url, job_name, branch_name, username=None, api_token=None):
    """Trigger a build for a specific branch."""
    print("="*60)
    print("🚀 Triggering Build")
    print("="*60)
    print()
    
    auth = (username, api_token) if username and api_token else None
    encoded_branch = branch_name.replace('/', '%2F')
    
    try:
        response = requests.post(
            f"{jenkins_url}/job/{job_name}/job/{encoded_branch}/build",
            auth=auth,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            print("✅ Build triggered successfully!")
            print()
            print(f"Monitor at: {jenkins_url}/job/{job_name}/job/{encoded_branch}")
            print()
            return True
        else:
            print(f"❌ Failed to trigger build: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def scan_repository(jenkins_url, job_name, username=None, api_token=None):
    """Trigger a repository scan to detect new branches."""
    print("="*60)
    print("🔍 Scanning Repository")
    print("="*60)
    print()
    
    auth = (username, api_token) if username and api_token else None
    
    try:
        response = requests.post(
            f"{jenkins_url}/job/{job_name}/build",
            auth=auth,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            print("✅ Repository scan triggered!")
            print()
            print("Jenkins is scanning for new branches...")
            print("This may take 1-2 minutes.")
            print()
            return True
        else:
            print(f"⚠️  Scan response: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Main test function."""
    # Load environment
    load_dotenv()
    
    # Configuration
    jenkins_url = os.getenv('JENKINS_URL', 'http://localhost:8080').rstrip('/')
    jenkins_user = os.getenv('JENKINS_USER')
    jenkins_token = os.getenv('JENKINS_TOKEN')
    job_name = os.getenv('JENKINS_JOB_NAME', 'API-Testing-Agent')
    
    # Get last branch from command line or find latest
    if len(sys.argv) > 1:
        test_branch = sys.argv[1]
    else:
        # Use the most recent branch from terminal output
        test_branch = 'auto/tests/KAN-4/20251024T124535Z'
    
    print()
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "JENKINS INTEGRATION TEST" + " "*19 + "║")
    print("╚" + "="*58 + "╝")
    print()
    
    # Test 1: Check Jenkins connection
    if not check_jenkins_connection(jenkins_url, jenkins_user, jenkins_token):
        print()
        print("❌ Jenkins is not accessible. Please start Jenkins first.")
        print()
        return False
    
    # Test 2: Check job exists
    if not check_job_exists(jenkins_url, job_name, jenkins_user, jenkins_token):
        print()
        print("❌ Jenkins job not configured. Please create the job first.")
        print()
        print("Quick setup:")
        print(f"  1. Open: {jenkins_url}")
        print("  2. Follow: JENKINS_QUICK_START.md")
        print()
        return False
    
    # Test 3: Check if we should scan for branches
    print("="*60)
    print("🔍 Testing Branch Detection")
    print("="*60)
    print()
    print(f"Looking for branch: {test_branch}")
    print()
    
    response = input("Scan repository for new branches? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
        scan_repository(jenkins_url, job_name, jenkins_user, jenkins_token)
        print("Waiting 10 seconds for scan to complete...")
        time.sleep(10)
    
    # Test 4: Check build status
    status = check_build_status(jenkins_url, job_name, test_branch, jenkins_user, jenkins_token)
    
    if status is None:
        print("="*60)
        print("💡 Next Steps")
        print("="*60)
        print()
        print("The branch hasn't been built yet. You can:")
        print()
        print("1. Trigger a manual build:")
        encoded_branch = test_branch.replace('/', '%2F')
        print(f"   {jenkins_url}/job/{job_name}/job/{encoded_branch}/build")
        print()
        print("2. Wait for automatic scan (if configured)")
        print()
        print("3. Run this script again with:")
        print(f"   python3 tests/test_jenkins_integration.py {test_branch}")
        print()
        
        response = input("Trigger build now? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            if trigger_build(jenkins_url, job_name, test_branch, jenkins_user, jenkins_token):
                print("Build triggered! Monitoring progress...")
                print()
                
                # Monitor build for up to 2 minutes
                for i in range(12):  # 12 * 10s = 2 minutes
                    time.sleep(10)
                    print(f"Checking status... ({i+1}/12)")
                    status = check_build_status(
                        jenkins_url, job_name, test_branch, 
                        jenkins_user, jenkins_token
                    )
                    
                    if status and status != 'BUILDING':
                        break
    
    # Final summary
    print("="*60)
    print("📊 Test Summary")
    print("="*60)
    print()
    print(f"Jenkins URL: {jenkins_url}")
    print(f"Job Name: {job_name}")
    print(f"Branch: {test_branch}")
    print(f"Status: {status or 'Not Built'}")
    print()
    
    if status == 'SUCCESS':
        print("✅ Jenkins integration is working perfectly!")
        print()
        print("Your complete pipeline is operational:")
        print("  Jira → Python → GitHub → Jenkins → Results")
        print()
        return True
    elif status in ['FAILURE', 'UNSTABLE']:
        print("⚠️  Jenkins is working but tests failed.")
        print()
        print("Check Jenkins console output for details:")
        encoded_branch = test_branch.replace('/', '%2F')
        print(f"  {jenkins_url}/job/{job_name}/job/{encoded_branch}/lastBuild/console")
        print()
        return False
    else:
        print("ℹ️  Jenkins integration test incomplete.")
        print()
        print("Follow JENKINS_QUICK_START.md to complete setup.")
        print()
        return False

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

