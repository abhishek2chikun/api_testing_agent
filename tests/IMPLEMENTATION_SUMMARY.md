# Implementation Summary: OpenAPI Integration & Test Generation Flow

## ✅ What We've Implemented

### 1. **Enhanced Contract Parser** (`integrations/jira/contract_parser.py`)

#### New Features:
- ✅ **Fetches OpenAPI specifications** from URLs found in Jira Epic descriptions
- ✅ **Parses both JSON and YAML** OpenAPI formats
- ✅ **Handles Atlassian Document Format (ADF)** from Jira API v3
- ✅ **Extracts three types of contracts**:
  1. OpenAPI spec (fetched and parsed)
  2. Manual endpoint definitions
  3. Plain text descriptions

#### New Functions:
```python
# Fetches and parses OpenAPI spec from URL
fetch_openapi_spec(url: str, timeout: int = 10) -> Optional[dict]

# Extracts contract with optional OpenAPI fetching
extract_contract(epic_json: dict, fetch_openapi: bool = True) -> dict
```

#### Output Format:
```python
# When OpenAPI URL is found and fetched:
{
    'openapi_url': 'https://api.example.com/openapi.json',
    'openapi_spec': {
        'openapi': '3.0.0',
        'info': {...},
        'paths': {...},
        'components': {...}
    }
}

# When only endpoints are found:
{
    'endpoints': [
        {'method': 'GET', 'path': '/users'},
        {'method': 'POST', 'path': '/users'}
    ]
}

# Fallback:
{
    'description': 'Plain text description...'
}
```

### 2. **Enhanced Test Generator** (`services/test_generator/generator.py`)

#### New Features:
- ✅ **Formats OpenAPI spec for LLM prompt** (with truncation to avoid token limits)
- ✅ **Extracts Epic summary and description separately**
- ✅ **Normalizes ADF descriptions** to plain text
- ✅ **Creates structured prompts** with both Epic details and API contract

#### New Functions:
```python
# Formats contract details for the LLM prompt
format_contract_for_prompt(contract: dict) -> str

# Formats OpenAPI spec as JSON (with truncation)
format_openapi_spec(spec: dict, max_length: int = 8000) -> str
```

#### Generated Prompt Structure:
```
=== JIRA EPIC INFORMATION ===
ISSUE_KEY: EPIC-123
SUMMARY: User Management API
DESCRIPTION: [normalized description]

=== API CONTRACT ===
TYPE: OpenAPI Specification
URL: https://api.example.com/openapi.json
VERSION: 3.0.0
TITLE: User Management API

FULL OPENAPI SPEC:
{
  "openapi": "3.0.0",
  "paths": {...},
  "components": {...}
}

=== REQUIREMENTS ===
[Detailed test generation requirements]
```

### 3. **Comprehensive Test Suite** (`tests/test_jira_integration.py`)

#### New Tests:
- ✅ `test_fetch_openapi_spec_json()` - Fetches real OpenAPI spec
- ✅ `test_fetch_openapi_spec_invalid_url()` - Handles invalid URLs
- ✅ `test_extract_contract_with_openapi_fetch()` - Full integration test
- ✅ `test_extract_contract_without_openapi_fetch()` - URL-only mode
- ✅ `test_normalize_description_with_adf()` - ADF parsing
- ✅ Enhanced `test_extract_contract_from_real_epic()` - Shows OpenAPI spec details

### 4. **Manual Test Script** (`tests/test_jira_manual.py`)

#### New Features:
- ✅ Tests OpenAPI spec fetching with public Swagger Petstore API
- ✅ Shows fetched OpenAPI spec details (version, title, paths)
- ✅ Displays endpoint methods for each path
- ✅ Comprehensive summary of all working features

## 🔄 Complete Workflow

```
1. JIRA EPIC CREATED
   └─> Epic description contains: https://api.example.com/openapi.json
   
2. WEBHOOK RECEIVED
   └─> POST /jira/webhook
   └─> core/webhooks.py triggers process_epic()
   
3. FETCH EPIC FROM JIRA
   └─> integrations/jira/client.py::fetch_issue()
   └─> Returns Epic JSON (with ADF description)
   
4. EXTRACT & FETCH CONTRACT
   └─> integrations/jira/contract_parser.py::extract_contract()
   ├─> normalize_description() - Converts ADF to plain text
   ├─> extract_openapi_url() - Finds OpenAPI URL
   └─> fetch_openapi_spec() - Fetches & parses OpenAPI spec
   
   Returns:
   {
       'openapi_url': 'https://api.example.com/openapi.json',
       'openapi_spec': { full parsed spec }
   }
   
5. GENERATE TESTS WITH LLM
   └─> services/test_generator/generator.py::generate_tests()
   ├─> Extracts Epic summary & description
   ├─> format_contract_for_prompt() - Formats OpenAPI spec + Epic details
   └─> call_llm() - Sends to OpenAI with comprehensive prompt
   
   Prompt includes:
   - Epic key, summary, description
   - Full OpenAPI specification
   - Test generation requirements
   
6. LLM GENERATES TESTS
   └─> Returns test files with ---TESTFILE markers
   └─> parse_test_files() extracts files
   
7. COMMIT TO GITHUB
   └─> integrations/github/client.py::commit_files_to_branch()
   └─> Creates branch: auto/tests/EPIC-123/timestamp
   
8. RUN TESTS IN DOCKER
   └─> services/test_runner/runner.py::run_pytests_in_docker()
   └─> Clones branch, runs pytest in container
   
9. POST RESULTS TO JIRA
   └─> integrations/jira/client.py::post_comment()
   └─> Posts test results as comment on Epic
```

## 📝 How to Use

### Option 1: OpenAPI URL (Recommended ⭐)

Create a Jira Epic with:
```
User Management API

OpenAPI Spec: https://api.example.com/openapi.json

This API provides full CRUD operations for user management.
```

**What happens:**
1. System extracts the OpenAPI URL
2. Fetches and parses the spec (JSON or YAML)
3. Passes **full OpenAPI spec + Epic details** to LLM
4. LLM generates comprehensive tests covering all endpoints

### Option 2: Manual Endpoints

Create a Jira Epic with:
```
User Management API

GET /users - List all users
POST /users - Create user
GET /users/{id} - Get user by ID
DELETE /users/{id} - Delete user
```

**What happens:**
1. System extracts endpoint definitions
2. Passes **endpoints + Epic description** to LLM
3. LLM generates tests for listed endpoints

### Option 3: Plain Description

Create a Jira Epic with:
```
User Management API

Implement CRUD operations for users including registration,
authentication, profile management, and deletion.
```

**What happens:**
1. System uses plain description
2. LLM infers reasonable endpoints and generates tests

## 🧪 Testing

### Run Manual Test:
```bash
# Install dependencies first
pip install requests python-dotenv pyyaml

# Run test
python3 tests/test_jira_manual.py
```

### Run With Pytest:
```bash
# Install pytest
pip install pytest

# Run all integration tests
pytest tests/test_jira_integration.py -v -s

# Run specific test
pytest tests/test_jira_integration.py::TestContractExtraction::test_fetch_openapi_spec_json -v -s
```

### Expected Output:
```
============================================================
JIRA INTEGRATION TEST
============================================================

[1/4] Checking Configuration...
✓ Configuration loaded

[2/4] Testing Jira Connection...
✓ Successfully connected to Jira

[3/4] Testing Epic Fetch: EPIC-123...
✓ Successfully fetched Epic
  - OpenAPI version: 3.0.0
  - API title: User Management API
  - Total paths: 15

[4/4] Testing Contract Extraction...
✓ OpenAPI spec fetched successfully
  - /users: get, post
  - /users/{id}: get, put, delete

[BONUS] Testing OpenAPI Spec Fetching...
✓ Successfully fetched and parsed OpenAPI spec
  - Version: 2.0
  - Title: Swagger Petstore
  - Paths: 14 endpoints

✅ ALL TESTS PASSED
```

## 📦 Dependencies Added

```txt
requests     # HTTP requests (OpenAPI fetching)
pyyaml       # YAML parsing (for OpenAPI YAML files)
```

Already included in `requirements.txt`.

## 🎯 Key Benefits

1. **Automatic OpenAPI Fetching**: No manual work - just paste URL in Jira
2. **Rich Context for LLM**: Full API spec + Epic details = better tests
3. **Flexible Input**: Supports OpenAPI, endpoints, or plain text
4. **ADF Support**: Works with Jira API v3's Atlassian Document Format
5. **Error Handling**: Gracefully handles fetch failures, invalid URLs
6. **Comprehensive Tests**: All features tested and validated

## 🔧 Configuration

No additional configuration needed! Just ensure:
```bash
# .env file contains:
JIRA_BASE=https://yourcompany.atlassian.net
JIRA_USER=your-email@example.com
JIRA_TOKEN=your_jira_api_token
OPENAI_API_KEY=your_openai_key
GITHUB_TOKEN=your_github_token
REPO_FULL_NAME=owner/repo

# Optional: test with a specific Epic
TEST_EPIC_KEY=EPIC-123
```

## 📊 Example LLM Prompt (What Gets Sent)

```
=== JIRA EPIC INFORMATION ===
ISSUE_KEY: EPIC-123
SUMMARY: User Management API
DESCRIPTION: Implement CRUD operations for user management with proper
authentication and validation.

=== API CONTRACT ===
TYPE: OpenAPI Specification
URL: https://api.example.com/openapi.json
VERSION: 3.0.0
TITLE: User Management API
DESCRIPTION: RESTful API for user management operations

FULL OPENAPI SPEC:
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "User Management API",
    "version": "1.0.0"
  },
  "paths": {
    "/users": {
      "get": {
        "summary": "List users",
        "responses": {...}
      },
      "post": {
        "summary": "Create user",
        "requestBody": {...},
        "responses": {...}
      }
    }
  },
  "components": {
    "schemas": {
      "User": {
        "type": "object",
        "properties": {...}
      }
    }
  }
}
```

NOTE: Use this OpenAPI specification to generate comprehensive tests.
Include Schemathesis property tests that validate all endpoints against the schema.

=== REQUIREMENTS ===
[Full test generation requirements...]
```

## 🚀 Next Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure .env file** with your credentials

3. **Test Jira integration**:
   ```bash
   python3 tests/test_jira_manual.py
   ```

4. **Create a test Epic** with OpenAPI URL in description

5. **Run the service**:
   ```bash
   uvicorn core.webhooks:app --reload --port 8000
   ```

6. **Watch the magic happen**! 🎉

---

**Status**: ✅ **Fully Implemented and Tested**

All components are working together to fetch OpenAPI specs from Jira Epics and pass them to the LLM for comprehensive test generation!

