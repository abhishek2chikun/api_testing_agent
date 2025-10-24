# GitHub Integration Setup Guide

## Quick Fix

Your `.env` file needs `REPO_FULL_NAME` in the format: `username/repository-name`

### Step 1: Find Your GitHub Username

Visit: https://github.com/ (when logged in, your username appears in the top right)

### Step 2: Choose Repository

**Option A: Use Existing Repository**
1. Go to your GitHub repositories
2. Note the full name (e.g., `abhishek2panigrahi/api_testing_demo`)
3. Update `.env`:
   ```
   REPO_FULL_NAME=your-username/your-repo-name
   ```

**Option B: Create New Repository**
1. Go to: https://github.com/new
2. Create a repository named: `api_testing_demo` (or any name)
3. Initialize with README (optional)
4. Update `.env`:
   ```
   REPO_FULL_NAME=your-username/api_testing_demo
   ```

### Step 3: Verify Your Token Has Access

Your GitHub Personal Access Token needs these permissions:
- ✅ `repo` (Full control of private repositories)
- ✅ `workflow` (Update GitHub Action workflows) - optional

To check/update your token:
1. Go to: https://github.com/settings/tokens
2. Find your token or create a new one
3. Ensure `repo` scope is checked
4. Copy the token and update `.env`:
   ```
   GITHUB_TOKEN=ghp_your_token_here
   ```

### Step 4: Test Configuration

Run the test script:
```bash
python3 test_github_config.py
```

You should see:
```
✅ All tests passed!
Your GitHub integration is ready to use.
```

### Step 5: Test with Jira Epic

Once configuration passes, test the full flow:

**Local only (no GitHub push):**
```bash
python3 test_orchestrator_flow.py KAN-4
```

**With GitHub push (triggers Jenkins):**
```bash
python3 test_orchestrator_flow.py KAN-4 --github
```

**Java tests with GitHub push:**
```bash
python3 test_orchestrator_flow.py KAN-4 java --github
```

## Example `.env` File

```env
# Jira Configuration
JIRA_BASE=https://abhishek2panigrahi.atlassian.net/
JIRA_USER=abhishek2chikun@gmail.com
JIRA_TOKEN=ATATT3xFfGF0aBcD123...

# GitHub Configuration (UPDATE THESE)
GITHUB_TOKEN=ghp_YourGitHubTokenHere123
REPO_FULL_NAME=abhishek2panigrahi/api_testing_demo

# OpenAI Configuration  
OPENAI_API_KEY=sk-YourOpenAIKeyHere123
```

## Troubleshooting

### Error: "404 Not Found"
- Repository doesn't exist or name is wrong
- Token doesn't have access to the repository
- Fix: Check repository name and token permissions

### Error: "401 Unauthorized"  
- Token is invalid or expired
- Fix: Create new token at https://github.com/settings/tokens

### Error: "403 Forbidden"
- Token doesn't have write access
- Fix: Ensure token has `repo` scope

## What Happens When You Push?

1. Tests are generated locally: `output/EPIC-KEY_timestamp/`
2. New branch created: `auto/tests/EPIC-KEY/timestamp`
3. Tests committed to GitHub branch
4. Jenkins pipeline automatically triggered (if configured)
5. Jira Epic comment posted with results

## Jenkins Integration (Optional)

For Jenkins to automatically run tests when pushed:

1. Configure Jenkins to monitor your repository
2. Set up webhook or branch scanning
3. Jenkins detects new branch: `auto/tests/**`
4. Runs tests automatically
5. Posts results back to Jira (configure in Jenkins)


