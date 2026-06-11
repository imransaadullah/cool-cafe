"""
Test fixtures for pytest
"""

import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def client():
    """Create a test client."""
    from local_server.app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def global_client():
    """Create a global server test client."""
    from global_server.app.main import app
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database for unit tests."""
    class MockDB:
        def __init__(self):
            self.admins = []
            self.pcs = []
            self.sessions = []
            self.codes = []
        
        def admin(self):
            return self
        
        def find_unique(self, where):
            return None
        
        def find_many(self, where=None, order=None, take=None):
            return []
        
        def create(self, data):
            return type('obj', (object,), data)()
        
        def update(self, where, data):
            return type('obj', (object,), {**where, **data})()
        
        def delete(self, where):
            return True
        
        def count(self, where=None):
            return 0
    
    return MockDB()


@pytest.fixture
def sample_pc_data():
    """Sample PC data for testing."""
    return {
        "name": "Test PC",
        "pc_number": 1,
        "branch_id": 1,
        "ip_address": "192.168.1.100",
        "mac_address": "AA:BB:CC:DD:EE:FF",
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing."""
    return {
        "pc_id": 1,
        "branch_id": 1,
        "duration_minutes": 60,
    }


@pytest.fixture
def sample_code_data():
    """Sample code data for testing."""
    return {
        "branch_id": 1,
        "duration_minutes": 60,
        "count": 10,
        "value_per_code": 100,
    }


@pytest.fixture
def sample_admin_data():
    """Sample admin data for testing."""
    return {
        "username": "testadmin",
        "email": "test@example.com",
        "full_name": "Test Admin",
        "password": "testpassword123",
        "role": "branch_admin",
        "branch_id": 1,
    }
