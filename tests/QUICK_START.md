# API Testing Agent - Quick Start Guide 🚀

## What This Does

Automatically generates and runs API tests from Jira Epics:
1. **Fetch** Epic from Jira
2. **Extract** OpenAPI specification  
3. **Generate** tests using AI (Python/pytest or Java/RestAssured)
4. **Save** locally and/or **push** to GitHub
5. **Trigger** Jenkins pipeline (automatic test execution)

## ✅ Setup (3 Minutes)

### 1. Configure Environment Variables

Copy the example and fill in your credentials:
```bash
cp env.example .env
```

Edit `.env`:
```env
# Jira Configuration
JIRA_BASE=https://your-domain.atlassian.net/
JIRA_USER=your-email@example.com
JIRA_TOKEN=your-jira-api-token

# GitHub Configuration
GITHUB_TOKEN=ghp_your_github_token
REPO_FULL_NAME=your-username/your-repo-name  # IMPORTANT: Must be username/repo

# OpenAI Configuration
OPENAI_API_KEY=sk-your_openai_api_key
```

### 2. Test Jira Connection

```bash
source .venv/bin/activate
python3 tests/test_jira_integration.py
```

Expected output:
```
✓ Successfully connected to Jira
✓ Successfully fetched Epic
✓ Found OpenAPI URL
```

### 3. Test GitHub Connection (Optional)

```bash
python3 test_github_config.py
```

Expected output:
```
✅ All tests passed!
Your GitHub integration is ready to use.
```

## 🎯 Usage

### Generate Python Tests (Local Only)

```bash
python3 test_orchestrator_flow.py KAN-4
```

**Output:**
- Tests saved to: `output/KAN-4_20231024_123456/`
- Files: `test_orders.py`, `conftest.py`, `requirements.txt`

### Generate Java Tests (Local Only)

```bash
python3 test_orchestrator_flow.py KAN-4 java
```

**Output:**
- Tests saved to: `output/KAN-4_20231024_123456/`
- Files: `OrdersApiTest.java`, `pom.xml`

### Generate & Push to GitHub (Triggers Jenkins)

```bash
python3 test_orchestrator_flow.py KAN-4 --github
```

**What happens:**
1. ✅ Tests generated locally
2. 🔀 New branch created: `auto/tests/KAN-4/20231024T123456Z`
3. 📤 Tests pushed to GitHub
4. 🔄 Jenkins pipeline triggered automatically
5. 💬 Jira comment posted with status

### Generate Java Tests & Push to GitHub

```bash
python3 test_orchestrator_flow.py KAN-4 java --github
```

## 📋 Creating a Jira Epic

Your Jira Epic description should include an OpenAPI URL:

### Example Epic Description:

```
We need to validate the Orders Service API.

OpenAPI Specification: http://localhost:8002/openapi.json

Requirements:
- Test all CRUD operations
- Validate error handling
- Check authentication
```

### Supported OpenAPI URL Formats:

- ✅ `http://localhost:8002/openapi.json`
- ✅ `http://localhost:8002/openapi.yaml`
- ✅ `http://localhost:8002/openapi` (auto-detects .json or .yaml)
- ✅ `https://api.example.com/swagger.json`
- ✅ `https://api.example.com/docs` (FastAPI docs endpoint)

## 🔧 Troubleshooting

### Issue: "REPO_FULL_NAME must be in 'username/repo-name' format"

**Fix:** Update `.env`:
```env
# Wrong:
REPO_FULL_NAME=api_testing_demo

# Correct:
REPO_FULL_NAME=abhishek2panigrahi/api_testing_demo
```

### Issue: "404 Not Found" from GitHub

**Causes:**
1. Repository doesn't exist
2. Repository name is incorrect
3. Token doesn't have access

**Fix:** 
1. Check repository exists: `https://github.com/username/repo-name`
2. Verify REPO_FULL_NAME format: `username/repo-name`
3. Check token permissions: https://github.com/settings/tokens

### Issue: "400 Bad Request" when posting to Jira

**Cause:** Jira API v3 requires ADF (Atlassian Document Format)

**Fix:** Already handled! Updated `integrations/jira/client.py` to use ADF format.

### Issue: "Failed to fetch OpenAPI spec"

**Causes:**
1. URL is incorrect
2. Service is not running
3. URL doesn't return valid JSON/YAML

**Fix:**
1. Test URL in browser: `http://localhost:8002/openapi.json`
2. Ensure service is running
3. Check URL returns valid OpenAPI spec

## 📊 Generated Test Examples

### Python/pytest Example:
```python
def test_place_order_success(client, valid_order_data):
    """Test successful order placement with valid data."""
    response = client.post(f"{BASE_URL}/orders", json=valid_order_data)
    assert response.status_code == 200
    assert "order_id" in response.json()
```

### Java/RestAssured Example:
```java
@Test
public void testPlaceOrderSuccess() {
    given()
        .contentType(ContentType.JSON)
        .body(orderPayload)
    .when()
        .post("/orders")
    .then()
        .statusCode(200)
        .body("order_id", notNullValue());
}
```

## 🚀 Production Deployment

### Option 1: Webhook Listener

Run the FastAPI webhook server:
```bash
uvicorn core.webhooks:app --host 0.0.0.0 --port 8000
```

Configure Jira webhook:
- URL: `http://your-server:8000/webhook/jira`
- Events: `Epic created`, `Epic updated`

### Option 2: Manual Trigger

Run on-demand for specific Epics:
```bash
python3 test_orchestrator_flow.py EPIC-KEY --github
```

### Option 3: Scheduled Job

Add to crontab for periodic processing:
```bash
# Run every hour
0 * * * * cd /path/to/api_testing_agent && python3 process_pending_epics.py
```

## 📁 Project Structure

```
api_testing_agent/
├── core/
│   ├── orchestrator.py        # Main workflow orchestration
│   └── webhooks.py             # Jira webhook handler
├── integrations/
│   ├── jira/
│   │   ├── client.py           # Jira API client
│   │   └── contract_parser.py  # OpenAPI extraction
│   └── github/
│       └── client.py           # GitHub API client
├── services/
│   ├── test_generator/
│   │   ├── generator.py        # LLM test generation
│   │   └── prompts.py          # Prompt templates
│   └── test_runner/
│       └── runner.py           # Docker test execution
├── tests/
│   └── test_jira_integration.py
├── output/                     # Generated tests (gitignored)
├── test_orchestrator_flow.py  # Manual testing script
├── test_github_config.py       # GitHub config validator
├── GITHUB_SETUP.md             # GitHub setup guide
└── README.md                   # Full documentation
```

## 🎯 Next Steps

1. ✅ Configure `.env` with your credentials
2. ✅ Test Jira connection: `python3 tests/test_jira_integration.py`
3. ✅ Test GitHub connection: `python3 test_github_config.py`
4. ✅ Generate tests locally: `python3 test_orchestrator_flow.py EPIC-KEY`
5. 🚀 Push to GitHub: `python3 test_orchestrator_flow.py EPIC-KEY --github`

## 🆘 Need Help?

- **Jira Issues:** Check `tests/test_jira_integration.py`
- **GitHub Issues:** Check `GITHUB_SETUP.md`
- **OpenAPI Issues:** Verify URL returns valid JSON/YAML
- **General Issues:** Check `README.md` for detailed documentation

## 📚 Additional Resources

- Full documentation: `README.md`
- GitHub setup guide: `GITHUB_SETUP.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- Architecture overview: `helper.md`

