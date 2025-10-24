// Jenkinsfile for API Testing Agent
// Auto-detects Python or Java tests and runs them accordingly

pipeline {
    agent any
    
    environment {
        // Extract Epic key from branch name (e.g., auto/tests/KAN-4/timestamp -> KAN-4)
        EPIC_KEY = sh(
            script: "echo ${env.BRANCH_NAME} | cut -d'/' -f3",
            returnStdout: true
        ).trim()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    echo "================================"
                    echo "API Testing Agent - Jenkins Pipeline"
                    echo "================================"
                    echo "Branch: ${env.BRANCH_NAME}"
                    echo "Epic Key: ${env.EPIC_KEY}"
                    echo "Build: ${env.BUILD_NUMBER}"
                    echo "================================"
                }
            }
        }
        
        stage('Detect Test Type') {
            steps {
                script {
                    // Check directory structure to determine test type
                    if (fileExists('pom.xml')) {
                        env.TEST_TYPE = 'java'
                        env.TEST_FRAMEWORK = 'RestAssured + JUnit5'
                        echo "✓ Detected Java/RestAssured tests"
                    } 
                    else if (fileExists('tests/requirements.txt') || fileExists('tests/conftest.py')) {
                        env.TEST_TYPE = 'python'
                        env.TEST_FRAMEWORK = 'pytest + Schemathesis'
                        echo "✓ Detected Python/pytest tests"
                    }
                    else if (fileExists('requirements.txt')) {
                        env.TEST_TYPE = 'python'
                        env.TEST_FRAMEWORK = 'pytest'
                        echo "✓ Detected Python tests (root requirements.txt)"
                    }
                    else {
                        error "❌ Could not detect test type (no pom.xml or tests/ directory found)"
                    }
                    
                    echo "Test Framework: ${env.TEST_FRAMEWORK}"
                }
            }
        }
        
        stage('Setup Python Environment') {
            when {
                expression { env.TEST_TYPE == 'python' }
            }
            steps {
                echo "📦 Setting up Python environment..."
                sh '''
                    python3 --version
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    
                    # Install from tests/requirements.txt or requirements.txt
                    if [ -f tests/requirements.txt ]; then
                        pip install -r tests/requirements.txt
                    elif [ -f requirements.txt ]; then
                        pip install -r requirements.txt
                    fi
                    
                    # Install pytest plugins for reporting
                    pip install pytest-html pytest-json-report
                    
                    echo "✓ Python environment ready"
                '''
            }
        }
        
        stage('Run Python Tests') {
            when {
                expression { env.TEST_TYPE == 'python' }
            }
            steps {
                echo "🧪 Running Python tests..."
                sh '''
                    . venv/bin/activate
                    
                    # Change to tests directory if it exists
                    if [ -d tests ]; then
                        cd tests
                    fi
                    
                    # Run pytest with reporting
                    pytest -v \
                        --junitxml=test-results.xml \
                        --html=report.html \
                        --self-contained-html \
                        --json-report \
                        --json-report-file=report.json \
                        || true
                    
                    # Move reports to workspace root if we're in tests/
                    if [ -d ../tests ]; then
                        mv test-results.xml report.html report.json .. 2>/dev/null || true
                    fi
                '''
            }
        }
        
        stage('Setup Java Environment') {
            when {
                expression { env.TEST_TYPE == 'java' }
            }
            steps {
                echo "📦 Setting up Java environment..."
                sh '''
                    java -version
                    mvn -version
                    echo "✓ Java environment ready"
                '''
            }
        }
        
        stage('Run Java Tests') {
            when {
                expression { env.TEST_TYPE == 'java' }
            }
            steps {
                echo "🧪 Running Java tests..."
                sh '''
                    # Run Maven tests (continue even if some tests fail)
                    mvn clean test -Dmaven.test.failure.ignore=true
                    
                    echo "✓ Java tests completed"
                '''
            }
        }
        
        stage('Publish Test Results') {
            steps {
                script {
                    echo "📊 Publishing test results..."
                    
                    try {
                        if (env.TEST_TYPE == 'python') {
                            // Publish JUnit results
                            junit 'test-results.xml'
                            
                            // Publish HTML report
                            publishHTML([
                                reportDir: '.',
                                reportFiles: 'report.html',
                                reportName: 'Test Report',
                                keepAll: true,
                                alwaysLinkToLastBuild: true
                            ])
                            
                            echo "✓ Python test results published"
                        } 
                        else if (env.TEST_TYPE == 'java') {
                            // Publish JUnit results
                            junit 'target/surefire-reports/*.xml'
                            
                            echo "✓ Java test results published"
                        }
                    } catch (Exception e) {
                        echo "⚠ Warning: Could not publish all reports: ${e.message}"
                    }
                }
            }
        }
        
        stage('Generate Summary') {
            steps {
                script {
                    echo "📋 Generating test summary..."
                    
                    def testResults = currentBuild.result ?: 'SUCCESS'
                    def status = testResults == 'SUCCESS' ? '✅' : '❌'
                    
                    // Get test counts from JUnit results
                    def summary = junit testResults: '**/test-results.xml, **/surefire-reports/*.xml', allowEmptyResults: true
                    
                    def passCount = summary?.passCount ?: 0
                    def failCount = summary?.failCount ?: 0
                    def skipCount = summary?.skipCount ?: 0
                    def totalCount = passCount + failCount + skipCount
                    
                    env.TEST_SUMMARY = """
${status} Test Execution Complete

Epic: ${env.EPIC_KEY}
Framework: ${env.TEST_FRAMEWORK}
Status: ${testResults}

Test Results:
✓ Passed: ${passCount}
✗ Failed: ${failCount}
⊘ Skipped: ${skipCount}
Total: ${totalCount}

Build: ${env.BUILD_URL}
Branch: ${env.BRANCH_NAME}
Duration: ${currentBuild.durationString}
"""
                    
                    echo env.TEST_SUMMARY
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "🧹 Cleaning up workspace..."
            }
            // Archive test reports
            archiveArtifacts artifacts: '**/test-results.xml, **/report.html, **/report.json, **/surefire-reports/*.xml', allowEmptyArchive: true
        }
        
        success {
            script {
                echo "================================"
                echo "✅ BUILD SUCCESSFUL"
                echo "================================"
                echo "${env.TEST_SUMMARY}"
                
                // TODO: Uncomment to post to Jira
                // postToJira(env.EPIC_KEY, env.TEST_SUMMARY, 'SUCCESS')
            }
        }
        
        failure {
            script {
                echo "================================"
                echo "❌ BUILD FAILED"
                echo "================================"
                echo "${env.TEST_SUMMARY}"
                
                // TODO: Uncomment to post to Jira
                // postToJira(env.EPIC_KEY, env.TEST_SUMMARY, 'FAILURE')
            }
        }
        
        unstable {
            script {
                echo "================================"
                echo "⚠ BUILD UNSTABLE (Some tests failed)"
                echo "================================"
                echo "${env.TEST_SUMMARY}"
                
                // TODO: Uncomment to post to Jira
                // postToJira(env.EPIC_KEY, env.TEST_SUMMARY, 'UNSTABLE')
            }
        }
    }
}

// Helper function to post results to Jira (optional)
// Uncomment and configure credentials to enable
/*
def postToJira(epicKey, summary, status) {
    withCredentials([usernamePassword(
        credentialsId: 'jira-credentials',
        usernameVariable: 'JIRA_USER',
        passwordVariable: 'JIRA_TOKEN'
    )]) {
        def jiraUrl = "https://your-domain.atlassian.net"
        def escapedSummary = summary.replaceAll('"', '\\\\"').replaceAll('\n', '\\\\n')
        
        sh """
            curl -X POST \
              -u "\${JIRA_USER}:\${JIRA_TOKEN}" \
              -H "Content-Type: application/json" \
              -d '{"body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "${escapedSummary}"}]}]}}' \
              "${jiraUrl}/rest/api/3/issue/${epicKey}/comment"
        """
        
        echo "✓ Posted results to Jira Epic: ${epicKey}"
    }
}
*/

