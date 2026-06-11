"""
Integration tests for API endpoints
"""

import pytest


class TestHealthEndpoint:
    """Test health endpoint."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/auth/login",
            params={"username": "invalid", "password": "invalid"},
        )
        assert response.status_code == 401
    
    def test_create_admin(self, client):
        """Test creating an admin."""
        admin_data = {
            "username": "testadmin",
            "email": "test@example.com",
            "full_name": "Test Admin",
            "password": "testpassword123",
            "role": "branch_admin",
        }
        response = client.post("/api/auth/create", json=admin_data)
        # May return 400 if user exists, which is also valid
        assert response.status_code in [200, 400]


class TestPCEndpoints:
    """Test PC management endpoints."""
    
    def test_get_pcs(self, client):
        """Test getting list of PCs."""
        response = client.get("/api/pcs/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_pc(self, client):
        """Test creating a PC."""
        pc_data = {
            "name": "Test PC",
            "pc_number": 99,
            "branch_id": 1,
            "ip_address": "192.168.1.200",
        }
        response = client.post("/api/pcs/", json=pc_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test PC"


class TestSessionEndpoints:
    """Test session management endpoints."""
    
    def test_get_sessions(self, client):
        """Test getting list of sessions."""
        response = client.get("/api/sessions/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestCodeEndpoints:
    """Test code management endpoints."""
    
    def test_get_batches(self, client):
        """Test getting code batches."""
        response = client.get("/api/codes/batches")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_batch(self, client):
        """Test creating a code batch."""
        batch_data = {
            "branch_id": 1,
            "duration_minutes": 60,
            "count": 5,
            "value_per_code": 100,
        }
        response = client.post("/api/codes/batches", json=batch_data)
        assert response.status_code == 200


class TestDashboardEndpoints:
    """Test dashboard endpoints."""
    
    def test_get_overview(self, client):
        """Test getting dashboard overview."""
        response = client.get("/api/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_pcs" in data
        assert "online_pcs" in data
        assert "active_sessions" in data
