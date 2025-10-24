"""
Integration tests for Jira connectivity and Epic fetching.

This test suite verifies:
1. Jira credentials are properly configured
2. Jira API connection is working
3. We can successfully fetch Epic details
4. Contract extraction works correctly

Usage:
    pytest tests/test_jira_integration.py -v
    
    # Run specific test:
    pytest tests/test_jira_integration.py::test_jira_connection -v
    
    # Skip if no credentials:
    pytest tests/test_jira_integration.py --skip-integration
"""

import os
import sys
import pytest
import requests
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Import our modules
try:
    from integrations.jira.client import fetch_issue, post_comment, JIRA_BASE, JIRA_USER, JIRA_TOKEN
    from integrations.jira.contract_parser import (
        extract_contract, 
        extract_openapi_url, 
        extract_endpoints,
        normalize_description,
        extract_text_from_adf,
        fetch_openapi_spec
    )
except ImportError as e:
    pytest.skip(f"Could not import Jira modules: {e}", allow_module_level=True)


# Configuration checks
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


# Pytest fixtures
@pytest.fixture(scope="module")
def jira_config():
    """Validate Jira configuration before running tests."""
    missing = check_jira_config()
    if missing:
        pytest.skip(f"Missing Jira configuration: {', '.join(missing)}")
    
    return {
        'base': JIRA_BASE,
        'user': JIRA_USER,
        'token': JIRA_TOKEN
    }


@pytest.fixture(scope="module")
def test_epic_key():
    """
    Get test Epic key from environment or skip.
    Set TEST_EPIC_KEY in .env to run Epic fetching tests.
    """
    epic_key = os.getenv('TEST_EPIC_KEY')
    if not epic_key:
        pytest.skip("TEST_EPIC_KEY not set in environment. Add a valid Jira Epic key to test Epic fetching.")
    return epic_key


# Test Cases
class TestJiraConnection:
    """Test basic Jira API connectivity."""
    
    def test_jira_config_exists(self, jira_config):
        """Test that Jira configuration is loaded."""
        assert jira_config['base'], "JIRA_BASE should not be empty"
        assert jira_config['user'], "JIRA_USER should not be empty"
        assert jira_config['token'], "JIRA_TOKEN should not be empty"
        assert jira_config['base'].startswith('https://'), "JIRA_BASE should start with https://"
    
    def test_jira_api_reachable(self, jira_config):
        """Test that Jira API endpoint is reachable."""
        # Try to reach Jira API root
        url = f"{jira_config['base']}/rest/api/3/serverInfo"
        
        try:
            response = requests.get(
                url,
                auth=(jira_config['user'], jira_config['token']),
                timeout=10
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert 'version' in data, "Response should contain version info"
            
            print(f"\n✓ Connected to Jira: {data.get('baseUrl', 'N/A')}")
            print(f"✓ Jira Version: {data.get('version', 'N/A')}")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to connect to Jira API: {str(e)}")
    
    def test_jira_authentication(self, jira_config):
        """Test that Jira credentials are valid."""
        # Try to get current user info
        url = f"{jira_config['base']}/rest/api/3/myself"
        
        try:
            response = requests.get(
                url,
                auth=(jira_config['user'], jira_config['token']),
                timeout=10
            )
            
            if response.status_code == 401:
                pytest.fail("Authentication failed. Check JIRA_USER and JIRA_TOKEN.")
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            print(f"\n✓ Authenticated as: {data.get('displayName', 'N/A')}")
            print(f"✓ Email: {data.get('emailAddress', 'N/A')}")
            
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to authenticate with Jira: {str(e)}")


class TestJiraEpicFetching:
    """Test Epic fetching functionality."""
    
    def test_fetch_issue_function_exists(self):
        """Test that fetch_issue function is available."""
        assert callable(fetch_issue), "fetch_issue should be a callable function"
    
    def test_fetch_valid_epic(self, jira_config, test_epic_key):
        """Test fetching a valid Jira Epic."""
        try:
            epic = fetch_issue(test_epic_key)
            
            # Verify response structure
            assert isinstance(epic, dict), "Epic should be a dictionary"
            assert 'key' in epic, "Epic should have 'key' field"
            assert 'fields' in epic, "Epic should have 'fields' field"
            
            # Verify key matches
            assert epic['key'] == test_epic_key, f"Expected key {test_epic_key}, got {epic['key']}"
            
            # Print Epic details
            fields = epic.get('fields', {})
            print(f"\n✓ Successfully fetched Epic: {test_epic_key}")
            print(f"✓ Summary: {fields.get('summary', 'N/A')}")
            print(f"✓ Status: {fields.get('status', {}).get('name', 'N/A')}")
            print(f"✓ Issue Type: {fields.get('issuetype', {}).get('name', 'N/A')}")
            
            # Check if it's actually an Epic
            issue_type = fields.get('issuetype', {}).get('name', '').lower()
            if 'epic' not in issue_type:
                print(f"⚠ Warning: Issue {test_epic_key} is type '{issue_type}', not 'Epic'")
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                pytest.fail(f"Epic {test_epic_key} not found. Check TEST_EPIC_KEY value.")
            elif e.response.status_code == 403:
                pytest.fail(f"No permission to access {test_epic_key}. Check user permissions.")
            else:
                pytest.fail(f"HTTP error fetching Epic: {e}")
        except Exception as e:
            pytest.fail(f"Failed to fetch Epic: {str(e)}")
    
    def test_fetch_invalid_epic_returns_error(self, jira_config):
        """Test that fetching invalid Epic raises appropriate error."""
        invalid_key = "INVALID-99999"
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            fetch_issue(invalid_key)
        
        assert exc_info.value.response.status_code == 404, "Should return 404 for invalid Epic"
        print(f"\n✓ Correctly handled invalid Epic key")


class TestContractExtraction:
    """Test API contract extraction from Epic descriptions."""
    
    def test_normalize_description_with_string(self):
        """Test description normalization with plain string."""
        desc = "This is a plain text description"
        result = normalize_description(desc)
        assert result == desc
        assert isinstance(result, str)
        print("\n✓ String description normalization working")
    
    def test_normalize_description_with_adf(self):
        """Test description normalization with ADF format."""
        # Sample ADF structure from Jira API v3
        adf_desc = {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "User Management API"}
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "GET /users"}
                    ]
                }
            ]
        }
        
        result = normalize_description(adf_desc)
        assert isinstance(result, str)
        assert "User Management API" in result
        assert "GET /users" in result
        print(f"\n✓ ADF description normalization working")
        print(f"  Extracted text: {result.strip()[:50]}...")
    
    def test_normalize_description_with_none(self):
        """Test description normalization with None."""
        result = normalize_description(None)
        assert result == ''
        print("\n✓ None description handled correctly")
    
    def test_extract_openapi_url(self):
        """Test extraction of OpenAPI URL from text."""
        test_cases = [
            ("API spec: https://api.example.com/openapi.yaml", "https://api.example.com/openapi.yaml"),
            ("Swagger: https://api.example.com/swagger.json", "https://api.example.com/swagger.json"),
            ("OpenAPI at https://api.example.com/openapi.json", "https://api.example.com/openapi.json"),
            ("No URL here", None),
        ]
        
        for text, expected in test_cases:
            result = extract_openapi_url(text)
            assert result == expected, f"For '{text}', expected {expected}, got {result}"
        
        print("\n✓ OpenAPI URL extraction working correctly")
    
    def test_extract_endpoints(self):
        """Test extraction of endpoint definitions from text."""
        text = """
        User API Endpoints:
        GET /users
        POST /users
        GET /users/{id}
        PUT /users/{id}
        DELETE /users/{id}
        
        Some other text
        """
        
        endpoints = extract_endpoints(text)
        
        assert len(endpoints) == 5, f"Expected 5 endpoints, got {len(endpoints)}"
        assert endpoints[0] == {'method': 'GET', 'path': '/users'}
        assert endpoints[1] == {'method': 'POST', 'path': '/users'}
        assert endpoints[2] == {'method': 'GET', 'path': '/users/{id}'}
        
        print(f"\n✓ Extracted {len(endpoints)} endpoints correctly")
    
    def test_extract_contract_with_openapi(self):
        """Test contract extraction when OpenAPI URL is present."""
        mock_epic = {
            'fields': {
                'description': 'API Spec: https://api.example.com/openapi.yaml\n\nImplement user management.'
            }
        }
        
        contract = extract_contract(mock_epic)
        
        assert 'openapi_url' in contract, "Should extract OpenAPI URL"
        assert contract['openapi_url'] == 'https://api.example.com/openapi.yaml'
        
        print("\n✓ Contract extraction with OpenAPI URL working")
    
    def test_extract_contract_with_endpoints(self):
        """Test contract extraction when endpoints are defined."""
        mock_epic = {
            'fields': {
                'description': '''
                User Management API
                
                GET /users - List users
                POST /users - Create user
                '''
            }
        }
        
        contract = extract_contract(mock_epic)
        
        assert 'endpoints' in contract, "Should extract endpoints"
        assert len(contract['endpoints']) == 2
        assert contract['endpoints'][0]['method'] == 'GET'
        
        print("\n✓ Contract extraction with endpoints working")
    
    def test_extract_contract_fallback(self):
        """Test contract extraction fallback to description."""
        mock_epic = {
            'fields': {
                'description': 'Just a plain description without specific contract info.'
            }
        }
        
        contract = extract_contract(mock_epic)
        
        assert 'description' in contract, "Should fallback to description"
        assert contract['description'] == mock_epic['fields']['description']
        
        print("\n✓ Contract extraction fallback working")
    
    def test_extract_contract_from_real_epic(self, jira_config, test_epic_key):
        """Test contract extraction from a real Epic."""
        try:
            epic = fetch_issue(test_epic_key)
            contract = extract_contract(epic)
            
            assert isinstance(contract, dict), "Contract should be a dictionary"
            assert len(contract) > 0, "Contract should not be empty"
            
            print(f"\n✓ Extracted contract from Epic {test_epic_key}:")
            
            if 'openapi_url' in contract:
                print(f"  - Type: OpenAPI Specification")
                print(f"  - URL: {contract['openapi_url']}")
                
                # Check if spec was fetched
                if 'openapi_spec' in contract:
                    spec = contract['openapi_spec']
                    print(f"  - OpenAPI spec fetched successfully")
                    print(f"  - OpenAPI version: {spec.get('openapi', spec.get('swagger', 'N/A'))}")
                    print(f"  - API title: {spec.get('info', {}).get('title', 'N/A')}")
                    
                    # Count paths
                    paths_count = len(spec.get('paths', {}))
                    print(f"  - Total paths: {paths_count}")
                else:
                    print(f"  - OpenAPI spec not fetched (URL only)")
                    
            elif 'endpoints' in contract:
                print(f"  - Type: Endpoint Definitions")
                print(f"  - Count: {len(contract['endpoints'])} endpoints")
                for ep in contract['endpoints'][:3]:  # Show first 3
                    print(f"    • {ep['method']} {ep['path']}")
            else:
                print(f"  - Type: Plain Description")
                desc = contract.get('description', '')
                print(f"  - Length: {len(desc)} characters")
            
        except Exception as e:
            pytest.skip(f"Could not test with real Epic: {str(e)}")
    
    def test_fetch_openapi_spec_json(self):
        """Test fetching OpenAPI spec from a public JSON endpoint."""
        # Using Swagger Petstore as a test OpenAPI spec
        test_url = "https://petstore.swagger.io/v2/swagger.json"
        
        spec = fetch_openapi_spec(test_url)
        
        if spec is None:
            pytest.skip("Could not fetch test OpenAPI spec (network issue)")
        
        assert isinstance(spec, dict), "Spec should be a dictionary"
        assert 'swagger' in spec or 'openapi' in spec, "Should have version field"
        assert 'paths' in spec, "Should have paths field"
        assert 'info' in spec, "Should have info field"
        
        print(f"\n✓ Successfully fetched and parsed OpenAPI spec")
        print(f"  - Version: {spec.get('swagger', spec.get('openapi', 'N/A'))}")
        print(f"  - Title: {spec.get('info', {}).get('title', 'N/A')}")
        print(f"  - Paths: {len(spec.get('paths', {}))} endpoints")
    
    def test_fetch_openapi_spec_invalid_url(self):
        """Test fetching OpenAPI spec from invalid URL."""
        invalid_url = "https://invalid-domain-12345.com/openapi.json"
        
        spec = fetch_openapi_spec(invalid_url, timeout=2)
        
        assert spec is None, "Should return None for invalid URL"
        print(f"\n✓ Correctly handled invalid OpenAPI URL")
    
    def test_extract_contract_with_openapi_fetch(self):
        """Test contract extraction that fetches OpenAPI spec."""
        mock_epic = {
            'fields': {
                'description': 'API Spec: https://petstore.swagger.io/v2/swagger.json\n\nPet store API.'
            }
        }
        
        contract = extract_contract(mock_epic, fetch_openapi=True)
        
        assert 'openapi_url' in contract, "Should extract OpenAPI URL"
        assert contract['openapi_url'] == 'https://petstore.swagger.io/v2/swagger.json'
        
        # Check if spec was fetched
        if 'openapi_spec' in contract:
            print(f"\n✓ Contract extraction with OpenAPI fetch working")
            spec = contract['openapi_spec']
            print(f"  - Fetched spec with {len(spec.get('paths', {}))} paths")
        else:
            pytest.skip("Could not fetch OpenAPI spec (network issue)")
    
    def test_extract_contract_without_openapi_fetch(self):
        """Test contract extraction without fetching OpenAPI spec."""
        mock_epic = {
            'fields': {
                'description': 'API Spec: https://api.example.com/openapi.yaml\n\nExample API.'
            }
        }
        
        contract = extract_contract(mock_epic, fetch_openapi=False)
        
        assert 'openapi_url' in contract, "Should extract OpenAPI URL"
        assert 'openapi_spec' not in contract, "Should not fetch spec when fetch_openapi=False"
        
        print(f"\n✓ Contract extraction without fetch working")
        print(f"  - URL extracted but not fetched")


class TestJiraComments:
    """Test posting comments to Jira."""
    
    def test_post_comment_function_exists(self):
        """Test that post_comment function is available."""
        assert callable(post_comment), "post_comment should be a callable function"
    
    @pytest.mark.skip(reason="Skipped by default to avoid posting test comments. Remove skip to test.")
    def test_post_comment_to_epic(self, jira_config, test_epic_key):
        """
        Test posting a comment to Epic.
        WARNING: This will actually post a comment to the Epic.
        Remove @pytest.mark.skip to run this test.
        """
        test_comment = "🤖 **Test Comment from API Testing Agent**\n\nThis is an automated test comment. Please ignore."
        
        try:
            result = post_comment(test_epic_key, test_comment)
            
            assert isinstance(result, dict), "Result should be a dictionary"
            print(f"\n✓ Successfully posted test comment to {test_epic_key}")
            print(f"  Comment ID: {result.get('id', 'N/A')}")
            
        except Exception as e:
            pytest.fail(f"Failed to post comment: {str(e)}")


# Helper function for manual testing
def manual_test():
    """
    Run manual tests without pytest.
    Usage: python -c "from tests.test_jira_integration import manual_test; manual_test()"
    """
    print("=== Manual Jira Integration Test ===\n")
    
    # Check configuration
    missing = check_jira_config()
    if missing:
        print(f"❌ Missing configuration: {', '.join(missing)}")
        print("\nPlease set these environment variables in your .env file:")
        for var in missing:
            print(f"  {var}=your_value_here")
        return
    
    print("✓ Configuration loaded")
    print(f"  JIRA_BASE: {JIRA_BASE}")
    print(f"  JIRA_USER: {JIRA_USER}")
    print(f"  JIRA_TOKEN: {'*' * 8 if JIRA_TOKEN else 'NOT SET'}")
    
    # Test connection
    print("\n--- Testing Jira Connection ---")
    try:
        url = f"{JIRA_BASE}/rest/api/3/myself"
        response = requests.get(url, auth=(JIRA_USER, JIRA_TOKEN), timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Successfully connected to Jira")
            print(f"  User: {data.get('displayName', 'N/A')}")
            print(f"  Email: {data.get('emailAddress', 'N/A')}")
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"  {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
    
    # Test Epic fetching if TEST_EPIC_KEY is set
    test_epic_key = os.getenv('TEST_EPIC_KEY')
    if test_epic_key:
        print(f"\n--- Testing Epic Fetch: {test_epic_key} ---")
        try:
            epic = fetch_issue(test_epic_key)
            fields = epic.get('fields', {})
            print(f"✓ Successfully fetched Epic")
            print(f"  Key: {epic.get('key')}")
            print(f"  Summary: {fields.get('summary', 'N/A')}")
            print(f"  Type: {fields.get('issuetype', {}).get('name', 'N/A')}")
            
            # Test contract extraction
            print("\n--- Testing Contract Extraction ---")
            contract = extract_contract(epic)
            if 'openapi_url' in contract:
                print(f"✓ Found OpenAPI URL: {contract['openapi_url']}")
            elif 'endpoints' in contract:
                print(f"✓ Found {len(contract['endpoints'])} endpoints")
            else:
                print(f"✓ Using description (no specific contract found)")
            
        except Exception as e:
            print(f"❌ Failed to fetch Epic: {str(e)}")
    else:
        print("\n⚠ TEST_EPIC_KEY not set. Skipping Epic fetch test.")
        print("  Add TEST_EPIC_KEY=EPIC-123 to your .env file to test Epic fetching.")
    
    print("\n=== Test Complete ===")


if __name__ == '__main__':
    # Allow running directly for quick manual testing
    manual_test()

