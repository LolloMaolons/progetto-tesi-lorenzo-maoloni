from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn, os, json, redis, time, logging, sys, uuid
from contextvars import ContextVar
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

logger = logging.getLogger("api-rest")
logHandler = logging.StreamHandler(sys. stdout)
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(trace_id)s"
)
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

r = redis.Redis. from_url(REDIS_URL)

limiter = Limiter(key_func=get_remote_address)

REQUEST_COUNT = Counter("api_rest_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("api_rest_request_duration_seconds", "Request latency", ["method", "endpoint"])
ERROR_COUNT = Counter("api_rest_errors_total", "Total errors", ["endpoint"])


app = FastAPI(title="API REST - Catalog/Orders/Users")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class Product(BaseModel):
    id: int
    name: str
    price: float
    stock:  int
    category: str | None = None
    description: str | None = None

BASE_PRODUCTS = {
    1: {"id": 1, "name":  "Laptop Pro", "price": 1499.0, "stock": 10, "category": "laptop", "description": '15" performance laptop'},
    2: {"id": 2, "name": "Mouse", "price": 29.0, "stock": 200, "category": "accessories", "description": "Wireless ergonomic mouse"},
    3: {"id": 3, "name": "Keyboard", "price":  79.0, "stock":  120, "category": "accessories", "description": "Mechanical keyboard"},
    4: {"id": 4, "name": "Monitor 27\"", "price": 329.0, "stock": 45, "category": "monitor", "description": '27" QHD IPS monitor'},
    5: {"id":  5, "name": "Headset", "price": 119.0, "stock": 80, "category": "audio", "description": "Wireless noise-cancelling headset"},
    6: {"id": 6, "name": "Webcam 4K", "price": 149.0, "stock": 60, "category": "accessories", "description": "4K streaming webcam"},
    7: {"id": 7, "name": "Docking Station", "price": 199.0, "stock": 35, "category": "accessories", "description": "USB-C docking station"},
    8: {"id": 8, "name": "SSD 1TB", "price":  129.0, "stock": 150, "category": "storage", "description": "NVMe 1TB SSD"},
    9: {"id": 9, "name": "GPU External", "price": 799.0, "stock": 8, "category": "gpu", "description": "External GPU enclosure"},
    10: {"id": 10, "name": "Laptop Air", "price": 999.0, "stock": 25, "category": "laptop", "description": '13" ultrabook'},
    11: {"id": 11, "name": "Smartphone Plus", "price": 899.0, "stock": 55, "category": "phone", "description": '6. 7" OLED smartphone'},
    12: {"id": 12, "name": "Tablet Max", "price": 649.0, "stock": 40, "category": "tablet", "description": '12" tablet with pen'},
    13: {"id": 13, "name": "Charger 100W", "price": 59.0, "stock": 300, "category": "accessories", "description": "GaN fast charger"},
    14: {"id": 14, "name":  "Router WiFi 6", "price": 179.0, "stock": 70, "category": "network", "description": "WiFi 6 tri-band router"},
    15: {"id": 15, "name": "NAS 4-bay", "price": 549.0, "stock": 15, "category": "storage", "description": "4-bay NAS with RAID"},
    16: {"id": 16, "name": "Printer Laser", "price": 229.0, "stock": 50, "category": "printer", "description": "Duplex laser printer"},
    17: {"id": 17, "name": "Smartwatch", "price": 249.0, "stock": 90, "category": "wearable", "description": "Fitness smartwatch"},
    18: {"id": 18, "name": "Earbuds Pro", "price": 159.0, "stock": 180, "category": "audio", "description": "ANC true wireless earbuds"},
    19: {"id": 19, "name": "Projector 1080p", "price": 399.0, "stock": 22, "category": "display", "description": "Portable 1080p projector"},
    20: {"id": 20, "name":  "Action Cam", "price":  299.0, "stock":  65, "category": "camera", "description": "4K action camera"},
}

DB_PRODUCTS = {k: Product(**v) for k, v in BASE_PRODUCTS.items()}

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request. headers.get("X-Request-ID", str(uuid.uuid4()))
    trace_id = request.headers.get("X-Trace-ID", request_id)
    request_id_ctx.set(request_id)
    
    start_time = time.time()
    method = request.method
    path = request.url.path
    
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "trace_id": trace_id,
            "method": method,
            "path": path,
        }
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(method=method, endpoint=path, status=response.status_code).inc()
        REQUEST_LATENCY. labels(method=method, endpoint=path).observe(duration)
        
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "method":  method,
                "path": path,
                "status":  response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        )
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        return response
    except Exception as e:
        ERROR_COUNT.labels(endpoint=path).inc()
        logger.error(
            f"Request failed:  {str(e)}",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "method": method,
                "path": path,
            }
        )
        raise

@app.get("/health")
async def health_check():
    try:
        r.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "degraded", "redis": "disconnected", "error": str(e)}

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post("/reset")
@limiter.limit(RATE_LIMIT)
async def reset_products(request: Request):
    global DB_PRODUCTS
    DB_PRODUCTS = {k: Product(**v) for k, v in BASE_PRODUCTS.items()}
    logger.info("All products reset to base values", extra={"request_id": request_id_ctx.get()})
    return {"message": "All products reset to base values", "count": len(DB_PRODUCTS)}

@app.get("/products", response_model=List[Product])
@limiter.limit(RATE_LIMIT)
async def list_products(request: Request, limit: int | None = None, category: str | None = None):
    items = list(DB_PRODUCTS.values())
    if category:
        items = [p for p in items if p.category == category]
    if limit:
        items = items[:limit]
    return items

@app.get("/products/{pid}", response_model=Product)
@limiter.limit(RATE_LIMIT)
async def get_product(request: Request, pid: int):
    p = DB_PRODUCTS.get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    return p

@app.get("/products/{pid}/recommendations", response_model=List[Product])
@limiter.limit(RATE_LIMIT)
async def get_recommendations(request: Request, pid: int, limit: int = 3):
    if pid not in DB_PRODUCTS:
        raise HTTPException(404, "Not found")
    category = DB_PRODUCTS[pid].category
    items = [p for p in DB_PRODUCTS.values() if p.id != pid and p.category == category]
    if len(items) < limit:
        others = [p for p in DB_PRODUCTS.values() if p.id != pid and p not in items]
        items = (items + others)[:limit]
    return items[:limit]


@app.patch("/products/{pid}", response_model=Product)
@limiter.limit(RATE_LIMIT)
async def update_product(request: Request, pid: int, stock: int | None = None, price: float | None = None):
    p = DB_PRODUCTS.get(pid)
    if not p:
        raise HTTPException(404, "Not found")
    if stock is not None:
        p.stock = stock
        try:
            r.publish("events", json.dumps({"type": "stock_update", "id": pid, "stock": stock}))
            THRESHOLD = 25
            if stock <= THRESHOLD:
                r.publish("product-lowstock", str(pid))
        except Exception as e: 
            logger.error(f"Redis publish stock_update error: {e}", extra={"request_id": request_id_ctx.get()})
    if price is not None:
        p.price = price
        try:
            r.publish("events", json.dumps({"type": "price_update", "id": pid, "price": price}))
        except Exception as e:
            logger.error(f"Redis publish price_update error: {e}", extra={"request_id": request_id_ctx.get()})
    return p

from fastapi import Body

class ProductPatch(BaseModel):
    id: int
    stock: Optional[int] = None
    price: Optional[float] = None

@app.patch("/products", response_model=List[Product])
@limiter.limit(RATE_LIMIT)
async def patch_multiple_products(
    request: Request,
    updates: List[ProductPatch] = Body(...)
):
    updated = []
    for upd in updates:
        p = DB_PRODUCTS.get(upd.id)
        if not p:
            continue
        if upd.stock is not None:
            p.stock = upd.stock
            try:
                r.publish("events", json.dumps({"type": "stock_update", "id": upd.id, "stock": upd.stock}))
                THRESHOLD = 25
                if upd.stock <= THRESHOLD:
                    r.publish("product-lowstock", str(upd.id))
            except Exception as e:
                logger.error(f"Redis publish stock_update error: {e}", extra={"request_id": request_id_ctx.get()})
        if upd.price is not None:
            p.price = upd.price
            try:
                r.publish("events", json.dumps({"type": "price_update", "id": upd.id, "price": upd.price}))
            except Exception as e:
                logger.error(f"Redis publish price_update error: {e}", extra={"request_id": request_id_ctx.get()})
        updated.append(p)
    return updated

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)