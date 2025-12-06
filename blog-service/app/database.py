# blog-service/app/database.py
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime
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

    async def create_post(self, title: str, content: str, author: str, category_id: int) -> Dict:
        """Create a new post and return it with category info."""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    # Insert post
                    row = await conn.fetchrow(
                        "INSERT INTO posts (title, content, author, category_id) VALUES ($1, $2, $3, $4) RETURNING id, created_at, updated_at",
                        title, content, author, category_id
                    )
                    post_id = row["id"]
                    created_at = row["created_at"].isoformat() if row["created_at"] else None
                    updated_at = row["updated_at"].isoformat() if row["updated_at"] else None

                    # Get category info
                    cat = await conn.fetchrow("SELECT name, slug FROM categories WHERE id = $1", category_id)
                    category_name = cat["name"] if cat else None
                    category_slug = cat["slug"] if cat else None
        else:
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                conn.row_factory = aiosqlite.Row
                now = datetime.utcnow().isoformat()
                cursor = await conn.execute(
                    "INSERT INTO posts (title, content, author, category_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (title, content, author, category_id, now, now)
                )
                post_id = cursor.lastrowid
                created_at = now
                updated_at = now
                await conn.commit()

                # Get category info
                cursor = await conn.execute("SELECT name, slug FROM categories WHERE id = ?", (category_id,))
                cat = await cursor.fetchone()
                category_name = cat["name"] if cat else None
                category_slug = cat["slug"] if cat else None

        return {
            "id": post_id,
            "title": title,
            "content": content,
            "author": author,
            "created_at": created_at,
            "updated_at": updated_at,
            "category": {
                "id": category_id,
                "name": category_name,
                "slug": category_slug
            }
        }

    async def get_post_author(self, post_id: int) -> Optional[str]:
        """Get the author of a post for permission checking."""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                return await conn.fetchval("SELECT author FROM posts WHERE id = $1", post_id)
        else:
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.execute("SELECT author FROM posts WHERE id = ?", (post_id,))
                row = await cursor.fetchone()
                return row[0] if row else None

    async def update_post(self, post_id: int, title: Optional[str], content: Optional[str], category_id: Optional[int]) -> Optional[Dict]:
        """Update a post and return the updated post with category info."""
        fields = []
        params = []
        param_idx = 1

        if self.use_postgres:
            if title is not None:
                fields.append(f"title = ${param_idx}")
                params.append(title)
                param_idx += 1
            if content is not None:
                fields.append(f"content = ${param_idx}")
                params.append(content)
                param_idx += 1
            if category_id is not None:
                fields.append(f"category_id = ${param_idx}")
                params.append(category_id)
                param_idx += 1
            
            if not fields:
                return None

            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(post_id)
            
            query = f"UPDATE posts SET {', '.join(fields)} WHERE id = ${param_idx}"
            
            async with self.pool.acquire() as conn:
                await conn.execute(query, *params)
                return await self.get_post_by_id(post_id)
        else:
            if title is not None:
                fields.append("title = ?")
                params.append(title)
            if content is not None:
                fields.append("content = ?")
                params.append(content)
            if category_id is not None:
                fields.append("category_id = ?")
                params.append(category_id)
            
            if not fields:
                return None

            fields.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(post_id)
            
            query = f"UPDATE posts SET {', '.join(fields)} WHERE id = ?"
            
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                await conn.execute(query, tuple(params))
                await conn.commit()
                return await self.get_post_by_id(post_id)

    async def delete_post(self, post_id: int) -> bool:
        """Delete a post. Returns True if deleted, False if not found (though logic usually checks existence first)."""
        if self.use_postgres:
            async with self.pool.acquire() as conn:
                result = await conn.execute("DELETE FROM posts WHERE id = $1", post_id)
                return result != "DELETE 0"
        else:
            async with aiosqlite.connect(DATABASE_PATH) as conn:
                cursor = await conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
                await conn.commit()
                return cursor.rowcount > 0

    async def close(self):
        """Close database connection pool."""
        if self.use_postgres and self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")


# Singleton instance
db = BlogDatabase()
