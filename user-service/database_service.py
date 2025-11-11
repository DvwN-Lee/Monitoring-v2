# user-service/database_service.py (Hybrid: SQLite + PostgreSQL)
import asyncio
import os
import logging
from typing import Optional, Dict

from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

# Determine which DB to use based on environment variable
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() == 'true'

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("🐘 Using PostgreSQL database")
else:
    import sqlite3
    logger.info("💾 Using SQLite database")


class UserServiceDatabase:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.use_postgres = USE_POSTGRES

        if self.use_postgres:
            # PostgreSQL connection parameters
            self.db_config = {
                'host': os.getenv('POSTGRES_HOST', 'postgresql-service'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'database': os.getenv('POSTGRES_DB', 'titanium'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', ''),
            }
            self._connection = None
        else:
            # SQLite configuration
            self.db_file = os.getenv('DATABASE_PATH', '/data/users.db')

        self._initialize_db()

    def _get_connection(self):
        """Get or create database connection."""
        if self.use_postgres:
            try:
                if self._connection is None or self._connection.closed:
                    self._connection = psycopg2.connect(**self.db_config)
                    logger.info(f"Connected to PostgreSQL at {self.db_config['host']}:{self.db_config['port']}")
                return self._connection
            except psycopg2.Error as e:
                logger.error(f"PostgreSQL connection failed: {e}", exc_info=True)
                raise
        else:
            # SQLite - return new connection each time
            return sqlite3.connect(self.db_file)

    def _initialize_db(self):
        """Initialize database schema."""
        try:
            if self.use_postgres:
                conn = self._get_connection()
                with conn.cursor() as cursor:
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(100) UNIQUE NOT NULL,
                            email VARCHAR(255) NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
                    ''')
                    conn.commit()
                logger.info("PostgreSQL user database initialized successfully")
            else:
                os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
                with sqlite3.connect(self.db_file) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            email TEXT NOT NULL,
                            password_hash TEXT NOT NULL
                        )
                    ''')
                    conn.commit()
                logger.info("SQLite user database initialized successfully")
        except Exception as e:
            logger.error(f"User DB initialization failed: {e}", exc_info=True)
            raise

    async def add_user(self, username: str, email: str, password: str) -> Optional[int]:
        """Add a new user with hashed password."""
        password_hash = generate_password_hash(password, method='pbkdf2:sha256:100000')
        async with self.lock:
            try:
                if self.use_postgres:
                    conn = self._get_connection()
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
                            (username, email, password_hash)
                        )
                        user_id = cursor.fetchone()[0]
                        conn.commit()
                        logger.info(f"User '{username}' added with ID {user_id}")
                        return user_id
                else:
                    with sqlite3.connect(self.db_file) as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                            (username, email, password_hash)
                        )
                        return cursor.lastrowid
            except (psycopg2.IntegrityError if self.use_postgres else sqlite3.IntegrityError):
                if self.use_postgres:
                    conn.rollback()
                logger.warning(f"User '{username}' already exists")
                return None
            except Exception as e:
                if self.use_postgres:
                    conn.rollback()
                logger.error(f"Error adding user: {e}", exc_info=True)
                return None

    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user information by username."""
        async with self.lock:
            try:
                if self.use_postgres:
                    conn = self._get_connection()
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(
                            "SELECT id, username, email, password_hash, created_at FROM users WHERE username = %s",
                            (username,)
                        )
                        user = cursor.fetchone()
                        return dict(user) if user else None
                else:
                    with sqlite3.connect(self.db_file) as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT * FROM users WHERE username = ?",
                            (username,)
                        )
                        user = cursor.fetchone()
                        return dict(user) if user else None
            except Exception as e:
                logger.error(f"Error getting user by username: {e}", exc_info=True)
                return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user information by ID."""
        async with self.lock:
            try:
                if self.use_postgres:
                    conn = self._get_connection()
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(
                            "SELECT id, username, email, password_hash, created_at FROM users WHERE id = %s",
                            (user_id,)
                        )
                        user = cursor.fetchone()
                        return dict(user) if user else None
                else:
                    with sqlite3.connect(self.db_file) as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute(
                            "SELECT * FROM users WHERE id = ?",
                            (user_id,)
                        )
                        user = cursor.fetchone()
                        return dict(user) if user else None
            except Exception as e:
                logger.error(f"Error getting user by ID: {e}", exc_info=True)
                return None

    async def verify_user_credentials(self, username: str, password: str) -> Optional[Dict]:
        """Verify user credentials."""
        user = await self.get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            # Return user info without password_hash
            return {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            }
        return None

    async def health_check(self) -> bool:
        """Check database connection health."""
        async with self.lock:
            try:
                if self.use_postgres:
                    conn = self._get_connection()
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                else:
                    with sqlite3.connect(self.db_file) as conn:
                        conn.execute("SELECT 1")
                return True
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                return False

    def close(self):
        """Close database connection."""
        if self.use_postgres and self._connection and not self._connection.closed:
            self._connection.close()
            logger.info("PostgreSQL connection closed")
