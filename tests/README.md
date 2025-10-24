# Tests Directory

This directory contains test suites for the API Testing Agent.

## Test Files

### test_jira_integration.py
Comprehensive integration tests for Jira connectivity and Epic fetching.

**What it tests:**
- ✅ Jira configuration is properly set
- ✅ Jira API is reachable
- ✅ Authentication credentials are valid
- ✅ Can fetch Epic details
- ✅ Contract extraction from Epic descriptions
- ✅ Posting comments to Jira (optional)

**Running the tests:**

```bash
# Run all Jira integration tests
pytest tests/test_jira_integration.py -v

# Run specific test class
pytest tests/test_jira_integration.py::TestJiraConnection -v

# Run specific test
pytest tests/test_jira_integration.py::TestJiraConnection::test_jira_api_reachable -v

# Show print output
pytest tests/test_jira_integration.py -v -s
```

**Quick manual test (without pytest):**

```bash
# Run manual test function
python tests/test_jira_integration.py

# Or from Python
python -c "from tests.test_jira_integration import manual_test; manual_test()"
```

**Required Setup:**

1. Configure `.env` file with Jira credentials:
   ```bash
   JIRA_BASE=https://yourcompany.atlassian.net
   JIRA_USER=your-email@example.com
   JIRA_TOKEN=your_jira_api_token
   ```

2. (Optional) Add a test Epic key to test Epic fetching:
   ```bash
   TEST_EPIC_KEY=EPIC-123
   ```

**Test Levels:**

- **Basic Tests** (always run): Configuration and connection tests
- **Epic Tests** (require TEST_EPIC_KEY): Fetch real Epic and extract contract
- **Comment Tests** (skipped by default): Post test comments to Jira

### sample_pytest.py
Example pytest file showing the expected format for LLM-generated tests.

**Purpose:** Reference template for test generation service.

## Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-cov

# Or install all requirements
pip install -r requirements.txt
```

## Environment Variables for Testing

Add these to your `.env` file:

```bash
# Required for Jira tests
JIRA_BASE=https://yourcompany.atlassian.net
JIRA_USER=your-email@example.com
JIRA_TOKEN=your_jira_api_token

# Optional: specific Epic to test with
TEST_EPIC_KEY=EPIC-123

# Required for full integration tests
GITHUB_TOKEN=your_github_token
REPO_FULL_NAME=owner/repo
OPENAI_API_KEY=your_openai_key
```

## Common Test Scenarios

### 1. First Time Setup - Verify Jira Connection

```bash
# Quick manual test
python tests/test_jira_integration.py
```

Expected output:
```
=== Manual Jira Integration Test ===

✓ Configuration loaded
  JIRA_BASE: https://yourcompany.atlassian.net
  JIRA_USER: you@example.com
  JIRA_TOKEN: ********

--- Testing Jira Connection ---
✓ Successfully connected to Jira
  User: Your Name
  Email: you@example.com
```

### 2. Test Epic Fetching

Set `TEST_EPIC_KEY` in `.env`, then:

```bash
pytest tests/test_jira_integration.py::TestJiraEpicFetching -v -s
```

### 3. Test Contract Extraction

```bash
pytest tests/test_jira_integration.py::TestContractExtraction -v -s
```

### 4. Full Integration Test Suite

```bash
# Run all tests with coverage
pytest tests/ -v --cov=integrations --cov=services --cov=core
```

## Troubleshooting

### "Missing Jira configuration" Error

**Problem:** Environment variables not loaded.

**Solution:**
1. Ensure `.env` file exists in project root
2. Check `.env` has correct format (no quotes around values)
3. Verify python-dotenv is installed: `pip install python-dotenv`

### "Authentication failed" Error

**Problem:** Invalid Jira credentials.

**Solution:**
1. Regenerate Jira API token at https://id.atlassian.com/manage-profile/security/api-tokens
2. Ensure JIRA_USER is your email (not username)
3. Check JIRA_BASE URL is correct (with https://)

### "Epic not found" Error

**Problem:** TEST_EPIC_KEY doesn't exist or you don't have access.

**Solution:**
1. Verify Epic key is correct (e.g., PROJECT-123)
2. Check you have permission to view the Epic in Jira
3. Try with a different Epic that you created

### "Could not import Jira modules" Error

**Problem:** Python path issues.

**Solution:**
```bash
# Run from project root
cd /path/to/api_testing_agent
pytest tests/test_jira_integration.py -v

# Or set PYTHONPATH
export PYTHONPATH=/path/to/api_testing_agent:$PYTHONPATH
pytest tests/test_jira_integration.py -v
```

## Adding New Tests

### For a new integration:

```python
# tests/test_github_integration.py
import pytest
from integrations.github.client import commit_files_to_branch

class TestGitHubIntegration:
    def test_github_connection(self):
        # Your test here
        pass
```

### For a new service:

```python
# tests/test_test_generator.py
import pytest
from services.test_generator.generator import generate_tests

class TestTestGenerator:
    def test_generate_python_tests(self):
        # Your test here
        pass
```

## Continuous Integration

For CI/CD pipelines, use pytest-xdist for parallel execution:

```bash
# Install
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto

# Generate JUnit XML for CI
pytest tests/ --junitxml=results.xml
```

## Test Coverage

Generate coverage report:

```bash
# HTML report
pytest tests/ --cov=. --cov-report=html

# Terminal report
pytest tests/ --cov=. --cov-report=term-missing

# Check minimum coverage (e.g., 80%)
pytest tests/ --cov=. --cov-fail-under=80
```

## Best Practices

1. **Always use fixtures** for shared setup/teardown
2. **Mock external services** in unit tests
3. **Use integration tests** for actual API calls
4. **Skip destructive tests** by default (@pytest.mark.skip)
5. **Add clear docstrings** explaining what each test does
6. **Print useful info** with print() statements (use -s flag to see)
7. **Use parametrize** for testing multiple cases

Example:
```python
@pytest.mark.parametrize("text,expected", [
    ("GET /users", [{'method': 'GET', 'path': '/users'}]),
    ("POST /users", [{'method': 'POST', 'path': '/users'}]),
])
def test_extract_endpoints(text, expected):
    result = extract_endpoints(text)
    assert result == expected
```

## Support

If tests fail unexpectedly:
1. Check logs in terminal output
2. Review helper.md for module documentation
3. Verify all environment variables are set
4. Test each component separately (connection → fetch → extract)

