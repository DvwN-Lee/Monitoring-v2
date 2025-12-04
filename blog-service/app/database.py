# blog-service/app/database.py
import os
import logging
from typing import Optional, Dict, List
from app.config import USE_POSTGRES, DB_CONFIG, DATABASE_PATH

logger = logging.getLogger(__name__)

if USE_POSTGRES:
    import asyncpg
    logger.info("🐘 Using PostgreSQL database with asyncpg")
else:
    import aiosqlite
    logger.info("💾 Using SQLite database")


class BlogDatabase:
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connection pool and schema."""
        if self._initialized:
            return

        if self.use_postgres:
            try:
                self.pool = await asyncpg.create_pool(
                    min_size=5,
                    max_size=20,
                    **DB_CONFIG
                )
                logger.info(f"PostgreSQL connection pool created: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
                await self._initialize_postgres_schema()
            except Exception as e:
                logger.error(f"PostgreSQL pool creation failed: {e}", exc_info=True)
                raise
        else:
            await self._initialize_sqlite_schema()

        self._initialized = True

    async def _initialize_postgres_schema(self):
        """Initialize PostgreSQL database schema."""
        async with self.pool.acquire() as conn:
            # Create categories table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    slug VARCHAR(50) NOT NULL UNIQUE
                )
            ''')

            # Insert default categories if not exist
            count = await conn.fetchval("SELECT COUNT(*) FROM categories")
            if count == 0:
                await conn.execute('''
                    INSERT INTO categories (id, name, slug) VALUES
                    (1, '기술 스택', 'tech-stack'),
                    (2, 'Troubleshooting', 'troubleshooting'),
                    (3, 'Test', 'test')
                ''')

            # Create posts table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    content TEXT NOT NULL,
                    author VARCHAR(100) NOT NULL,
                    category_id INTEGER NOT NULL REFERENCES categories(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id)')

        logger.info("PostgreSQL blog database schema initialized")

    async def _initialize_sqlite_schema(self):
        """Initialize SQLite database schema."""
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        async with aiosqlite.connect(DATABASE_PATH) as conn:
            # Create categories table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    slug TEXT NOT NULL UNIQUE
                )
            ''')

            # Insert default categories if not exist
            cursor = await conn.execute("SELECT COUNT(*) FROM categories")
            count = await cursor.fetchone()
            if count[0] == 0:
                await conn.execute('''
                    INSERT INTO categories (id, name, slug) VALUES
                    (1, '기술 스택', 'tech-stack'),
                    (2, 'Troubleshooting', 'troubleshooting'),
                    (3, 'Test', 'test')
                ''')

            # Create posts table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                )
            ''')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id)')
            await conn.commit()

        logger.info("SQLite blog database schema initialized")

    async def validate_category_id(self, category_id: int) -> bool:
        """Validate that category_id exists."""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT id FROM categories WHERE id = $1", category_id)
                return result is not None
        else:
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
                result = await cursor.fetchone()
                return result is not None

    async def get_posts(self, offset: int, limit: int, category_slug: Optional[str] = None) -> List[Dict]:
        """Fetch paginated posts with category info, ordered by id DESC."""
        base_query = """
            SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, p.category_id,
                   c.name as category_name, c.slug as category_slug
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
        """

        if self.use_postgres:
            if category_slug:
                query = base_query + " WHERE c.slug = $1 ORDER BY p.id DESC LIMIT $2 OFFSET $3"
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, category_slug, limit, offset)
                    return [dict(row) for row in rows]
            else:
                query = base_query + " ORDER BY p.id DESC LIMIT $1 OFFSET $2"
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch(query, limit, offset)
                    return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                if category_slug:
                    query = base_query + " WHERE c.slug = ? ORDER BY p.id DESC LIMIT ? OFFSET ?"
                    cursor = await conn.execute(query, (category_slug, limit, offset))
                else:
                    query = base_query + " ORDER BY p.id DESC LIMIT ? OFFSET ?"
                    cursor = await conn.execute(query, (limit, offset))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_post_by_id(self, post_id: int) -> Optional[Dict]:
        """Fetch single post by ID with category info."""
        query = """
            SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, p.category_id,
                   c.name as category_name, c.slug as category_slug
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = """

        if self.use_postgres:
            query += "$1"
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, post_id)
                return dict(row) if row else None
        else:
            query += "?"
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query, (post_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_categories_with_counts(self) -> List[Dict]:
        """Fetch all categories with post counts."""
        query = """
            SELECT c.id, c.name, c.slug, COUNT(p.id) as post_count
            FROM categories c
            LEFT JOIN posts p ON c.id = p.category_id
            GROUP BY c.id, c.name, c.slug
            ORDER BY c.id
        """

        if self.use_postgres:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [dict(row) for row in rows]
        else:
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def close(self):
        """Close database connection pool."""
        if self.use_postgres and self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")


# Singleton instance
db = BlogDatabase()
