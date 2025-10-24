"""
Example pytest test file - shows expected LLM output format.
This file demonstrates the structure and style that the LLM should generate.
"""
import requests
import uuid
import pytest

BASE_URL = 'http://localhost:8000/v1'

def test_create_user_happy_path():
    """Test successful user creation."""
    unique = str(uuid.uuid4())[:8]
    payload = {
        "name": f"TestUser-{unique}",
        "email": f"test-{unique}@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/users", json=payload)
    
    assert response.status_code == 201
    body = response.json()
    assert body.get('id') is not None
    assert body.get('email') == payload['email']
    assert body.get('name') == payload['name']

def test_create_user_invalid_email():
    """Test user creation with invalid email format."""
    payload = {
        "name": "Test User",
        "email": "invalid-email"
    }
    
    response = requests.post(f"{BASE_URL}/users", json=payload)
    
    assert response.status_code == 400
    body = response.json()
    assert 'error' in body or 'message' in body

def test_get_user_not_found():
    """Test fetching non-existent user returns 404."""
    response = requests.get(f"{BASE_URL}/users/99999")
    
    assert response.status_code == 404

@pytest.mark.skipif(not BASE_URL.startswith('https'), reason="Auth tests require HTTPS")
def test_create_user_unauthorized():
    """Test user creation without authentication fails."""
    payload = {"name": "Test", "email": "test@example.com"}
    
    # Intentionally omit auth headers
    response = requests.post(f"{BASE_URL}/users", json=payload)
    
    assert response.status_code in [401, 403]


