"""Database initialisation script for ChronoCare AI.

Usage:
    python scripts/init_db.py
"""
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

from app.db.database import init_db

if __name__ == "__main__":
    init_db()
    print("Database tables created successfully.")
