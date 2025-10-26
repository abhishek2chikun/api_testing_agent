# Complete End-to-End Workflow 🔄

## 📊 Mermaid Flow Diagrams

### Complete System Flow (Jira to Jenkins)

```mermaid
graph TB
    subgraph Input["🔹 Input Sources"]
        Jira[Jira Epic<br/>OpenAPI URL + Requirements]
        Webhook[FastAPI Webhook<br/>/jira/webhook]
        Runner[Polling Runner<br/>time_sleep + prefix]
    end

    subgraph Config["⚙️ Configuration"]
        YAML[config.yaml<br/>runner.prefix_jira_name<br/>openai.review_threshold<br/>models]
        ENV[.env secrets<br/>JIRA_TOKEN<br/>GITHUB_TOKEN<br/>OPENAI_API_KEY]
    end

    subgraph Orchestrator["🎯 Orchestration Pipeline"]
        Fetch[Fetch Epic<br/>fetch_issue]
        Parse[Parse Contract<br/>extract_contract]
        
        subgraph AI["🤖 AI Processing Chain"]
            AI1[AI-1: Eligibility Gate<br/>check_epic_eligibility<br/>should_proceed: bool]
            AI2[AI-2: Test Generator<br/>generate_tests<br/>pytest/RestAssured]
            AI3[AI-3: Review<br/>review_and_fix_tests<br/>score + notes]
            AI4[AI-4: Refine<br/>refine_tests_with_notes<br/>corrected files]
        end
        
        Decision{avg score<br/><= threshold?}
        SaveMeta[Save metadata.json<br/>gate+testcases+reviewer+refiner]
        SaveLocal[Save Locally<br/>output/EPIC_timestamp/]
    end

    subgraph Deployment["🚀 Deployment & CI/CD"]
        GitHub[Push to GitHub<br/>auto/tests/EPIC/timestamp]
        Jenkins[Jenkins Pipeline<br/>pytest/mvn test<br/>JUnit results]
        Comment[Post to Jira<br/>test results + branch]
    end

    Jira -->|webhook event| Webhook
    Jira -.->|JQL poll| Runner
    Webhook -->|prefix filter| Fetch
    Runner -->|prefix filter| Fetch
    
    YAML -.->|config| Runner
    YAML -.->|thresholds| Decision
    ENV -.->|secrets| AI

    Fetch --> Parse
    Parse --> AI1
    
    AI1 -->|false| Comment
    AI1 -->|true| AI2
    AI2 --> AI3
    AI3 --> Decision
    
    Decision -->|yes| AI4
    Decision -->|no| SaveMeta
    AI4 --> SaveMeta
    
    SaveMeta --> SaveLocal
    SaveLocal -->|optional| GitHub
    GitHub --> Jenkins
    Jenkins --> Comment

    style AI1 fill:#e1f5ff
    style AI2 fill:#fff9e1
    style AI3 fill:#ffe1f5
    style AI4 fill:#e1ffe1
    style Decision fill:#ffd700
```

---

## 🔄 Detailed Workflow

### Phase 1: Epic Creation & Configuration

```
Developer creates Jira Epic
       │
       ├─ Summary: "QA Validation for Orders Service API"
       │
       └─ Description:
          ├─ OpenAPI URL: http://localhost:8002/openapi.json
          ├─ Requirements
          └─ Test scenarios
```

### Phase 2: Test Generation (with eligibility gate)

```bash
# Direct single-epic run (new CLI)
python3 tests/test_orchestrator_flow.py --jira_name KAN-4 --language python --jenkins yes

# Or start the polling runner (process epics by project prefix)
python3 tests/test_orchestrator_flow.py --runner on --language python --jenkins no
```

**What Happens:**

```
Step 1: Fetch Epic from Jira
   ↓
   ├─ Connect to Jira API
   ├─ Fetch Epic details (KAN-4)
   └─ Extract summary & description
   
Step 2: Extract OpenAPI Specification
   ↓
   ├─ Parse Epic description for OpenAPI URL
   ├─ Fetch OpenAPI spec (http://localhost:8002/openapi.json)
   ├─ Parse JSON/YAML format
   └─ Extract 4 endpoints
   
Eligibility Gate (LLM)
   ↓
   ├─ Validate presence of OpenAPI URL or concrete endpoints
   ├─ Optionally verify accessibility signals
   └─ Decide: {"should_proceed": true|false, "reason": "..."}
      └─ If false → skip pipeline and post comment to Jira
   
Step 3: Generate Tests with LLM (only if should_proceed=true)
   ↓
   ├─ Build prompt with Epic + OpenAPI spec
   ├─ Call OpenAI model (configurable)
   ├─ Parse response
   └─ Generate 4-5 test files:
      ├─ tests/conftest.py (fixtures)
      ├─ tests/test_orders.py (main tests)
      ├─ tests/test_schemathesis.py (property tests)
      ├─ tests/requirements.txt (dependencies)
      └─ tests/README.md (documentation)
   
Step 4: Save Tests Locally
   ↓
   └─ output/KAN-4_20251024_124753/
      ├─ tests/
      └─ GENERATION_INFO.txt
   
Step 5: Push to GitHub
   ↓
   ├─ Create branch: auto/tests/KAN-4/20251024T071757Z
   ├─ Commit all test files
   ├─ Push to GitHub
   └─ Post comment to Jira Epic
```

### Phase 3: Jenkins Automation

```
GitHub receives push
   ↓
Webhook triggers Jenkins
   ↓
Jenkins detects new branch matching "auto/tests/*"
   ↓
   ├─ Clone repository
   ├─ Read Jenkinsfile
   └─ Start pipeline
   
Pipeline Execution:
   ↓
   ├─ Stage 1: Checkout
   │  └─ Pull code from branch
   │
   ├─ Stage 2: Detect Test Type
   │  ├─ Check for pom.xml (Java)
   │  └─ Check for tests/requirements.txt (Python)
   │
   ├─ Stage 3: Setup Environment
   │  ├─ Python: Create venv, install deps
   │  └─ Java: Verify Maven, JDK
   │
   ├─ Stage 4: Run Tests
   │  ├─ Python: pytest -v --junitxml --html
   │  └─ Java: mvn clean test
   │
   ├─ Stage 5: Publish Results
   │  ├─ Parse JUnit XML
   │  ├─ Generate HTML report
   │  └─ Archive artifacts
   │
   └─ Stage 6: Post Results
      ├─ Update Jira Epic with results
      ├─ Send notifications (email/Slack)
      └─ Mark build as SUCCESS/FAILURE
```

### Phase 4: Results & Reporting

```
Test Results Published:
   ↓
   ├─ Jenkins UI
   │  ├─ Test Results tab
   │  ├─ HTML Report
   │  └─ Console Output
   │
   ├─ Jira Epic Comment
   │  ├─ Test summary
   │  ├─ Pass/Fail counts
   │  └─ Build URL
   │
   └─ Notifications
      ├─ Email to team
      └─ Slack message
```

## 🚀 Quick Commands (updated)

```bash
# Direct single-epic run (python)
python3 tests/test_orchestrator_flow.py --jira_name KAN-4 --language python --jenkins yes

# Direct single-epic run (java)
python3 tests/test_orchestrator_flow.py --jira_name KAN-4 --language java --jenkins yes

# Start polling runner (no GitHub push)
python3 tests/test_orchestrator_flow.py --runner on --language python --jenkins no

# Start service + runner
python3 main.py --runner on --language python --jenkins no --port 8002

# Test configuration and integrations
python3 tests/test_jira_integration.py
python3 tests/test_github_config.py
python3 setup_jenkins_integration.py
```

## 📚 Documentation

- **Quick Start**: `QUICK_START.md`
- **GitHub Setup**: `GITHUB_SETUP.md`
- **Jenkins Setup**: `JENKINS_SETUP.md`
- **Jenkins Quick Start**: `JENKINS_QUICK_START.md`
- **Full Documentation**: `README.md`
- **Architecture**: `helper.md`
- **Implementation**: `IMPLEMENTATION_SUMMARY.md`

## 🎉 Success Metrics

Your system is working when:
- ✅ Tests generate in < 30 seconds
- ✅ GitHub push successful
- ✅ Jenkins build starts automatically
- ✅ Test results appear in Jenkins
- ✅ Jira comment posted with results

---

**Congratulations! Your API Testing Agent is fully operational! 🚀**

