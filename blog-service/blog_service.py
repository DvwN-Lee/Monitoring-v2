import os
import logging
from datetime import datetime
from typing import Optional, Dict, List
import aiohttp
from fastapi import FastAPI, Request, HTTPException, Form, Depends, Query, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

try:
    from prometheus_fastapi_instrumentator.metrics import request_latency
except ImportError:
    from prometheus_fastapi_instrumentator import metrics as _metrics

    def request_latency(*args, **kwargs):
        return _metrics.latency(*args, **kwargs)

# --- 기본 로깅 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BlogServiceApp')

app = FastAPI()

# Prometheus 메트릭 설정
# 히스토그램 버킷을 세밀하게 설정하여 정확한 P95/P99 계산 가능
from prometheus_client import Counter
from prometheus_fastapi_instrumentator.metrics import Info

REQUEST_LATENCY_BUCKETS = (
    0.001,
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    10.0,
)

# 커스텀 메트릭: http_requests_total_custom
# api-gateway와 동일한 형식의 status 레이블(2xx, 4xx, 5xx)을 사용
http_requests_total_custom = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ("method", "status"),
)

def http_requests_total_custom_metric(info: Info) -> None:
    status_code = info.response.status_code
    status_group = "unknown"
    if 200 <= status_code < 300:
        status_group = "2xx"
    elif 300 <= status_code < 400:
        status_group = "3xx"
    elif 400 <= status_code < 500:
        status_group = "4xx"
    elif 500 <= status_code < 600:
        status_group = "5xx"
    
    http_requests_total_custom.labels(info.method, status_group).inc()

def configure_metrics(application: FastAPI) -> None:
    """Configure Prometheus request latency metrics with backward-compatible buckets."""
    try:
        instrumentator = Instrumentator(buckets=REQUEST_LATENCY_BUCKETS)
    except TypeError as exc:
        if "buckets" not in str(exc):
            raise
        instrumentator = Instrumentator()
        instrumentator.add(
            request_latency(buckets=REQUEST_LATENCY_BUCKETS)
        )

    # 커스텀 메트릭 추가
    instrumentator.add(http_requests_total_custom_metric)
    instrumentator.instrument(application).expose(application)


configure_metrics(app)

# --- 정적 파일 및 템플릿 설정 ---
templates = Jinja2Templates(directory="templates")
app.mount("/blog/static", StaticFiles(directory="static"), name="static")

# --- 설정 ---
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth-service:8002')

# Determine which DB to use
USE_POSTGRES = os.getenv('USE_POSTGRES', 'false').lower() == 'true'

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    logger.info("🐘 Using PostgreSQL database for blog posts")

    DB_CONFIG = {
        'host': os.getenv('POSTGRES_HOST', 'postgresql-service'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'titanium'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', ''),
    }
else:
    import sqlite3
    logger.info("💾 Using SQLite database for blog posts")
    DATABASE_PATH = os.getenv('BLOG_DATABASE_PATH', '/app/blog.db')

# --- Database Helper Functions ---
def get_db_connection():
    """Get database connection."""
    if USE_POSTGRES:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL connection failed: {e}", exc_info=True)
            raise
    else:
        return sqlite3.connect(DATABASE_PATH)

def init_db():
    """Initialize database schema."""
    try:
        if USE_POSTGRES:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Create categories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categories (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(50) NOT NULL UNIQUE,
                        slug VARCHAR(50) NOT NULL UNIQUE
                    )
                ''')
                # Insert default categories if not exist
                cursor.execute("SELECT COUNT(*) FROM categories")
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                        INSERT INTO categories (id, name, slug) VALUES
                        (1, '기술 스택', 'tech-stack'),
                        (2, 'Troubleshooting', 'troubleshooting'),
                        (3, 'Test', 'test')
                    ''')

                # Create posts table
                cursor.execute('''
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
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC)
                ''')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id)
                ''')
                conn.commit()
            conn.close()
            logger.info("PostgreSQL blog database initialized successfully")
        else:
            os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                # Create categories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        slug TEXT NOT NULL UNIQUE
                    )
                ''')
                # Insert default categories if not exist
                cursor.execute("SELECT COUNT(*) FROM categories")
                if cursor.fetchone()[0] == 0:
                    cursor.execute('''
                        INSERT INTO categories (id, name, slug) VALUES
                        (1, '기술 스택', 'tech-stack'),
                        (2, 'Troubleshooting', 'troubleshooting'),
                        (3, 'Test', 'test')
                    ''')

                # Create posts table
                cursor.execute('''
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
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id)
                ''')
                conn.commit()
            logger.info("SQLite blog database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        raise

def row_to_post(row: Dict) -> Dict:
    """Convert database row to post dictionary."""
    if USE_POSTGRES:
        return {
            "id": row["id"],
            "title": row["title"],
            "content": row["content"],
            "author": row["author"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"]),
            "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], 'isoformat') else str(row["updated_at"]),
        }
    else:
        # SQLite row
        return {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "author": row[3],
            "created_at": row[4],
            "updated_at": row[5],
        }

init_db()

# --- Pydantic 모델 ---
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str

class PostCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    content: str = Field(..., min_length=1, max_length=20000)
    category_id: int = Field(..., gt=0)

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=120)
    content: Optional[str] = Field(None, min_length=1, max_length=20000)
    category_id: Optional[int] = Field(None, gt=0)

# --- 인증 유틸 ---
async def require_user(request: Request) -> str:
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Authorization header missing or invalid')
    token = auth_header.split(' ')[1]
    verify_url = f"{AUTH_SERVICE_URL}/verify"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(verify_url, headers={'Authorization': f'Bearer {token}'}) as resp:
                data = await resp.json()
                if resp.status != 200 or data.get('status') != 'success':
                    raise HTTPException(status_code=401, detail='Invalid or expired token')
                username = data.get('data', {}).get('username')
                if not username:
                    raise HTTPException(status_code=401, detail='Invalid token payload')
                return username
    except aiohttp.ClientError:
        raise HTTPException(status_code=502, detail='Auth service not reachable')

def validate_category_id(category_id: int) -> bool:
    """Validate that category_id exists in the database."""
    conn = get_db_connection()
    try:
        if USE_POSTGRES:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM categories WHERE id = %s", (category_id,))
                result = cursor.fetchone()
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
            result = cursor.fetchone()
        return result is not None
    finally:
        conn.close()

# --- API 핸들러 함수 ---
@app.get("/api/posts")
async def handle_get_posts(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None)
):
    """모든 블로그 게시물 목록을 반환합니다(최신순, 페이지네이션, 카테고리 필터링)."""
    conn = get_db_connection()
    try:
        # Build query based on category filter
        base_query = """
            SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, p.category_id,
                   c.name as category_name, c.slug as category_slug
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
        """
        where_clause = ""
        params = []

        if category:
            where_clause = " WHERE c.slug = "
            if USE_POSTGRES:
                where_clause += "%s"
                params.append(category)
            else:
                where_clause += "?"
                params.append(category)

        order_limit = " ORDER BY p.id DESC LIMIT "
        if USE_POSTGRES:
            order_limit += "%s OFFSET %s"
            params.extend([limit, offset])
        else:
            order_limit += "? OFFSET ?"
            params.extend([limit, offset])

        full_query = base_query + where_clause + order_limit

        if USE_POSTGRES:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(full_query, tuple(params))
                rows = cursor.fetchall()
                items = [dict(r) for r in rows]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(full_query, tuple(params))
            rows = cursor.fetchall()
            items = [dict(r) for r in rows]

        # 목록 응답은 요약 정보 위주로 반환 + 발췌(excerpt) + 카테고리 정보
        summaries = []
        for p in items:
            content = (p.get("content") or "").replace("\r", " ").replace("\n", " ")
            excerpt = content[:120] + ("..." if len(content) > 120 else "")
            summaries.append({
                "id": p["id"],
                "title": p["title"],
                "author": p["author"],
                "created_at": p["created_at"].isoformat() if hasattr(p["created_at"], 'isoformat') else str(p["created_at"]),
                "excerpt": excerpt,
                "category": {
                    "id": p["category_id"],
                    "name": p["category_name"],
                    "slug": p["category_slug"]
                }
            })
        return JSONResponse(content=summaries)
    finally:
        conn.close()

@app.get("/api/posts/{post_id}")
async def handle_get_post_by_id(post_id: int):
    """ID로 특정 게시물을 찾아 반환합니다."""
    conn = get_db_connection()
    try:
        query = """
            SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, p.category_id,
                   c.name as category_name, c.slug as category_slug
            FROM posts p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = """

        if USE_POSTGRES:
            query += "%s"
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (post_id,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail={'error': 'Post not found'})
                post_dict = dict(row)
        else:
            query += "?"
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, (post_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail={'error': 'Post not found'})
            post_dict = dict(row)

        # Format response with category info
        response = {
            "id": post_dict["id"],
            "title": post_dict["title"],
            "content": post_dict["content"],
            "author": post_dict["author"],
            "created_at": post_dict["created_at"].isoformat() if hasattr(post_dict["created_at"], 'isoformat') else str(post_dict["created_at"]),
            "updated_at": post_dict["updated_at"].isoformat() if hasattr(post_dict["updated_at"], 'isoformat') else str(post_dict["updated_at"]),
            "category": {
                "id": post_dict["category_id"],
                "name": post_dict["category_name"],
                "slug": post_dict["category_slug"]
            }
        }
        return JSONResponse(content=response)
    finally:
        conn.close()

@app.post("/api/login")
async def handle_login(user_login: UserLogin):
    """사용자 로그인을 처리합니다."""
    user = users_db.get(user_login.username)
    if user and user['password'] == user_login.password:
        return JSONResponse(content={'token': f'session-token-for-{user_login.username}'})
    raise HTTPException(status_code=401, detail={'error': 'Invalid credentials'})

@app.post("/api/register", status_code=201)
async def handle_register(user_register: UserRegister):
    """사용자 등록을 처리합니다."""
    if not user_register.username or not user_register.password:
        raise HTTPException(status_code=400, detail={'error': 'Username and password are required'})
    if user_register.username in users_db:
        raise HTTPException(status_code=409, detail={'error': 'Username already exists'})

    users_db[user_register.username] = {'password': user_register.password}
    logger.info(f"New user registered: {user_register.username}")
    return JSONResponse(content={'message': 'Registration successful'})

@app.post("/api/posts", status_code=201)
async def create_post(request: Request, payload: PostCreate, username: str = Depends(require_user)):
    # Validate category_id exists
    if not validate_category_id(payload.category_id):
        raise HTTPException(status_code=422, detail=f'Category with id {payload.category_id} does not exist')

    conn = get_db_connection()
    try:
        if USE_POSTGRES:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    "INSERT INTO posts (title, content, author, category_id) VALUES (%s, %s, %s, %s) RETURNING id, created_at, updated_at",
                    (payload.title, payload.content, username, payload.category_id)
                )
                result = cursor.fetchone()
                post_id = result["id"]
                created_at = result["created_at"].isoformat()
                updated_at = result["updated_at"].isoformat()
                conn.commit()

                # Get category info
                cursor.execute("SELECT name, slug FROM categories WHERE id = %s", (payload.category_id,))
                cat = cursor.fetchone()
                category_name = cat["name"] if cat else None
                category_slug = cat["slug"] if cat else None
        else:
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT INTO posts (title, content, author, category_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (payload.title, payload.content, username, payload.category_id, now, now)
            )
            post_id = cursor.lastrowid
            created_at = now
            updated_at = now
            conn.commit()

            # Get category info
            conn.row_factory = sqlite3.Row
            cursor.execute("SELECT name, slug FROM categories WHERE id = ?", (payload.category_id,))
            cat = cursor.fetchone()
            category_name = cat["name"] if cat else None
            category_slug = cat["slug"] if cat else None

        return JSONResponse(content={
            "id": post_id,
            "title": payload.title,
            "content": payload.content,
            "author": username,
            "created_at": created_at,
            "updated_at": updated_at,
            "category": {
                "id": payload.category_id,
                "name": category_name,
                "slug": category_slug
            }
        })
    finally:
        conn.close()

@app.patch("/api/posts/{post_id}")
async def update_post_partial(post_id: int, request: Request, payload: PostUpdate, username: str = Depends(require_user)):
    # Validate category_id if provided
    if payload.category_id is not None and not validate_category_id(payload.category_id):
        raise HTTPException(status_code=422, detail=f'Category with id {payload.category_id} does not exist')

    conn = get_db_connection()
    try:
        if USE_POSTGRES:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT author FROM posts WHERE id = %s", (post_id,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail={'error': 'Post not found'})
                if row["author"] != username:
                    raise HTTPException(status_code=403, detail='Forbidden: not the author')

                fields = []
                params = []
                if payload.title is not None:
                    fields.append("title = %s")
                    params.append(payload.title)
                if payload.content is not None:
                    fields.append("content = %s")
                    params.append(payload.content)
                if payload.category_id is not None:
                    fields.append("category_id = %s")
                    params.append(payload.category_id)
                if not fields:
                    return JSONResponse(content={"message": "No changes"})

                fields.append("updated_at = CURRENT_TIMESTAMP")
                params.append(post_id)

                cursor.execute(
                    f"UPDATE posts SET {', '.join(fields)} WHERE id = %s",
                    tuple(params)
                )
                conn.commit()

                cursor.execute(
                    """SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, p.category_id,
                              c.name as category_name, c.slug as category_slug
                       FROM posts p LEFT JOIN categories c ON p.category_id = c.id
                       WHERE p.id = %s""",
                    (post_id,)
                )
                out = cursor.fetchone()
                post_dict = dict(out)
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT author FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail={'error': 'Post not found'})
            if row[0] != username:
                raise HTTPException(status_code=403, detail='Forbidden: not the author')

            fields = []
            params = []
            if payload.title is not None:
                fields.append("title = ?")
                params.append(payload.title)
            if payload.content is not None:
                fields.append("content = ?")
                params.append(payload.content)
            if payload.category_id is not None:
                fields.append("category_id = ?")
                params.append(payload.category_id)
            if not fields:
                return JSONResponse(content={"message": "No changes"})

            fields.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(post_id)

            cursor.execute(f"UPDATE posts SET {', '.join(fields)} WHERE id = ?", tuple(params))
            conn.commit()

            cursor.execute(
                """SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, p.category_id,
                          c.name as category_name, c.slug as category_slug
                   FROM posts p LEFT JOIN categories c ON p.category_id = c.id
                   WHERE p.id = ?""",
                (post_id,)
            )
            out = cursor.fetchone()
            post_dict = dict(out)

        # Format response with category info
        response = {
            "id": post_dict["id"],
            "title": post_dict["title"],
            "content": post_dict["content"],
            "author": post_dict["author"],
            "created_at": post_dict["created_at"].isoformat() if hasattr(post_dict["created_at"], 'isoformat') else str(post_dict["created_at"]),
            "updated_at": post_dict["updated_at"].isoformat() if hasattr(post_dict["updated_at"], 'isoformat') else str(post_dict["updated_at"]),
            "category": {
                "id": post_dict["category_id"],
                "name": post_dict["category_name"],
                "slug": post_dict["category_slug"]
            }
        }
        return JSONResponse(content=response)
    finally:
        conn.close()

@app.get("/api/categories")
async def handle_get_categories():
    """모든 카테고리 목록과 각 카테고리별 게시물 수를 반환합니다."""
    conn = get_db_connection()
    try:
        if USE_POSTGRES:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT c.id, c.name, c.slug, COUNT(p.id) as post_count
                    FROM categories c
                    LEFT JOIN posts p ON c.id = p.category_id
                    GROUP BY c.id, c.name, c.slug
                    ORDER BY c.id
                """)
                rows = cursor.fetchall()
                categories = [dict(r) for r in rows]
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.id, c.name, c.slug, COUNT(p.id) as post_count
                FROM categories c
                LEFT JOIN posts p ON c.id = p.category_id
                GROUP BY c.id, c.name, c.slug
                ORDER BY c.id
            """)
            rows = cursor.fetchall()
            categories = [dict(r) for r in rows]

        return JSONResponse(content=categories)
    finally:
        conn.close()

@app.delete("/api/posts/{post_id}", status_code=204)
async def delete_post(post_id: int, request: Request, username: str = Depends(require_user)):
    conn = get_db_connection()
    try:
        if USE_POSTGRES:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT author FROM posts WHERE id = %s", (post_id,))
                row = cursor.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail={'error': 'Post not found'})
                if row["author"] != username:
                    raise HTTPException(status_code=403, detail='Forbidden: not the author')
                cursor.execute("DELETE FROM posts WHERE id = %s", (post_id,))
                conn.commit()
        else:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT author FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail={'error': 'Post not found'})
            if row[0] != username:
                raise HTTPException(status_code=403, detail='Forbidden: not the author')
            cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()

        return Response(status_code=204)
    finally:
        conn.close()

@app.get("/health")
async def handle_health():
    """쿠버네티스를 위한 헬스 체크 엔드포인트"""
    return {"status": "ok", "service": "blog-service"}

@app.get("/stats")
async def handle_stats():
    """대시보드를 위한 통계 엔드포인트"""
    return {
        "blog_service": {
            "service_status": "online",
            "post_count": len(posts_db)
        }
    }

# --- 웹 페이지 서빙 (SPA) ---
@app.get("/blog/{path:path}")
async def serve_spa(request: Request, path: str):
    """메인 블로그 페이지를 렌더링합니다."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- 애플리케이션 시작 시 샘플 데이터 설정 ---
@app.on_event("startup")
def setup_sample_data():
    """서비스 시작 시 샘플 데이터를 생성합니다."""
    global posts_db, users_db
    posts_db = {
        1: {"id": 1, "title": "첫 번째 블로그 글", "author": "admin",
            "content": "마이크로서비스 아키텍처에 오신 것을 환영합니다! 이 블로그는 FastAPI로 리팩터링되었습니다."},
        2: {"id": 2, "title": "Kustomize와 Skaffold 활용하기", "author": "dev",
            "content": "인프라 관리가 이렇게 쉬울 수 있습니다. CI/CD 파이프라인을 통해 자동으로 배포됩니다."},
    }
    users_db = {
        'admin': {'password': 'password123'}
    }
    logger.info(f"{len(posts_db)}개의 샘플 게시물과 {len(users_db)}명의 사용자로 초기화되었습니다.")

if __name__ == "__main__":
    import uvicorn
    port = 8005
    logger.info(f"✅ Blog Service starting on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
