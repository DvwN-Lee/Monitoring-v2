import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

try:
    from prometheus_fastapi_instrumentator.metrics import request_latency
except ImportError:  # Older library versions expose latency helper instead
    from prometheus_fastapi_instrumentator import metrics as _metrics

    def request_latency(*args, **kwargs):
        return _metrics.latency(*args, **kwargs)

from config import config
from auth_service import AuthService

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('AuthServiceApp')

# FastAPI 앱 생성
app = FastAPI()
auth_service = AuthService()

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
    """
    Configure Prometheus metrics with backward-compatible bucket settings.
    Older versions of Instrumentator do not accept the `buckets` kwarg directly.
    """
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


# --- API 엔드포인트 ---
@app.post("/login")
async def handle_login(request: Request):
    """로그인 요청을 처리하고 JWT 토큰을 반환합니다."""
    try:
        data = await request.json()
        result = await auth_service.login(data.get('username'), data.get('password'))
        status_code = 200 if result.get('status') == 'success' else 401
        return JSONResponse(content=result, status_code=status_code)
    except Exception:
        raise HTTPException(status_code=400, detail={"status": "failed", "message": "Invalid request body"})

@app.get("/verify")
async def validate_token(request: Request):
    """토큰 유효성을 검증합니다."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=400, detail={'valid': False, 'error': 'Authorization header missing or invalid'})

    token = auth_header.split(' ')[1]
    result = auth_service.verify_token(token)
    is_valid = result.get('status') == 'success'
    status_code = 200 if is_valid else 401
    return JSONResponse(content=result, status_code=status_code)

@app.get("/health")
async def handle_health():
    """헬스 체크 엔드포인트"""
    return {"status": "ok", "service": "auth-service"}

@app.get("/stats")
async def handle_stats():
    """서비스의 간단한 통계를 반환합니다."""
    stats_data = {
        "auth": {
            "service_status": "online",
            "active_session_count": 0  # 실제 구현에서는 세션 수를 추적해야 합니다.
        }
    }
    return stats_data

# --- Uvicorn으로 앱 실행 ---
if __name__ == "__main__":
    import uvicorn
    logger.info(f"✅ Auth Service starting on http://{config.server.host}:{config.server.port}")
    uvicorn.run(app, host=config.server.host, port=config.server.port)
