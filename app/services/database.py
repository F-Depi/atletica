from sqlalchemy import create_engine
from config import DB_CONFIG

def get_db_engine():
    """Create and return a SQLAlchemy engine for PostgreSQL"""
    return create_engine(f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}")
