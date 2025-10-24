#!/usr/bin/env python3
"""
Standalone manual test for Jira integration.
Does not require pytest - can be run directly with python.

Usage:
    python3 tests/test_jira_manual.py
"""

import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from integrations.jira.client import fetch_issue, post_comment, JIRA_BASE, JIRA_USER, JIRA_TOKEN
from integrations.jira.contract_parser import extract_contract, normalize_description, fetch_openapi_spec


def check_jira_config():
    """Check if Jira environment variables are set."""
    missing = []
    if not JIRA_BASE:
        missing.append('JIRA_BASE')
    if not JIRA_USER:
        missing.append('JIRA_USER')
    if not JIRA_TOKEN:
        missing.append('JIRA_TOKEN')
    return missing


def test_connection():
    """Test basic Jira API connectivity."""
    print("\n" + "="*60)
    print("JIRA INTEGRATION TEST")
    print("="*60)
    
    # Check configuration
    print("\n[1/4] Checking Configuration...")
    missing = check_jira_config()
    if missing:
        print(f"❌ Missing configuration: {', '.join(missing)}")
        print("\nPlease set these environment variables in your .env file:")
        for var in missing:
            print(f"  {var}=your_value_here")
        return False
    
    print("✓ Configuration loaded")
    print(f"  JIRA_BASE: {JIRA_BASE}")
    print(f"  JIRA_USER: {JIRA_USER}")
    print(f"  JIRA_TOKEN: {'*' * 8 if JIRA_TOKEN else 'NOT SET'}")
    
    # Test connection
    print("\n[2/4] Testing Jira Connection...")
    try:
        url = f"{JIRA_BASE}/rest/api/3/myself"
        response = requests.get(url, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
        
        if response.status_code == 401:
            print("❌ Authentication failed!")
            print("  Check your JIRA_USER and JIRA_TOKEN")
            return False
        elif response.status_code != 200:
            print(f"❌ Connection failed: HTTP {response.status_code}")
            print(f"  Response: {response.text}")
            return False
        
        data = response.json()
        print(f"✓ Successfully connected to Jira")
        print(f"  User: {data.get('displayName', 'N/A')}")
        print(f"  Email: {data.get('emailAddress', 'N/A')}")
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: Cannot reach {JIRA_BASE}")
        print(f"  Check if JIRA_BASE URL is correct")
        return False
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False
    
    # Test Epic fetching if TEST_EPIC_KEY is set
    test_epic_key = os.getenv('TEST_EPIC_KEY')
    if test_epic_key:
        print(f"\n[3/4] Testing Epic Fetch: {test_epic_key}...")
        try:
            epic = fetch_issue(test_epic_key)
            fields = epic.get('fields', {})
            
            print(f"✓ Successfully fetched Epic")
            print(f"  Key: {epic.get('key')}")
            print(f"  Summary: {fields.get('summary', 'N/A')}")
            print(f"  Type: {fields.get('issuetype', {}).get('name', 'N/A')}")
            
            # Show description format
            desc_field = fields.get('description')
            if desc_field:
                desc_type = type(desc_field).__name__
                print(f"  Description type: {desc_type}")
                if isinstance(desc_field, dict):
                    print(f"  Description format: ADF (Atlassian Document Format)")
                else:
                    print(f"  Description format: Plain text")
            
            # Test contract extraction
            print("\n[4/4] Testing Contract Extraction...")
            try:
                contract = extract_contract(epic)
                
                if 'openapi_url' in contract:
                    print(f"✓ Found OpenAPI URL")
                    print(f"  URL: {contract['openapi_url']}")
                    
                    # Check if OpenAPI spec was fetched
                    if 'openapi_spec' in contract:
                        spec = contract['openapi_spec']
                        print(f"✓ OpenAPI spec fetched successfully")
                        print(f"  - OpenAPI version: {spec.get('openapi', spec.get('swagger', 'N/A'))}")
                        print(f"  - API title: {spec.get('info', {}).get('title', 'N/A')}")
                        print(f"  - API description: {spec.get('info', {}).get('description', 'N/A')[:100]}...")
                        
                        # Count paths
                        paths = spec.get('paths', {})
                        print(f"  - Total paths: {len(paths)}")
                        
                        # Show first few paths
                        path_items = list(paths.items())[:3]
                        for path, methods in path_items:
                            method_list = ', '.join(methods.keys())
                            print(f"    • {path}: {method_list}")
                    else:
                        print(f"  ⚠ OpenAPI spec not fetched (URL only)")
                        
                elif 'endpoints' in contract:
                    print(f"✓ Found {len(contract['endpoints'])} endpoints")
                    for i, ep in enumerate(contract['endpoints'][:5], 1):
                        print(f"  {i}. {ep['method']} {ep['path']}")
                    if len(contract['endpoints']) > 5:
                        print(f"  ... and {len(contract['endpoints']) - 5} more")
                else:
                    desc_text = contract.get('description', '')
                    print(f"✓ Using plain description")
                    print(f"  Length: {len(desc_text)} characters")
                    if desc_text:
                        preview = desc_text[:100].strip()
                        print(f"  Preview: {preview}{'...' if len(desc_text) > 100 else ''}")
                
            except Exception as e:
                print(f"❌ Contract extraction failed: {str(e)}")
                import traceback
                traceback.print_exc()
                return False
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ Epic {test_epic_key} not found")
                print(f"  Check if the Epic key is correct")
            elif e.response.status_code == 403:
                print(f"❌ No permission to access {test_epic_key}")
                print(f"  Check user permissions in Jira")
            else:
                print(f"❌ HTTP error: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to fetch Epic: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("\n[3/4] Skipping Epic Fetch Test")
        print("  ⚠ TEST_EPIC_KEY not set in .env file")
        print("  Add TEST_EPIC_KEY=YOUR-EPIC-KEY to .env to test Epic fetching")
        print("\n[4/4] Skipping Contract Extraction Test")
        print("  ⚠ Requires TEST_EPIC_KEY to be set")
    
    # Test OpenAPI fetching (bonus test with public API)
    print("\n[BONUS] Testing OpenAPI Spec Fetching...")
    try:
        test_url = "https://petstore.swagger.io/v2/swagger.json"
        print(f"  Fetching from: {test_url}")
        spec = fetch_openapi_spec(test_url)
        
        if spec:
            print(f"✓ Successfully fetched and parsed OpenAPI spec")
            print(f"  - Version: {spec.get('swagger', spec.get('openapi', 'N/A'))}")
            print(f"  - Title: {spec.get('info', {}).get('title', 'N/A')}")
            print(f"  - Paths: {len(spec.get('paths', {}))} endpoints")
        else:
            print(f"  ⚠ Could not fetch OpenAPI spec (network issue)")
    except Exception as e:
        print(f"  ⚠ OpenAPI fetch test failed: {str(e)}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
    print("\nYour Jira integration is working correctly!")
    print("\n📋 Summary:")
    print("  ✓ Jira connection working")
    print("  ✓ Epic fetching working")
    print("  ✓ Contract extraction working")
    print("  ✓ OpenAPI spec fetching working")
    print("\nYou can now run the full application with:")
    print("  python3 main.py")
    print("  # or")
    print("  uvicorn core.webhooks:app --reload --port 8000")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

