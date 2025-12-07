# Troubleshooting: Blog Service CRUD Endpoint Errors

**Date:** 2025-12-07
**Service:** Blog Service
**Status:** ✅ Resolved

---

## 1. 문제 요약 (Executive Summary)

Phase 4 품질 검증(E2E Testing) 과정에서 Blog Service의 게시물 작성(Create), 수정(Update), 삭제(Delete) Endpoint가 `500 Internal Server Error`를 반환하는 문제가 발견되었습니다. 조회(Read) 기능은 정상이었으나, 쓰기 작업 전반이 블락되는 Critical Issue였습니다.

| Endpoint | Method | Error Code | Root Cause |
|---|---|---|---|
| `/blog/api/posts` | POST | 500 | `datetime` 객체의 JSON 직렬화 불가 |
| `/blog/api/posts` | POST | 200 (Logic) | 성공 시 201 Created 대신 200 OK 반환 (Test Fail) |
| `/blog/api/posts/{id}` | PATCH | 500 | 존재하지 않는 캐시 메서드 호출 (`AttributeError`) |
| `/blog/api/posts/{id}` | DELETE | 500 | Dictionary 접근 패턴 오류 (`KeyError`) 및 인자 불일치 (`TypeError`) |

---

## 2. Root Cause Analysis & Resolution

### 2.1. POST Endpoint - Datetime Serialization
**증상:** 게시물 작성 시 `TypeError: Object of type datetime is not JSON serializable` 로그와 함께 500 에러 발생.

**원인:**
`asyncpg` (PostgreSQL Driver)는 `TIMESTAMP` 컬럼 반환 시 Python의 `datetime` 객체를 반환합니다. 그러나 FastAPI/Pydantic이 아닌 일반 `dict`를 `JSONResponse`로 반환하려고 할 때, 기본 JSON Encoder는 `datetime` 객체를 처리하지 못합니다.

**수정 전 (Error):**
```python
# database.py
created_at = row["created_at"]  # datetime object
```

**수정 후 (Fixed):**
`isoformat()` 메서드를 사용하여 JSON 호환 가능한 문자열로 변환했습니다.
```python
# Commit: cb785e1
created_at = row["created_at"].isoformat() if row["created_at"] else None
```

### 2.2. POST Endpoint - HTTP Status Code
**증상:** 게시물 작성은 성공했으나, E2E 테스트에서 `Expected 201, Got 200` 에러 발생.

**원인:**
FastAPI 데코레이터에 `@app.post(..., status_code=201)`을 명시했더라도, 핸들러 함수가 내부에서 `JSONResponse`를 직접 반환하는 경우, `JSONResponse`의 기본값인 `200 OK`가 우선 적용됩니다.

**수정 후 (Fixed):**
```python
# Commit: c556fcd
return JSONResponse(content=new_post, status_code=201)
```

### 2.3. UPDATE Endpoint - Cache Method Error
**증상:** 게시물 수정 시 `AttributeError: 'BlogCache' object has no attribute 'invalidate_post'` 발생.

**원인:**
개발 과정에서 `BlogCache` 클래스에 `invalidate_post(post_id)` 메서드가 구현되지 않았거나 삭제되었으나, 비즈니스 로직(`blog_service.py`)에서는 해당 메서드를 호출하고 있었습니다.

**수정 후 (Fixed):**
존재하지 않는 메서드 호출을 제거하고, 이미 구현된 전체 무효화 메서드(`invalidate_posts()`)만 사용하도록 변경했습니다.
```python
# Commit: a943fbd
# Removed: await cache.invalidate_post(post_id)
await cache.invalidate_posts()
```

### 2.4. DELETE Endpoint - Key Error & Type Error
**증상:** 게시물 삭제 시 `KeyError: 'category'` 및 `TypeError` 발생.

**원인 1 (KeyError):**
DB 조회 메서드(`get_post_by_id`)는 Flat Dictionary 구조(`category_slug`)를 반환하지만, 코드에서는 Nested Dictionary(`post['category']['slug']`)로 접근했습니다.

**원인 2 (TypeError):**
캐시 무효화 함수 `invalidate_posts()`는 인자를 받지 않도록 정의되어 있으나(`def invalidate_posts(self):`), 코드에서는 `category_slug`를 인자로 전달했습니다.

**수정 후 (Fixed):**
```python
# Commit: a943fbd
category_slug = post['category_slug']  # Flat Key 사용
await db.delete_post(post_id)
await cache.invalidate_posts()         # 인자 제거
```

---

## 3. 검증 결과

수정 사항 적용 후 `k6` 기반의 E2E 테스트를 재수행하여 모든 시나리오가 통과됨을 확인했습니다.

- **E2E Test Result:** 100% Pass (15/15 Checks)
- **Commits:**
    - `cb785e1` (Serialization)
    - `c556fcd` (Status Code)
    - `a943fbd` (Update/Delete Fixes)
