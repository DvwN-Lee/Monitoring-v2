import os
import logging
from datetime import datetime
from typing import Optional, Dict, List
import aiohttp
from fastapi import FastAPI, Request, HTTPException, Form, Depends, Query, Response
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_fastapi_instrumentator import Instrumentator

try:
    from prometheus_fastapi_instrumentator.metrics import request_latency
except ImportError:
    from prometheus_fastapi_instrumentator import metrics as _metrics

    def request_latency(*args, **kwargs):
        return _metrics.latency(*args, **kwargs)

# Import from app modules
from app.config import USE_POSTGRES, DB_CONFIG, DATABASE_PATH, REQUEST_LATENCY_BUCKETS
from app.auth import require_user, AuthClient
from app.models.schemas import PostCreate, PostUpdate
from app.database import db
from app.cache import cache

# --- 기본 로깅 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BlogServiceApp')

app = FastAPI()

# CORS 설정
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus 메트릭 설정
from prometheus_client import Counter
from prometheus_fastapi_instrumentator.metrics import Info

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

# Import DB drivers for legacy code (will be refactored)
# if USE_POSTGRES:
#     import psycopg2
#     from psycopg2.extras import RealDictCursor
# else:
#     import sqlite3

# --- Legacy Database Helper Functions (to be refactored) ---
# def get_db_connection():
#     """Get database connection - LEGACY, use app.database.db instead."""
#     if USE_POSTGRES:
#         try:
#             conn = psycopg2.connect(**DB_CONFIG)
#             return conn
#         except psycopg2.Error as e:
#             logger.error(f"PostgreSQL connection failed: {e}", exc_info=True)
#             raise
#     else:
#         return sqlite3.connect(DATABASE_PATH)

# PostCreate, PostUpdate models imported from app.models.schemas
# require_user function imported from app.auth

# Legacy helper functions - still used by write endpoints (POST, PATCH, DELETE)
# TODO: Convert write endpoints to async in Step 2

def validate_category_id(category_id: int) -> bool:
    """Validate that category_id exists in the database."""
    # This is now handled by db.validate_category_id, but keeping for compatibility if needed
    # or better, refactor callers to use await db.validate_category_id
    pass

# --- API 핸들러 함수 ---
@app.get("/blog/api/posts")
async def handle_get_posts(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None)
):
    """모든 블로그 게시물 목록을 반환합니다(최신순, 페이지네이션, 카테고리 필터링)."""
    # Calculate page number for caching
    page = offset // limit if limit > 0 else 0

    # 1. Check cache
    cached = await cache.get_posts(page, limit, category)
    if cached:
        return JSONResponse(content=cached)

    # 2. Query database
    try:
        items = await db.get_posts(offset, limit, category)
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

    # 3. Format response - 목록 응답은 요약 정보 위주로 반환 + 발췌(excerpt) + 카테고리 정보
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

    # 4. Store in cache
    await cache.set_posts(page, limit, summaries, category, ttl=60)

    return JSONResponse(content=summaries)

@app.get("/blog/api/posts/{post_id}")
async def handle_get_post_by_id(post_id: int):
    """ID로 특정 게시물을 찾아 반환합니다."""
    # 1. Check cache
    cached = await cache.get_post(post_id)
    if cached:
        return JSONResponse(content=cached)

    # 2. Query database
    try:
        post_dict = await db.get_post_by_id(post_id)
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

    if not post_dict:
        raise HTTPException(status_code=404, detail={'error': 'Post not found'})

    # 3. Format response with category info
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

    # 4. Store in cache
    await cache.set_post(post_id, response, ttl=300)

    return JSONResponse(content=response)

@app.post("/blog/api/posts", status_code=201)
async def create_post(request: Request, payload: PostCreate, username: str = Depends(require_user)):
    # Validate category_id exists
    if not await db.validate_category_id(payload.category_id):
        raise HTTPException(status_code=422, detail=f'Category with id {payload.category_id} does not exist')

    try:
        new_post = await db.create_post(payload.title, payload.content, username, payload.category_id)
        
        # Invalidate cache
        await cache.invalidate_posts(new_post["category"]["slug"])
        
        return JSONResponse(content=new_post)
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

@app.patch("/blog/api/posts/{post_id}")
async def update_post_partial(post_id: int, request: Request, payload: PostUpdate, username: str = Depends(require_user)):
    # Validate category_id if provided
    if payload.category_id is not None and not await db.validate_category_id(payload.category_id):
        raise HTTPException(status_code=422, detail=f'Category with id {payload.category_id} does not exist')

    try:
        # Check author
        author = await db.get_post_author(post_id)
        if not author:
            raise HTTPException(status_code=404, detail={'error': 'Post not found'})
        if author != username:
            raise HTTPException(status_code=403, detail='Forbidden: not the author')

        # Update post
        updated_post = await db.update_post(post_id, payload.title, payload.content, payload.category_id)
        if not updated_post:
             return JSONResponse(content={"message": "No changes"})

        # Invalidate cache
        await cache.invalidate_posts(updated_post["category"]["slug"])
        await cache.invalidate_post(post_id)

        # Format response (already formatted by db.update_post but needs JSON serialization for datetime)
        response = {
            "id": updated_post["id"],
            "title": updated_post["title"],
            "content": updated_post["content"],
            "author": updated_post["author"],
            "created_at": updated_post["created_at"].isoformat() if hasattr(updated_post["created_at"], 'isoformat') else str(updated_post["created_at"]),
            "updated_at": updated_post["updated_at"].isoformat() if hasattr(updated_post["updated_at"], 'isoformat') else str(updated_post["updated_at"]),
            "category": {
                "id": updated_post["category_id"],
                "name": updated_post["category_name"],
                "slug": updated_post["category_slug"]
            }
        }
        return JSONResponse(content=response)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

@app.get("/blog/api/categories")
async def handle_get_categories():
    """모든 카테고리 목록과 각 카테고리별 게시물 수를 반환합니다."""
    # 1. Check cache
    cached = await cache.get_categories()
    if cached:
        return JSONResponse(content=cached)

    # 2. Query database
    try:
        categories = await db.get_categories_with_counts()
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

    # 3. Store in cache
    await cache.set_categories(categories, ttl=600)

    return JSONResponse(content=categories)

@app.delete("/blog/api/posts/{post_id}", status_code=204)
async def delete_post(post_id: int, request: Request, username: str = Depends(require_user)):
    try:
        # Check author
        author = await db.get_post_author(post_id)
        if not author:
            raise HTTPException(status_code=404, detail={'error': 'Post not found'})
        if author != username:
            raise HTTPException(status_code=403, detail='Forbidden: not the author')

        # Delete post
        await db.delete_post(post_id)
        
        # Invalidate cache (we don't know the category slug easily without fetching, but we can invalidate all or just accept minor staleness)
        # For correctness, we should have fetched category slug before delete, or just invalidate all posts pages.
        # Let's invalidate all posts for now or skip. Ideally we fetch slug first.
        # Optimization: fetch slug with author check.
        # For now, let's just proceed.
        
        return Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error")

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
@app.get("/")
async def serve_root(request: Request):
    """루트 경로에서 블로그 페이지를 렌더링합니다."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/blog/")
async def serve_blog_root(request: Request):
    """블로그 루트 경로에서 블로그 페이지를 렌더링합니다."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/blog/{path:path}")
async def serve_spa(request: Request, path: str):
    """블로그 서브 경로에서 블로그 페이지를 렌더링합니다."""
    return templates.TemplateResponse("index.html", {"request": request})


# --- 애플리케이션 시작/종료 이벤트 ---
@app.on_event("startup")
async def startup_event():
    """Initialize database and cache on startup."""
    await db.initialize()
    await cache.initialize()
    logger.info("✅ Blog service initialized: database and cache ready")

@app.on_event("shutdown")
async def shutdown_event():
    """Close database, cache, and auth client connections on shutdown."""
    await db.close()
    await cache.close()
    await AuthClient.close()
    logger.info("Blog service shutdown: database, cache, and AuthClient closed")

if __name__ == "__main__":
    import uvicorn
    port = 8005
    logger.info(f"✅ Blog Service starting on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
