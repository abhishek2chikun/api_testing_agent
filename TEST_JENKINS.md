# Testing Jenkins Integration 🧪

Quick guide to verify your Jenkins setup is working with the generated tests.

## 📋 What This Does

The `test_jenkins_integration.py` script automatically:
1. ✅ Checks if Jenkins is running
2. ✅ Verifies your Jenkins job exists
3. ✅ Finds your latest test branch
4. ✅ Checks build status
5. ✅ Shows test results
6. ✅ Can trigger builds manually

## 🚀 Quick Start

### Step 1: Make Sure Jenkins is Running

**macOS:**
```bash
brew services start jenkins-lts
```

**Docker:**
```bash
docker run -d -p 8080:8080 -p 50000:50000 \
  --name jenkins \
  -v jenkins_home:/var/jenkins_home \
  jenkins/jenkins:lts
```

**Check it's running:**
```bash
open http://localhost:8080
```

### Step 2: (Optional) Configure Jenkins Credentials

If Jenkins requires authentication, add to your `.env`:

```env
JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_TOKEN=your-jenkins-api-token
```

**To get Jenkins API token:**
1. Go to Jenkins → Your Name (top right) → Configure
2. Click "Add new Token" under API Token
3. Generate and copy the token
4. Add to `.env` file

### Step 3: Run the Test

**Test with your last commit:**
```bash
python3 tests/test_jenkins_integration.py
```

**Or specify a branch:**
```bash
python3 tests/test_jenkins_integration.py auto/tests/KAN-4/20251024T124535Z
```

## 📊 Example Output

### ✅ When Everything is Working:

```
╔==========================================================╗
║               JENKINS INTEGRATION TEST                   ║
╚==========================================================╝

============================================================
🔧 Jenkins Connection Test
============================================================

Jenkins URL: http://localhost:8080

✅ Jenkins is running!
   Version: 2.401.1

============================================================
📋 Checking Jenkins Job
============================================================

✅ Job 'API-Testing-Agent' exists!
   Type: Multibranch Pipeline

   Found 3 branch(es):
     - auto%2Ftests%2FKAN-4%2F20251024T124535Z
     - auto%2Ftests%2FKAN-4%2F20251024T090613Z
     - main

============================================================
🔍 Testing Branch Detection
============================================================

Looking for branch: auto/tests/KAN-4/20251024T124535Z

============================================================
🔨 Build Status
============================================================

Branch: auto/tests/KAN-4/20251024T124535Z
Build: #1
URL: http://localhost:8080/job/API-Testing-Agent/.../1/

Status: ✅ SUCCESS
Duration: 45.2s

Test Results:
  ✅ Passed: 8
  ❌ Failed: 0
  ⊘ Skipped: 0
  Total: 8

============================================================
📊 Test Summary
============================================================

Jenkins URL: http://localhost:8080
Job Name: API-Testing-Agent
Branch: auto/tests/KAN-4/20251024T124535Z
Status: SUCCESS

✅ Jenkins integration is working perfectly!

Your complete pipeline is operational:
  Jira → Python → GitHub → Jenkins → Results
```

### ⚠️  When Jenkins Isn't Set Up Yet:

```
❌ Jenkins is not accessible. Please start Jenkins first.

To start Jenkins:
  - macOS: brew services start jenkins-lts
  - Docker: docker run -p 8080:8080 jenkins/jenkins:lts
  - Linux: sudo systemctl start jenkins
```

### ℹ️  When Job Doesn't Exist:

```
❌ Job 'API-Testing-Agent' not found

To create the job:
  1. Go to Jenkins → New Item
  2. Enter name: API-Testing-Agent
  3. Select: Multibranch Pipeline
  4. Configure GitHub source
  5. Set branch filter: auto/tests/*
```

### 🔄 When Build Hasn't Run Yet:

```
⚠️  Branch 'auto/tests/KAN-4/20251024T124535Z' not found in Jenkins

Possible reasons:
  1. Branch hasn't been scanned yet
  2. Branch doesn't match filter (auto/tests/*)
  3. Jenkins needs manual scan

Trigger build now? (yes/no): yes

✅ Build triggered successfully!
Build triggered! Monitoring progress...
```

## 🔧 Troubleshooting

### Issue: "Jenkins is not accessible"

**Cause:** Jenkins isn't running

**Solution:**
```bash
# macOS
brew services start jenkins-lts

# Docker
docker start jenkins
# or
docker run -p 8080:8080 jenkins/jenkins:lts

# Linux
sudo systemctl start jenkins
```

### Issue: "Authentication failed"

**Cause:** Jenkins requires login credentials

**Solution:**
1. Get API token from Jenkins (User → Configure → API Token)
2. Add to `.env`:
   ```env
   JENKINS_USER=admin
   JENKINS_TOKEN=11234567890abcdef1234567890abcdef
   ```

### Issue: "Job not found"

**Cause:** Jenkins job hasn't been created

**Solution:**
Follow `JENKINS_QUICK_START.md` to create the job (takes 5 minutes)

### Issue: "Branch not found"

**Cause:** Jenkins hasn't scanned for new branches yet

**Solution:**
The script will offer to trigger a scan. Answer `yes` when prompted.

## 📝 Script Features

### Automatic Detection

The script automatically uses your most recent branch:
```bash
# Automatically uses: auto/tests/KAN-4/20251024T124535Z
python3 tests/test_jenkins_integration.py
```

### Manual Branch Selection

Test any specific branch:
```bash
python3 tests/test_jenkins_integration.py auto/tests/KAN-4/20251024T090613Z
```

### Interactive Build Triggering

If a branch hasn't been built, the script offers to trigger it:
```
Trigger build now? (yes/no): yes
✅ Build triggered successfully!
Build triggered! Monitoring progress...
```

### Build Monitoring

Automatically monitors build progress for up to 2 minutes:
```
Checking status... (1/12)
Checking status... (2/12)
...
Status: ✅ SUCCESS
```

## 🎯 Use Cases

### 1. Verify Jenkins Setup

```bash
# Check if Jenkins is configured correctly
python3 tests/test_jenkins_integration.py
```

### 2. Test Latest Commit

```bash
# Test the branch you just pushed
python3 test_orchestrator_flow.py KAN-4 --github
python3 tests/test_jenkins_integration.py
```

### 3. Debug Failed Builds

```bash
# Check why a build failed
python3 tests/test_jenkins_integration.py auto/tests/KAN-4/failed-branch
```

### 4. Monitor Build Progress

```bash
# Watch a build in real-time
python3 tests/test_jenkins_integration.py
# Script will monitor and show results
```

## 🔄 Complete Workflow Test

Test the entire pipeline end-to-end:

```bash
# 1. Generate and push tests
python3 test_orchestrator_flow.py KAN-4 java --github

# 2. Test Jenkins integration
python3 tests/test_jenkins_integration.py

# 3. View results
# - Check Jenkins UI
# - Check Jira comment
# - Review local output/
```

## 📊 What Success Looks Like

When everything is working, you should see:

1. ✅ Jenkins connection successful
2. ✅ Job exists with branches listed
3. ✅ Build completed (SUCCESS/UNSTABLE/FAILURE)
4. ✅ Test results displayed (passed/failed counts)
5. ✅ Links to Jenkins UI for details

## 🚀 Next Steps

Once the test passes:

1. **Automate:** Set up GitHub webhook for instant builds
2. **Monitor:** Use Jenkins UI to watch builds
3. **Extend:** Add Slack/email notifications
4. **Scale:** Add more test scenarios

## 📚 Related Documentation

- **Jenkins Setup**: `JENKINS_QUICK_START.md`
- **Complete Workflow**: `COMPLETE_WORKFLOW.md`
- **GitHub Setup**: See `README.md`

---

**Your Jenkins integration test script is ready to use!** 🎉

Just make sure Jenkins is running and configured, then run:
```bash
python3 tests/test_jenkins_integration.py
```

