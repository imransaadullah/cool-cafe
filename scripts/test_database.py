#!/usr/bin/env python3
"""
Test database connection and admin user
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from prisma import Prisma
from shared.utils.auth import verify_password, get_password_hash


def main():
    print("Testing database connection...\n")
    
    # Connect to database
    client = Prisma()
    
    try:
        client.connect()
        print("✓ Database connected\n")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nPlease check:")
        print("1. PostgreSQL is running on port 5432")
        print("2. Database 'cybercafe' exists")
        print("3. .env has correct DATABASE_URL")
        return 1
    
    # Check for admin user
    print("Checking for admin user...")
    admin = client.admin.find_unique(where={"username": "admin"})
    
    if admin:
        print(f"✓ Admin user found (ID: {admin.id})")
        print(f"  Username: {admin.username}")
        print(f"  Role: {admin.role}")
        print(f"  Active: {admin.isActive}")
        
        # Test password verification
        print("\nTesting password verification...")
        test_password = "admin123"
        if verify_password(test_password, admin.passwordHash):
            print(f"✓ Password '{test_password}' is correct")
        else:
            print(f"✗ Password '{test_password}' is incorrect")
    else:
        print("✗ Admin user not found")
        print("\nCreating admin user...")
        
        from shared.utils.auth import get_password_hash
        
        admin = client.admin.create(
            data={
                "username": "admin",
                "email": "admin@cybercafe.com",
                "fullName": "System Administrator",
                "role": "global_admin",
                "passwordHash": get_password_hash("admin123"),
            }
        )
        print(f"✓ Admin user created (ID: {admin.id})")
        print(f"  Username: admin")
        print(f"  Password: admin123")
    
    # List all admins
    print("\nAll admin users:")
    admins = client.admin.find_many()
    for a in admins:
        print(f"  - {a.username} (ID: {a.id}, Role: {a.role})")
    
    client.disconnect()
    print("\n✓ Test complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
