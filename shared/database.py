from prisma import Prisma
from typing import Optional
import os


class Database:
    """Database client using Prisma."""
    
    def __init__(self):
        self.client: Optional[Prisma] = None
    
    async def connect(self):
        """Connect to the database."""
        self.client = Prisma()
        await self.client.connect()
    
    async def disconnect(self):
        """Disconnect from the database."""
        if self.client:
            await self.client.disconnect()
    
    def get_client(self) -> Prisma:
        """Get the Prisma client."""
        if self.client is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.client


db = Database()


def get_db():
    """Dependency for FastAPI routes."""
    client = db.get_client()
    try:
        yield client
    finally:
        pass  # Connection stays open for the app lifecycle
