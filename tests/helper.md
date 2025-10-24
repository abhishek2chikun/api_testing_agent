# API Testing Agent - Comprehensive Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Module Details](#module-details)
5. [File Descriptions](#file-descriptions)
6. [Workflow](#workflow)
7. [Configuration](#configuration)
8. [Development Guide](#development-guide)

---

## Overview

The API Testing Agent is an automated service that:
- Receives webhooks from Jira when Epics are created/updated
- Extracts API specifications from Epic descriptions (OpenAPI URLs or endpoint definitions)
- Uses LLM (OpenAI GPT) to generate comprehensive API tests
- Commits generated tests to GitHub on a feature branch
- Executes tests in isolated Docker containers
- Reports results back to the Jira Epic as comments

**Key Technologies:**
- FastAPI for webhook handling
- OpenAI GPT-4o-mini for test generation
- PyGithub for repository management
- Docker for test isolation
- pytest/Schemathesis for Python tests
- JUnit5/Rest-Assured for Java tests (optional)

---

## Architecture

```
┌─────────────┐
│ Jira Webhook│
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   core/webhooks.py  │ ◄── FastAPI endpoint
└──────┬──────────────┘
       │
       ▼
┌──────────────────────┐
│ core/orchestrator.py │ ◄── Main pipeline coordination
└──┬───────────────────┘
   │
   ├─► integrations/jira/         ◄── Fetch Epic details
   │   ├── client.py
   │   └── contract_parser.py
   │
   ├─► services/test_generator/   ◄── Generate tests with LLM
   │   ├── generator.py
   │   └── prompts.py
   │
   ├─► integrations/github/       ◄── Commit tests to branch
   │   └── client.py
   │
   └─► services/test_runner/      ◄── Execute in Docker
       └── runner.py
```

---

## Directory Structure

```
api_testing_agent/
│
├── core/                          # Core application logic
│   ├── __init__.py                # Module initialization
│   ├── webhooks.py                # FastAPI webhook endpoints
│   └── orchestrator.py            # Main orchestration pipeline
│
├── integrations/                  # External service integrations
│   ├── __init__.py
│   ├── jira/                      # Jira integration
│   │   ├── __init__.py
│   │   ├── client.py              # Jira REST API client
│   │   └── contract_parser.py    # Extract API specs from Epic
│   └── github/                    # GitHub integration
│       ├── __init__.py
│       └── client.py              # GitHub API client (PyGithub)
│
├── services/                      # Business logic services
│   ├── __init__.py
│   ├── test_generator/            # Test generation service
│   │   ├── __init__.py
│   │   ├── generator.py           # LLM test generation logic
│   │   └── prompts.py             # LLM prompt templates
│   └── test_runner/               # Test execution service
│       ├── __init__.py
│       └── runner.py              # Docker-based test runner
│
├── config/                        # Configuration management
│   └── __init__.py
│
├── examples/                      # Example test templates
│   ├── __init__.py
│   └── sample_pytest.py           # Sample pytest output
│
├── README.md                      # Quick start guide
├── helper.md                      # This file - detailed documentation
├── notes.md                       # Architecture notes & production tips
├── requirements.txt               # Python dependencies
├── env.example                    # Environment variable template
└── docker-runner.sh               # Helper script for local testing
```

---

## Module Details

### 1. core/ - Core Application

**Purpose:** Entry point and main orchestration logic.

#### core/webhooks.py
- **Responsibility:** FastAPI application and webhook endpoints
- **Key Endpoints:**
  - `GET /` - Health check
  - `POST /jira/webhook` - Receives Jira Epic webhooks
- **Features:**
  - Validates incoming webhook payloads
  - Extracts issue key from Jira payload
  - Triggers background task for Epic processing
  - Returns immediate response to avoid timeout

#### core/orchestrator.py
- **Responsibility:** Main pipeline coordination
- **Key Function:** `process_epic(issue_key)`
- **Pipeline Steps:**
  1. Fetch Epic from Jira
  2. Extract API contract (OpenAPI/endpoints)
  3. Generate tests using LLM
  4. Commit tests to GitHub branch
  5. Run tests in Docker
  6. Post results to Jira
- **Error Handling:** Catches exceptions and posts failures to Jira

---

### 2. integrations/ - External Services

**Purpose:** Abstraction layer for external API interactions.

#### integrations/jira/client.py
- **Responsibility:** Jira REST API communication
- **Functions:**
  - `fetch_issue(issue_key)` - Get Epic details
  - `post_comment(issue_key, body)` - Add comment to Epic
- **Authentication:** Basic auth using JIRA_USER and JIRA_TOKEN
- **API Version:** Jira REST API v3

#### integrations/jira/contract_parser.py
- **Responsibility:** Extract API specifications from Epic description
- **Extraction Strategies:**
  1. **OpenAPI URL:** Searches for swagger/openapi URLs
  2. **Endpoint Definitions:** Parses lines like "GET /users", "POST /users"
  3. **Fallback:** Returns plain description text
- **Functions:**
  - `extract_contract(epic_json)` - Main extraction logic
  - `extract_openapi_url(text)` - Regex-based URL extraction
  - `extract_endpoints(text)` - Parse HTTP method + path lines

#### integrations/github/client.py
- **Responsibility:** GitHub repository operations
- **Functions:**
  - `commit_files_to_branch(issue_key, files)` - Create branch and commit files
- **Branch Naming:** `auto/tests/{issue_key}/{timestamp}`
- **Authentication:** GitHub personal access token
- **Features:**
  - Creates branch from main
  - Handles file creation and updates
  - Idempotent operations (update if exists)

---

### 3. services/ - Business Logic

**Purpose:** Core business logic for test generation and execution.

#### services/test_generator/generator.py
- **Responsibility:** LLM-based test generation orchestration
- **Key Functions:**
  - `generate_tests(issue_key, epic, contract, language)` - Main entry point
  - `call_llm(prompt)` - OpenAI API interaction
  - `parse_test_files(text)` - Extract files from LLM response
- **LLM Configuration:**
  - Model: gpt-4o-mini
  - Temperature: 0.0 (deterministic)
  - Max tokens: 2000
- **File Format:** Uses markers `---TESTFILE: path---` and `---ENDTESTFILE---`
- **Supported Languages:** Python (pytest), Java (JUnit5/Rest-Assured)

#### services/test_generator/prompts.py
- **Responsibility:** LLM prompt templates
- **Templates:**
  - `PYTEST_PROMPT_TEMPLATE` - For Python/pytest tests
  - `JAVA_PROMPT_TEMPLATE` - For Java/Rest-Assured tests
- **Prompt Structure:**
  - System role: "You are a senior test engineer..."
  - User role: Epic details + contract + requirements
- **Requirements Specified:**
  - File output format
  - Test coverage (happy path, validation, 404, auth)
  - Framework-specific guidelines

#### services/test_runner/runner.py
- **Responsibility:** Execute tests in isolated Docker containers
- **Key Functions:**
  - `clone_repo_to_tmp(branch)` - Clone branch to temp directory
  - `run_pytests_in_docker(branch)` - Run pytest in python:3.11 container
  - `run_maven_tests_in_docker(branch)` - Run Maven in maven:3.9-jdk-17 container
- **Docker Strategy:**
  - Mounts cloned repo as volume
  - Installs dependencies inside container
  - Runs tests with JUnit XML output
  - Cleans up containers (--rm flag)
- **Security:** Isolated execution prevents malicious code from affecting host

---

### 4. config/ - Configuration

**Purpose:** Centralized configuration management (currently minimal).

**Potential Additions:**
- Settings class using Pydantic
- Environment-specific configurations
- Feature flags
- Logging configuration

---

### 5. examples/ - Example Templates

**Purpose:** Reference implementations showing expected LLM output.

#### examples/sample_pytest.py
- **Shows:** Structure and style of generated pytest tests
- **Includes:**
  - Happy path test
  - Validation error test
  - 404 not found test
  - Authentication test
- **Best Practices:**
  - Unique identifiers (UUID)
  - Proper assertions
  - Pytest markers
  - Docstrings

---

## File Descriptions

### Root-Level Files

#### README.md
- Quick start guide
- Environment setup
- Basic usage instructions

#### helper.md (this file)
- Comprehensive documentation
- Architecture details
- Module descriptions
- Development guide

#### notes.md
- Architecture decisions
- Production considerations
- Feature toggle instructions
- Future improvements

#### requirements.txt
- Python package dependencies
- Includes: fastapi, uvicorn, requests, PyGithub, openai, pytest, schemathesis

#### env.example
- Template for environment variables
- Lists all required configuration

#### docker-runner.sh
- Helper script for local test execution
- Usage: `./docker-runner.sh <branch_name>`

---

## Workflow

### Complete End-to-End Flow

```
1. Developer creates Jira Epic with API details
   ↓
2. Jira sends webhook to POST /jira/webhook
   ↓
3. core/webhooks.py receives request
   ↓
4. Webhook triggers process_epic() in background
   ↓
5. orchestrator fetches Epic from Jira
   ↓
6. contract_parser extracts API specification
   ↓
7. generator builds LLM prompt with Epic context
   ↓
8. LLM generates test files
   ↓
9. generator parses test files from LLM response
   ↓
10. github/client creates branch and commits files
   ↓
11. runner clones branch to temp directory
   ↓
12. runner executes tests in Docker container
   ↓
13. runner parses test results
   ↓
14. orchestrator posts results to Jira Epic
   ↓
15. Developer reviews tests and results in Jira
```

### Example Jira Epic Description

**Option 1: OpenAPI URL**
```
User Management API

OpenAPI Spec: https://api.example.com/openapi.yaml

Implement CRUD operations for user management.
```

**Option 2: Endpoint Definitions**
```
User Management API

Endpoints:
GET /users - List all users
POST /users - Create new user
GET /users/{id} - Get user by ID
PUT /users/{id} - Update user
DELETE /users/{id} - Delete user
```

---

## Configuration

### Required Environment Variables

Create a `.env` file in the project root:

```bash
# Jira Configuration
JIRA_BASE=https://yourcompany.atlassian.net
JIRA_USER=your-email@example.com
JIRA_TOKEN=your_jira_api_token

# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
REPO_FULL_NAME=owner/repository

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: Maven Command (for Java tests)
MAVEN_CMD=mvn
```

### Obtaining API Tokens

**Jira API Token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy and save the token

**GitHub Personal Access Token:**
1. Go to Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` scope
3. Copy and save the token

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy and save the key

---

## Development Guide

### Setup

1. **Clone Repository**
   ```bash
   git clone <repo-url>
   cd api_testing_agent
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp env.example .env
   # Edit .env with your credentials
   ```

5. **Run Application**
   ```bash
   uvicorn core.webhooks:app --reload --port 8000
   ```

### Testing Locally

**Without Jira Webhook:**

Create a test script to directly call `process_epic()`:

```python
from core.orchestrator import process_epic

# Use an actual Jira Epic key
process_epic("EPIC-123")
```

**With Webhook:**

Use ngrok or similar to expose local server:

```bash
ngrok http 8000
# Configure Jira webhook to: https://<ngrok-url>/jira/webhook
```

### Adding New Test Generators

1. Add new prompt template in `services/test_generator/prompts.py`
2. Update `generate_tests()` to support new language
3. Add corresponding runner function in `services/test_runner/runner.py`
4. Update orchestrator to call appropriate runner

### Extending Contract Parsers

Add new extraction strategies in `integrations/jira/contract_parser.py`:

```python
def extract_graphql_schema(text: str) -> dict:
    """Extract GraphQL schema URL."""
    # Implementation
    pass

def extract_contract(epic_json: dict) -> dict:
    # Add new strategy
    schema = extract_graphql_schema(desc)
    if schema:
        return {'graphql_schema': schema}
    # ... existing strategies
```

### Adding Observability

**Logging:**
- All modules use Python `logging` module
- Consistent format: `[{issue_key}] message`

**Metrics (Future):**
```python
# Add to orchestrator.py
import prometheus_client as prom

test_generation_duration = prom.Histogram('test_generation_duration_seconds')
test_execution_results = prom.Counter('test_execution_results', ['status'])
```

**Tracing (Future):**
```python
# Add OpenTelemetry
from opentelemetry import trace

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("generate_tests"):
    # ... generation logic
```

---

## Common Issues & Solutions

### Issue: LLM Not Generating Tests Properly

**Symptoms:** Generated files are empty or malformed

**Solutions:**
1. Check prompt templates in `services/test_generator/prompts.py`
2. Increase `max_tokens` in `call_llm()` function
3. Add more examples to prompt
4. Verify OpenAI API key is valid

### Issue: Docker Tests Failing

**Symptoms:** Tests fail with import errors or dependency issues

**Solutions:**
1. Ensure `requirements.txt` exists in repository
2. Check Docker daemon is running
3. Verify repo is cloneable with provided token
4. Check Docker image versions (python:3.11, maven:3.9.0-jdk-17)

### Issue: GitHub Commits Failing

**Symptoms:** Branch creation or commit errors

**Solutions:**
1. Verify GitHub token has `repo` scope
2. Check REPO_FULL_NAME format is `owner/repo`
3. Ensure main branch exists
4. Verify token hasn't expired

### Issue: Jira Comments Not Posting

**Symptoms:** Tests run but results don't appear in Jira

**Solutions:**
1. Check Jira credentials are correct
2. Verify user has permission to comment on Epic
3. Check Jira API version (should be v3)
4. Review logs for error messages

---

## Security Considerations

### Secrets Management
- **Current:** Environment variables (not production-ready)
- **Recommended:** AWS Secrets Manager, HashiCorp Vault, or similar

### Webhook Security
- **Current:** No signature verification
- **Recommended:** Validate Jira webhook signatures

### Code Execution
- **Current:** Docker isolation (good)
- **Recommended:** Additional sandboxing, resource limits

### API Rate Limiting
- **Current:** None
- **Recommended:** Rate limit OpenAI API calls, implement backoff

---

## Performance Optimization

### Current Bottlenecks
1. **Synchronous LLM calls** - Can take 5-30 seconds
2. **Docker test execution** - Depends on test suite size
3. **GitHub API calls** - Multiple requests per file

### Optimization Strategies
1. **Use task queue** - Celery, RQ, or AWS SQS
2. **Parallel test execution** - Run multiple Docker containers
3. **Batch GitHub commits** - Use GitHub tree API for multiple files
4. **Cache LLM responses** - For similar Epics
5. **Stream LLM responses** - Process files as they're generated

---

## Future Enhancements

### Planned Features
- [ ] Pull request creation with generated tests
- [ ] Test coverage analysis
- [ ] Support for more frameworks (pytest-bdd, cucumber)
- [ ] Integration test support
- [ ] Performance test generation
- [ ] Contract testing (Pact)
- [ ] Automatic PR review with test results

### Integration Opportunities
- [ ] Slack notifications
- [ ] PagerDuty alerts for test failures
- [ ] DataDog/New Relic metrics
- [ ] Jenkins/CircleCI pipeline integration

---

## Contributing

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings to all functions/classes
- Keep functions small and focused

### Commit Messages
```
<type>(<scope>): <subject>

<body>

Examples:
feat(generator): add support for GraphQL schema
fix(jira): handle missing description field
docs(helper): update workflow diagram
```

### Pull Request Process
1. Create feature branch from main
2. Make changes with tests
3. Update documentation
4. Submit PR with description
5. Address review comments
6. Squash and merge

---

## Support & Resources

### Documentation
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PyGithub Docs](https://pygithub.readthedocs.io/)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)

### Contact
- GitHub Issues: For bugs and feature requests
- Wiki: For additional documentation

---

**Last Updated:** October 2025  
**Version:** 1.0.0  
**Maintainer:** Development Team

