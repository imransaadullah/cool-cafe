"""
Unit tests for authentication utilities
"""

import pytest
from shared.utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)


class TestPasswordHashing:
    """Test password hashing functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_password(self):
        """Test password verification."""
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test wrong password verification."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        assert verify_password(wrong_password, hashed) is False


class TestJWT:
    """Test JWT token functions."""
    
    def test_create_token(self):
        """Test token creation."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        assert token is not None
        assert len(token) > 0
    
    def test_decode_token(self):
        """Test token decoding."""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "testuser"
        assert decoded["role"] == "admin"
    
    def test_decode_invalid_token(self):
        """Test decoding invalid token."""
        invalid_token = "invalid.token.here"
        decoded = decode_access_token(invalid_token)
        assert decoded is None
