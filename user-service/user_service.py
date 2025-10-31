# TItanium-v2/user-service/user_service.py
# Version: 1.2.1 - Improved Prometheus histogram buckets for accurate P95/P99

import logging
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import request_latency

from database_service import UserServiceDatabase
from cache_service import CacheService

class UserIn(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr

class Credentials(BaseModel):
    username: str
    password: str

app = FastAPI()
db = UserServiceDatabase()
cache = CacheService()

# Prometheus 메트릭 설정
# 히스토그램 버킷을 세밀하게 설정하여 정확한 P95/P99 계산 가능
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

    instrumentator.instrument(application).expose(application)


configure_metrics(app)

# --- User Service의 통계 및 DB/Cache 상태를 반환하는 엔드포인트 ---
@app.get("/stats")
async def handle_stats():
    # DB와 Cache의 상태를 실시간으로 확인
    is_db_healthy = await db.health_check()
    is_cache_healthy = await cache.ping()

    # 전체 서비스 상태 결정
    service_status = "online"
    if not is_db_healthy or not is_cache_healthy:
        service_status = "degraded"

    return {
        "user_service": {
            "service_status": service_status,
            # 대시보드가 인식할 수 있는 키로 DB와 Cache 상태를 제공
            "database": {
                "status": "healthy" if is_db_healthy else "unhealthy"
            },
            "cache": {
                "status": "healthy" if is_cache_healthy else "unhealthy",
                "hit_ratio": 0 # 이 예제에서는 단순화를 위해 0으로 고정
            }
        }
    }


# ... (기존 /health, /users 엔드포인트들은 그대로 유지) ...
@app.get("/health")
async def handle_health():
    return {"status": "healthy"}

@app.post("/users", response_model=UserOut, status_code=201)
async def create_user(user: UserIn):
    user_id = await db.add_user(user.username, user.email, user.password)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Username already exists")
    created_user = await db.get_user_by_id(user_id)
    return created_user

@app.get("/users/{username}", response_model=UserOut)
async def get_user(username: str):
    cached_user = await cache.get_user(username)
    if cached_user:
        return cached_user

    user_from_db = await db.get_user_by_username(username)
    if not user_from_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    await cache.set_user(username, user_from_db)
    return user_from_db

@app.post("/users/verify-credentials")
async def verify_credentials(creds: Credentials):
    user = await db.verify_user_credentials(creds.username, creds.password)
    if user:
        return user
    raise HTTPException(status_code=401, detail="Invalid credentials")
