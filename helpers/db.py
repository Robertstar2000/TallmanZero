import os
import sqlite3
import threading
from typing import Any, List, Optional, Callable
from abc import ABC, abstractmethod
from urllib.parse import urlparse

class DatabaseProxy(ABC):
    """Abstract database proxy for dialect-agnostic persistence."""
    
    @abstractmethod
    def query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        pass
    
    @abstractmethod
    def run(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        pass
    
    @abstractmethod
    def get(self, sql: str, params: Optional[List[Any]] = None) -> Optional[dict]:
        pass
    
    @abstractmethod
    def all(self, sql: str, params: Optional[List[Any]] = None) -> List[dict]:
        pass
    
    @abstractmethod
    def transaction(self, fn: Callable) -> Any:
        pass

def parse_database_url(url: str) -> dict:
    """
    Parse a fully-formed DATABASE_URL into connection components.
    Supports:
      - postgresql://user:password@host:port/database
      - postgres://user:password@host:port/database
      - sqlite:///path/to/database.db
      - sqlite:///:memory:
    """
    parsed = urlparse(url)
    
    if parsed.scheme in ('postgresql', 'postgres'):
        return {
            'type': 'postgres',
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/') if parsed.path else 'postgres',
            'user': parsed.username or 'postgres',
            'password': parsed.password or ''
        }
    elif parsed.scheme == 'sqlite':
        # sqlite:///path/to/db or sqlite:///:memory:
        db_path = parsed.path
        if db_path.startswith('//'):
            db_path = db_path[2:]  # Remove leading //
        elif db_path.startswith('/'):
            db_path = db_path[1:]  # Remove leading /
        return {
            'type': 'sqlite',
            'path': db_path or 'tmp/data.db'
        }
    else:
        raise ValueError(f"Unsupported database URL scheme: {parsed.scheme}")

# Dialect Detection - supports both legacy env vars and DATABASE_URL
def get_database_config() -> dict:
    """
    Get database configuration from environment.
    Priority:
      1. DATABASE_URL (fully-formed URL for Swarm/cloud deployment)
      2. POSTGRES_HOST + individual vars (legacy)
      3. SQLite fallback for local development
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        return parse_database_url(database_url)
    
    # Legacy PostgreSQL env vars
    postgres_host = os.environ.get('POSTGRES_HOST')
    if postgres_host:
        return {
            'type': 'postgres',
            'host': postgres_host,
            'port': int(os.environ.get('POSTGRES_PORT', 5432)),
            'database': os.environ.get('POSTGRES_DB', 'agentzero'),
            'user': os.environ.get('POSTGRES_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_PASSWORD', '')
        }
    
    # SQLite fallback
    return {
        'type': 'sqlite',
        'path': os.environ.get('SQLITE_PATH', 'tmp/data.db')
    }

def translate_params(sql: str) -> str:
    """Convert ? placeholders to $1, $2, etc. for PostgreSQL."""
    index = 0
    result = []
    for char in sql:
        if char == '?':
            index += 1
            result.append(f'${index}')
        else:
            result.append(char)
    return ''.join(result)

class SQLiteProxy(DatabaseProxy):
    """SQLite implementation for local development."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SQLiteProxy, cls).__new__(cls)
            return cls._instance

    def __init__(self, db_path: str = 'tmp/data.db'):
        if hasattr(self, 'initialized') and self.initialized:
            return
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if db_path != ':memory:' else None
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.initialized = True
    
    def query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        self.conn.commit()
        return cursor
        
    def run(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        return self.query(sql, params)
    
    def get(self, sql: str, params: Optional[List[Any]] = None) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def all(self, sql: str, params: Optional[List[Any]] = None) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        return [dict(row) for row in cursor.fetchall()]
        
    def transaction(self, fn: Callable) -> Any:
        try:
            result = fn(self)
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            raise e

class PostgresProxy(DatabaseProxy):
    """PostgreSQL implementation for production/Swarm deployment."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PostgresProxy, cls).__new__(cls)
            return cls._instance
    
    def __init__(self, config: dict = None):
        if hasattr(self, 'initialized') and self.initialized:
            return
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        if config is None:
            config = get_database_config()
        
        # Build connection URL for logging (without password)
        connection_info = f"postgres://{config['user']}@{config['host']}:{config['port']}/{config['database']}"
        print(f"[DB] Connecting to PostgreSQL: {connection_info}")
        
        self.conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        self.conn.autocommit = True
        self.initialized = True
    
    def query(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        sql = translate_params(sql)
        cursor = self.conn.cursor()
        cursor.execute(sql, params or [])
        return cursor

    def run(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        return self.query(sql, params)
    
    def get(self, sql: str, params: Optional[List[Any]] = None) -> Optional[dict]:
        import psycopg2.extras
        sql = translate_params(sql)
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        return dict(row) if row else None
        
    def all(self, sql: str, params: Optional[List[Any]] = None) -> List[dict]:
        import psycopg2.extras
        sql = translate_params(sql)
        cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql, params or [])
        return [dict(row) for row in cursor.fetchall()]

    def transaction(self, fn: Callable) -> Any:
        old_autocommit = self.conn.autocommit
        try:
            self.conn.autocommit = False
            result = fn(self)
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            self.conn.autocommit = old_autocommit

# Singleton database instance
_db_instance: Optional[DatabaseProxy] = None
_db_lock = threading.Lock()

def get_database() -> DatabaseProxy:
    """Get the appropriate database proxy based on environment."""
    global _db_instance
    
    with _db_lock:
        if _db_instance is not None:
            return _db_instance
        
        config = get_database_config()
        
        if config['type'] == 'postgres':
            _db_instance = PostgresProxy(config)
        else:
            _db_instance = SQLiteProxy(config.get('path', 'tmp/data.db'))
        
        return _db_instance

def init_db():
    """Initialize database schema."""
    config = get_database_config()
    db = get_database()
    
    if config['type'] == 'postgres':
        # PostgreSQL schema
        db.run("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[DB] PostgreSQL schema initialized")
    else:
        # SQLite schema
        db.run("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[DB] SQLite schema initialized")

if __name__ == "__main__":
    init_db()

