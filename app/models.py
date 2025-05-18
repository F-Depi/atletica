from sqlalchemy import create_engine
import json
from config import DB_CONFIG

def get_db_engine():
    """Create and return SQLAlchemy engine for database connection"""
    return create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}")
