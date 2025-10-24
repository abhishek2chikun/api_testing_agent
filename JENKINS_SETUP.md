# Jenkins Pipeline Setup Guide 🔧

This guide will help you set up Jenkins to automatically run generated tests when pushed to GitHub.

## 📋 Prerequisites

- Jenkins installed and running
- Jenkins plugins installed:
  - Git Plugin
  - GitHub Plugin
  - Pipeline Plugin
  - Docker Pipeline Plugin (if using Docker)
  - JUnit Plugin
  - HTML Publisher Plugin

## 🚀 Step-by-Step Setup

### Step 1: Install Required Jenkins Plugins

1. Go to **Jenkins Dashboard** → **Manage Jenkins** → **Manage Plugins**
2. Click **Available** tab
3. Install these plugins:
   - ✅ Git Plugin
   - ✅ GitHub Plugin
   - ✅ Pipeline Plugin
   - ✅ Docker Pipeline Plugin
   - ✅ JUnit Plugin
   - ✅ HTML Publisher Plugin
   - ✅ Credentials Binding Plugin
4. Click **Install without restart**

### Step 2: Configure GitHub Credentials

1. Go to **Jenkins Dashboard** → **Manage Jenkins** → **Manage Credentials**
2. Click **(global)** domain → **Add Credentials**
3. Configure:
   - **Kind**: Secret text
   - **Secret**: Your GitHub Personal Access Token
   - **ID**: `github-token`
   - **Description**: GitHub Access Token
4. Click **OK**

### Step 2.5: Configure Build Tools (Maven for Java tests)

If you plan to run Java/RestAssured tests, configure Maven:

1. Go to **Manage Jenkins** → **Global Tool Configuration**
2. Scroll to **Maven** section
3. Click **Add Maven**
4. Configure:
   - **Name**: `Maven-3.9.6` (must match the name in Jenkinsfile)
   - **Install automatically**: ✅ Check this
   - **Install from Apache**: Select version `3.9.6` or latest
5. Optional: Also configure JDK if needed:
   - Scroll to **JDK** section
   - Click **Add JDK**
   - **Name**: `JDK-17`
   - **Install automatically**: ✅ Check this
   - Select OpenJDK 17 or your preferred version
6. Click **Save**

**What this does:**
- Jenkins will automatically download and install Maven on first use
- The `Jenkinsfile` references this tool via the `tools` directive
- Maven becomes available in PATH for all pipeline stages

### Step 3: Configure Jira Credentials (Optional)

If you want to post test results back to Jira:

1. Go to **Manage Jenkins** → **Manage Credentials**
2. Add new credentials:
   - **Kind**: Username with password
   - **Username**: Your Jira email
   - **Password**: Your Jira API token
   - **ID**: `jira-credentials`
   - **Description**: Jira API Credentials
3. Click **OK**

### Step 4: Create Multibranch Pipeline Job

1. Go to **Jenkins Dashboard** → **New Item**
2. Enter name: `API-Testing-Agent`
3. Select **Multibranch Pipeline**
4. Click **OK**

### Step 5: Configure Branch Sources

1. Under **Branch Sources**, click **Add source** → **GitHub**
2. Configure:
   - **Credentials**: Select `github-token`
   - **Repository HTTPS URL**: `https://github.com/abhishek2chikun/api_testing_demo`
   - **Behaviors**: Add **Filter by name (with wildcards)**
     - **Include**: `auto/tests/*`
     - This ensures only test branches trigger builds
3. Click **Save**

### Step 6: Configure Build Triggers

1. In the job configuration, scroll to **Scan Multibranch Pipeline Triggers**
2. Check **Periodically if not otherwise run**
   - **Interval**: 5 minutes
3. Or set up **GitHub webhook** (recommended for instant triggers):
   - Go to your GitHub repository settings
   - Click **Webhooks** → **Add webhook**
   - **Payload URL**: `http://your-jenkins-url/github-webhook/`
   - **Content type**: `application/json`
   - **Events**: Select "Just the push event"
   - Click **Add webhook**

### Step 7: Add Jenkinsfiles to Repository

Jenkins will automatically detect and use `Jenkinsfile` in your branches.

We'll create Jenkinsfiles that detect whether it's Python or Java tests and run accordingly.

## 📝 Pipeline Scripts

### Option 1: Auto-Detect Language (Recommended)

Create this file in your repository root:

**`Jenkinsfile`**
```groovy
pipeline {
    agent any
    
    environment {
        JIRA_CREDENTIALS = credentials('jira-credentials')
    }
    
    stages {
        stage('Detect Test Type') {
            steps {
                script {
                    // Check if it's a Java project
                    if (fileExists('pom.xml')) {
                        env.TEST_TYPE = 'java'
                        echo "Detected Java/RestAssured tests"
                    } 
                    // Check if it's a Python project
                    else if (fileExists('tests/requirements.txt') || fileExists('requirements.txt')) {
                        env.TEST_TYPE = 'python'
                        echo "Detected Python/pytest tests"
                    }
                    else {
                        error "Could not detect test type (no pom.xml or requirements.txt found)"
                    }
                }
            }
        }
        
        stage('Setup Python Environment') {
            when {
                expression { env.TEST_TYPE == 'python' }
            }
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r tests/requirements.txt || pip install -r requirements.txt
                '''
            }
        }
        
        stage('Run Python Tests') {
            when {
                expression { env.TEST_TYPE == 'python' }
            }
            steps {
                sh '''
                    . venv/bin/activate
                    cd tests || true
                    pytest --junitxml=../test-results.xml --html=../report.html --self-contained-html || true
                '''
            }
        }
        
        stage('Setup Java Environment') {
            when {
                expression { env.TEST_TYPE == 'java' }
            }
            steps {
                sh '''
                    java -version
                    mvn -version
                '''
            }
        }
        
        stage('Run Java Tests') {
            when {
                expression { env.TEST_TYPE == 'java' }
            }
            steps {
                sh '''
                    mvn clean test -Dmaven.test.failure.ignore=true
                '''
            }
        }
        
        stage('Publish Results') {
            steps {
                script {
                    // Publish JUnit test results
                    if (env.TEST_TYPE == 'python') {
                        junit 'test-results.xml'
                        publishHTML([
                            reportDir: '.',
                            reportFiles: 'report.html',
                            reportName: 'Test Report',
                            keepAll: true
                        ])
                    } else if (env.TEST_TYPE == 'java') {
                        junit 'target/surefire-reports/*.xml'
                    }
                }
            }
        }
        
        stage('Post to Jira') {
            steps {
                script {
                    // Extract Epic key from branch name (e.g., auto/tests/KAN-4/timestamp)
                    def branchParts = env.BRANCH_NAME.split('/')
                    if (branchParts.size() >= 3) {
                        env.EPIC_KEY = branchParts[2]
                        
                        def testResults = currentBuild.result ?: 'SUCCESS'
                        def testCount = 0
                        def passCount = 0
                        def failCount = 0
                        
                        // Get test counts
                        if (env.TEST_TYPE == 'python') {
                            // Parse pytest results
                            def summary = sh(
                                script: "grep -oP '\\d+ passed' test-results.xml | grep -oP '\\d+' || echo '0'",
                                returnStdout: true
                            ).trim()
                            passCount = summary ? summary.toInteger() : 0
                            
                            def failSummary = sh(
                                script: "grep -oP '\\d+ failed' test-results.xml | grep -oP '\\d+' || echo '0'",
                                returnStdout: true
                            ).trim()
                            failCount = failSummary ? failSummary.toInteger() : 0
                        } else {
                            // Parse Maven surefire results
                            def summary = sh(
                                script: "mvn surefire-report:report-only && grep -oP 'Tests run: \\d+' target/surefire-reports/*.txt | head -1 | grep -oP '\\d+' || echo '0'",
                                returnStdout: true
                            ).trim()
                            testCount = summary ? summary.toInteger() : 0
                        }
                        
                        // Post comment to Jira
                        def framework = env.TEST_TYPE == 'python' ? 'pytest' : 'RestAssured'
                        def comment = """
Test Execution Complete

Framework: ${framework}
Status: ${testResults}
Passed: ${passCount}
Failed: ${failCount}
Build URL: ${env.BUILD_URL}

Branch: ${env.BRANCH_NAME}
"""
                        
                        echo "Would post to Jira Epic: ${env.EPIC_KEY}"
                        echo comment
                        
                        // Uncomment to actually post to Jira:
                        // sh """
                        // curl -X POST \\
                        //   -u "\${JIRA_CREDENTIALS_USR}:\${JIRA_CREDENTIALS_PSW}" \\
                        //   -H "Content-Type: application/json" \\
                        //   -d '{"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "${comment}"}]}]}}' \\
                        //   "https://your-domain.atlassian.net/rest/api/3/issue/${env.EPIC_KEY}/comment"
                        // """
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            echo '✅ Tests passed successfully!'
        }
        failure {
            echo '❌ Tests failed!'
        }
    }
}
```

### Option 2: Separate Jenkinsfiles

If you prefer separate pipelines for Python and Java:

**`Jenkinsfile.python`**
```groovy
pipeline {
    agent any
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r tests/requirements.txt
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    cd tests
                    pytest -v --junitxml=../test-results.xml --html=../report.html --self-contained-html
                '''
            }
        }
        
        stage('Publish Results') {
            steps {
                junit 'test-results.xml'
                publishHTML([
                    reportDir: '.',
                    reportFiles: 'report.html',
                    reportName: 'Test Report'
                ])
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}
```

**`Jenkinsfile.java`**
```groovy
pipeline {
    agent any
    
    tools {
        maven 'Maven 3.8'
        jdk 'JDK 11'
    }
    
    stages {
        stage('Build') {
            steps {
                sh 'mvn clean compile'
            }
        }
        
        stage('Run Tests') {
            steps {
                sh 'mvn test'
            }
        }
        
        stage('Publish Results') {
            steps {
                junit 'target/surefire-reports/*.xml'
                publishHTML([
                    reportDir: 'target/surefire-reports',
                    reportFiles: 'index.html',
                    reportName: 'Test Report'
                ])
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
    }
}
```

## 🐳 Docker-Based Pipeline (Advanced)

For isolated test execution:

**`Jenkinsfile.docker`**
```groovy
pipeline {
    agent any
    
    stages {
        stage('Detect & Run Tests') {
            steps {
                script {
                    if (fileExists('pom.xml')) {
                        // Java tests in Docker
                        docker.image('maven:3.8-openjdk-11').inside {
                            sh 'mvn clean test'
                        }
                        junit 'target/surefire-reports/*.xml'
                    } else {
                        // Python tests in Docker
                        docker.image('python:3.9').inside {
                            sh '''
                                pip install -r tests/requirements.txt
                                cd tests && pytest -v --junitxml=../test-results.xml
                            '''
                        }
                        junit 'test-results.xml'
                    }
                }
            }
        }
    }
}
```

## 🔄 Automatic Test Execution Flow

```
1. Developer triggers: python3 test_orchestrator_flow.py KAN-4 --github
2. Tests pushed to branch: auto/tests/KAN-4/20251024T123456Z
3. GitHub webhook triggers Jenkins
4. Jenkins detects branch matching auto/tests/*
5. Jenkins pulls code and detects test type (Python/Java)
6. Jenkins runs appropriate test suite
7. Jenkins publishes test results
8. Jenkins posts results to Jira Epic (optional)
```

## 📊 Configure Test Result Parsing

### For Python/pytest:

Install pytest plugins in your test requirements:
```bash
pip install pytest-html pytest-cov pytest-xdist
```

Run with reporting:
```bash
pytest -v \
  --junitxml=test-results.xml \
  --html=report.html \
  --cov=. \
  --cov-report=html
```

### For Java/Maven:

Add to your `pom.xml`:
```xml
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <version>2.22.2</version>
    <configuration>
        <testFailureIgnore>true</testFailureIgnore>
    </configuration>
</plugin>
```

## 🔐 Security Best Practices

1. **Use Jenkins Credentials**: Never hardcode tokens
2. **Restrict Job Permissions**: Only allow authorized users
3. **Use HTTPS**: For Jenkins and webhooks
4. **Rotate Tokens**: Regularly update GitHub and Jira tokens
5. **Audit Logs**: Monitor Jenkins build logs

## 🧪 Test Your Pipeline

1. **Manual Trigger**:
   ```bash
   python3 test_orchestrator_flow.py KAN-4 --github
   ```

2. **Check Jenkins**:
   - Go to Jenkins Dashboard
   - Find `API-Testing-Agent` job
   - You should see new branch appear automatically
   - Click on branch to see build progress

3. **View Results**:
   - Click on build number
   - View **Test Results** tab
   - View **HTML Report** (if configured)
   - Check **Console Output** for logs

## 🎯 Customization Options

### Add Slack Notifications

Add to Jenkinsfile:
```groovy
post {
    success {
        slackSend(color: 'good', message: "Tests passed: ${env.JOB_NAME} ${env.BUILD_NUMBER}")
    }
    failure {
        slackSend(color: 'danger', message: "Tests failed: ${env.JOB_NAME} ${env.BUILD_NUMBER}")
    }
}
```

### Add Email Notifications

Add to Jenkinsfile:
```groovy
post {
    always {
        emailext(
            to: 'team@example.com',
            subject: "Test Results: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
            body: "Build URL: ${env.BUILD_URL}",
            attachLog: true
        )
    }
}
```

### Parallel Test Execution

For faster execution:
```groovy
stage('Run Tests') {
    parallel {
        stage('Unit Tests') {
            steps {
                sh 'pytest tests/unit -v'
            }
        }
        stage('Integration Tests') {
            steps {
                sh 'pytest tests/integration -v'
            }
        }
    }
}
```

## 🐛 Troubleshooting

### Issue: Jenkins not detecting branches

**Solution**:
1. Check branch name pattern in configuration
2. Verify GitHub webhook is configured
3. Manually trigger "Scan Multibranch Pipeline Now"

### Issue: Tests failing in Jenkins but passing locally

**Solution**:
1. Check environment variables in Jenkins
2. Verify dependencies are installed
3. Check file paths (use absolute paths when possible)
4. Review Jenkins console output for errors

### Issue: Jira comment not posting

**Solution**:
1. Verify Jira credentials in Jenkins
2. Check Jira base URL in script
3. Ensure Epic key is extracted correctly
4. Test Jira API with curl manually

## 📚 Additional Resources

- [Jenkins Pipeline Documentation](https://www.jenkins.io/doc/book/pipeline/)
- [GitHub Webhooks](https://docs.github.com/webhooks)
- [Jira REST API](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)

## ✅ Verification Checklist

- [ ] Jenkins plugins installed
- [ ] GitHub credentials configured
- [ ] Jira credentials configured (optional)
- [ ] Multibranch pipeline created
- [ ] Branch filter set to `auto/tests/*`
- [ ] GitHub webhook configured
- [ ] Jenkinsfile added to repository
- [ ] Test pipeline with sample branch
- [ ] Verify test results appear in Jenkins
- [ ] Verify Jira comment posted (if enabled)

---

Your Jenkins pipeline is now ready to automatically run tests when pushed from the API Testing Agent! 🚀

