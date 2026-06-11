#!/usr/bin/env python3
"""
Create initial admin user
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from prisma import Prisma
from shared.utils.auth import get_password_hash


async def main():
    print("Creating initial admin user...")
    
    # Connect to database
    client = Prisma()
    await client.connect()
    
    # Check if admin exists
    existing = await client.admin.find_unique(where={"username": "admin"})
    if existing:
        print("Admin user already exists.")
        await client.disconnect()
        return
    
    # Create admin
    password = "admin123"  # Default password - should be changed
    admin = await client.admin.create(
        data={
            "username": "admin",
            "email": "admin@cybercafe.com",
            "fullName": "System Administrator",
            "role": "global_admin",
            "passwordHash": get_password_hash(password),
        }
    )
    
    print(f"Admin user created successfully!")
    print(f"  Username: admin")
    print(f"  Password: {password}")
    print(f"\nPlease change the default password after first login.")
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
