from fastapi import FastAPI
from .routes import auth, pcs, sessions, codes, dashboard, filter_rules

__all__ = ["app"]
