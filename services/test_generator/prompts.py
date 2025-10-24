"""
LLM prompt templates for test generation.
Contains templates for different test frameworks (pytest, Java/Rest-Assured).
"""

PYTEST_PROMPT_TEMPLATE = '''
You are an expert Python test engineer. Produce comprehensive pytest tests based on the API specification and Jira Epic details below.

=== JIRA EPIC INFORMATION ===
ISSUE_KEY: {issue_key}
SUMMARY: {epic_summary}
DESCRIPTION: {epic_description}

=== API CONTRACT ===
{contract_details}

=== REQUIREMENTS ===
1. OUTPUT FORMAT:
   - Delimit files using markers exactly like:
     ---TESTFILE: <path>---
     <file contents>
     ---ENDTESTFILE---

2. TEST FRAMEWORK:
   - Use pytest with requests or httpx for HTTP calls
   - If OpenAPI spec is provided, create a Schemathesis-based test harness for property testing
   - Include fixtures for setup/teardown
   - Use parametrize for testing multiple scenarios

3. TEST COVERAGE:
   Generate tests for the following scenarios:
   - ✅ Happy path: successful requests with valid data
   - ❌ Validation errors: invalid inputs, missing required fields, wrong data types
   - 🔍 Not found: requests for non-existent resources (404)
   - 🔒 Authentication: unauthorized/forbidden requests (401/403) if auth is used
   - 🔄 Edge cases: empty lists, boundary values, concurrent operations
   - 📊 Response validation: schema validation, required fields, data types

4. TEST STRUCTURE:
   - Create separate test files for different API modules
   - Use meaningful test names: test_<endpoint>_<scenario>
   - Include docstrings explaining what each test does
   - Use unique identifiers (UUID) to avoid conflicts
   - Clean up test data when possible

5. ADDITIONAL FILES:
   - tests/conftest.py: pytest fixtures and configuration
   - tests/test_<module>.py: test files for each API module
   - tests/README.md: instructions on how to run tests
   - tests/requirements.txt: test dependencies (if not already present)

=== EXAMPLE OUTPUT FORMAT ===
---TESTFILE: tests/test_users.py---
import pytest
import requests
from uuid import uuid4

BASE_URL = "http://localhost:8000"

@pytest.fixture
def unique_email():
    return f"test-{{uuid4()}}@example.com"

def test_create_user_success(unique_email):
    \"\"\"Test successful user creation with valid data.\"\"\"
    response = requests.post(f"{{BASE_URL}}/users", json={{
        "email": unique_email,
        "name": "Test User"
    }})
    assert response.status_code == 201
    assert response.json()["email"] == unique_email
---ENDTESTFILE---

Now generate comprehensive tests for the API specified above.
'''

JAVA_PROMPT_TEMPLATE = '''
You are a senior Java test engineer. Produce comprehensive JUnit5 + Rest-Assured tests based on the API specification and Jira Epic details below.

=== JIRA EPIC INFORMATION ===
ISSUE_KEY: {issue_key}
SUMMARY: {epic_summary}
DESCRIPTION: {epic_description}

=== API CONTRACT ===
{contract_details}

=== REQUIREMENTS ===
1. OUTPUT FORMAT:
   - Delimit files using markers exactly like:
     ---TESTFILE: <path>---
     <file contents>
     ---ENDTESTFILE---

2. TEST FRAMEWORK:
   - Use JUnit5 (@Test, @BeforeAll, @AfterAll, @BeforeEach)
   - Use Rest-Assured for HTTP requests with proper assertions
   - Use Hamcrest matchers for assertions (equalTo, hasSize, etc.)
   - Include proper imports for all classes

3. TEST COVERAGE:
   Generate tests for the following scenarios:
   - ✅ Happy path: successful requests with valid data
   - ❌ Validation errors: invalid inputs, missing required fields, wrong data types
   - 🔍 Not found: requests for non-existent resources (404)
   - 🔒 Authentication: unauthorized/forbidden requests (401/403) if auth is used
   - 🔄 Edge cases: empty lists, boundary values
   - 📊 Response validation: schema validation, required fields, data types

4. TEST STRUCTURE:
   - Create separate test classes for different API modules
   - Use meaningful test names: test<Endpoint><Scenario>
   - Include JavaDoc comments explaining what each test does
   - Use @BeforeAll for base URL setup
   - Package: com.example.api.tests (or similar)

5. ADDITIONAL FILES:
   - src/test/java/com/example/api/tests/Test*.java: test classes
   - src/test/resources/config.properties: configuration (if needed)
   - pom.xml: Maven dependencies and build configuration
   - README.md: instructions on how to run tests

6. MAVEN DEPENDENCIES (pom.xml):
   Include dependencies for:
   - JUnit5 (junit-jupiter)
   - Rest-Assured (rest-assured)
   - Hamcrest (hamcrest-all)
   - JSON parsing (jackson-databind)

=== EXAMPLE OUTPUT FORMAT ===
---TESTFILE: src/test/java/com/example/api/tests/UserApiTest.java---
package com.example.api.tests;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import java.util.UUID;

import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

public class UserApiTest {{
    
    @BeforeAll
    public static void setup() {{
        RestAssured.baseURI = "http://localhost:8000";
    }}
    
    @Test
    public void testCreateUserSuccess() {{
        String email = "test-" + UUID.randomUUID() + "@example.com";
        
        given()
            .contentType(ContentType.JSON)
            .body("{{\"email\": \"" + email + "\", \"name\": \"Test User\"}}")
        .when()
            .post("/users")
        .then()
            .statusCode(201)
            .body("email", equalTo(email))
            .body("name", equalTo("Test User"));
    }}
}}
---ENDTESTFILE---

Now generate comprehensive Java/Rest-Assured tests for the API specified above.
'''


