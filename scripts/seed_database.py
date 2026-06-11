#!/usr/bin/env python3
"""
Database seeding script
Creates initial data for development and testing
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import string

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from prisma import Prisma
from shared.utils.auth import get_password_hash


def generate_code(length: int = 8) -> str:
    """Generate a random alphanumeric code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


async def seed_database():
    """Seed the database with initial data."""
    print("Seeding database...")
    
    client = Prisma()
    await client.connect()
    
    # Create branches
    branches = [
        {"name": "Main Branch", "address": "123 Main Street", "phone": "+234 801 234 5678"},
        {"name": "Branch B", "address": "456 Second Avenue", "phone": "+234 802 345 6789"},
        {"name": "Branch C", "address": "789 Third Road", "phone": "+234 803 456 7890"},
    ]
    
    created_branches = []
    for branch_data in branches:
        existing = await client.branch.find_first(where={"name": branch_data["name"]})
        if not existing:
            branch = await client.branch.create(data=branch_data)
            created_branches.append(branch)
            print(f"  Created branch: {branch.name}")
        else:
            created_branches.append(existing)
            print(f"  Branch already exists: {existing.name}")
    
    # Create admins
    admins = [
        {
            "username": "admin",
            "email": "admin@cybercafe.com",
            "fullName": "System Administrator",
            "role": "global_admin",
            "password": "admin123",
        },
        {
            "username": "manager1",
            "email": "manager1@cybercafe.com",
            "fullName": "Branch Manager 1",
            "role": "branch_admin",
            "branchId": created_branches[0].id,
            "password": "manager123",
        },
    ]
    
    for admin_data in admins:
        existing = await client.admin.find_unique(where={"username": admin_data["username"]})
        if not existing:
            password = admin_data.pop("password")
            admin = await client.admin.create(
                data={
                    **admin_data,
                    "passwordHash": get_password_hash(password),
                }
            )
            print(f"  Created admin: {admin.username}")
        else:
            print(f"  Admin already exists: {existing.username}")
    
    # Create PCs for first branch
    branch = created_branches[0]
    for i in range(1, 11):
        existing = await client.pc.find_first(
            where={"pcNumber": i, "branchId": branch.id}
        )
        if not existing:
            pc = await client.pc.create(
                data={
                    "name": f"PC-{i:02d}",
                    "pcNumber": i,
                    "branchId": branch.id,
                    "ipAddress": f"192.168.1.{100 + i}",
                }
            )
            print(f"  Created PC: {pc.name}")
    
    # Create code batches
    for duration in [30, 60, 90]:
        existing = await client.codebatch.find_first(
            where={
                "branchId": branch.id,
                "durationMinutes": duration,
            }
        )
        if not existing:
            batch = await client.codebatch.create(
                data={
                    "branchId": branch.id,
                    "count": 50,
                    "durationMinutes": duration,
                    "valuePerCode": duration * 2,  # Simple pricing
                    "batchName": f"{duration} min batch",
                }
            )
            
            # Create codes for batch
            for _ in range(50):
                code_value = generate_code()
                while await client.code.find_unique(where={"code": code_value}):
                    code_value = generate_code()
                
                await client.code.create(
                    data={
                        "code": code_value,
                        "durationMinutes": duration,
                        "batchId": batch.id,
                        "branchId": branch.id,
                        "value": duration * 2,
                    }
                )
            
            print(f"  Created code batch: {duration} mins (50 codes)")
    
    # Create filter rules
    filter_rules = [
        {"ruleType": "dns", "pattern": "*.facebook.com", "action": "block", "priority": 10},
        {"ruleType": "dns", "pattern": "*.twitter.com", "action": "block", "priority": 10},
        {"ruleType": "process", "pattern": "game.exe", "action": "block", "priority": 5},
        {"ruleType": "url", "pattern": "gambling", "action": "block", "priority": 8},
    ]
    
    for rule_data in filter_rules:
        existing = await client.filterrule.find_first(
            where={"pattern": rule_data["pattern"]}
        )
        if not existing:
            await client.filterrule.create(data=rule_data)
            print(f"  Created filter rule: {rule_data['pattern']}")
    
    await client.disconnect()
    print("\nDatabase seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_database())
