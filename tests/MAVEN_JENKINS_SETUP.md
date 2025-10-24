# Configure Maven in Jenkins - Quick Guide

## Problem
Jenkins build fails with `mvn: not found` error when running Java tests.

## Solution: Configure Maven Tool (2 minutes)

### Step 1: Configure Maven in Jenkins UI

1. **Open Jenkins**: Go to `http://localhost:8080`

2. **Navigate to Tool Configuration**:
   - Click **Manage Jenkins** (left sidebar)
   - Click **Global Tool Configuration**

3. **Scroll to Maven Section**:
   - Scroll down to find **Maven** section
   - Click **Add Maven** button

4. **Configure Maven**:
   ```
   Name: Maven-3.9.6
   ☑ Install automatically
   Install from Apache: 3.9.6 (or latest version from dropdown)
   ```

5. **Save**:
   - Click **Save** button at the bottom

### Step 2: Push Updated Jenkinsfile to GitHub

The Jenkinsfile has been updated with the `tools` directive that references Maven.

```bash
# Add and commit the updated Jenkinsfile
git add Jenkinsfile JENKINS_QUICK_START.md JENKINS_SETUP.md MAVEN_JENKINS_SETUP.md
git commit -m "Configure Maven tool for Jenkins pipeline"
git push origin main
```

### Step 3: Re-trigger the Build

After configuring Maven in Jenkins:

**Option A: Using the test script**
```bash
python3 tests/test_jenkins_integration.py
```

**Option B: Manually in Jenkins**
1. Go to Jenkins Dashboard
2. Click on `API-Testing-Agent` job
3. Click **Scan Multibranch Pipeline Now**
4. Find the branch: `auto/tests/KAN-4/...`
5. Click **Build Now**

**Option C: Generate a new test**
```bash
python3 test_orchestrator_flow.py KAN-4 java --github
```

### What Happens on First Run?

When the build runs for the first time:
- ⏳ Jenkins downloads Maven (~2-3 minutes)
- 📦 Installs it in Jenkins workspace
- ✅ Maven becomes available for all future builds
- 🚀 Subsequent builds are fast (Maven already installed)

### Expected Output

In the Jenkins build console, you should now see:

```
[Pipeline] stage
[Pipeline] { (Setup Java Environment)
[Pipeline] echo
📦 Setting up Java environment...
[Pipeline] sh
+ echo Java version:
Java version:
+ java -version
openjdk version "17.0.16" 2025-07-15
+ echo

+ echo Maven version:
Maven version:
+ mvn -version
Apache Maven 3.9.6
Maven home: /var/jenkins_home/tools/hudson.tasks.Maven_MavenInstallation/Maven-3.9.6
```

### Troubleshooting

**Q: Still getting "mvn: not found"?**

A: Make sure:
1. Maven name in Jenkins is **exactly** `Maven-3.9.6`
2. Jenkinsfile has been updated and pushed to GitHub
3. You re-scanned the repository in Jenkins

**Q: Want to use a different Maven version?**

A: Update both places:
- Jenkins: Global Tool Configuration → Maven → Name: `Maven-X.Y.Z`
- Jenkinsfile: `tools { maven 'Maven-X.Y.Z' }`

**Q: Build takes too long on first run?**

A: Normal! Jenkins is downloading Maven. First build: ~3-5 min. Subsequent builds: ~30 sec - 2 min.

---

## Summary

✅ **Updated Files:**
- `Jenkinsfile` - Added `tools { maven 'Maven-3.9.6' }`
- `JENKINS_QUICK_START.md` - Added Step 3.5
- `JENKINS_SETUP.md` - Added Step 2.5

🎯 **Next Steps:**
1. Configure Maven in Jenkins UI (above)
2. Commit and push the updated files
3. Trigger a new build
4. Watch it succeed! 🎉

