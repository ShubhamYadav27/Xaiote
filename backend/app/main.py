from app.core.logging_scrubber import setup_secure_logging
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import (
    analysis,
    auth,
    communication,
    company,
    customers,
    health,
    impacts,
    imports,
    incidents,
    machines,
    manufacturing_events,
    operational,
    plants,
    products,
    risk,
    vendors,
    webhooks,
    work_orders,
    alerts
)

setup_secure_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import os
    if os.environ.get("TESTING") == "true":
        logger.info("TESTING mode: Skipping background workers")
        t1, t2, t3 = None, None, None
    else:
        from app.workers.canonicalization_worker import canonicalization_worker_loop
        from app.workers.media_worker import media_worker_loop
        from app.workers.stt_worker import stt_worker_loop
        # Start background workers as tasks tied to this lifespan
        from app.workers.extraction_worker import extraction_worker_loop
        from app.workers.resolution_worker import resolution_worker_loop
        t1 = asyncio.create_task(media_worker_loop())
        t4 = asyncio.create_task(extraction_worker_loop())
        t5 = asyncio.create_task(resolution_worker_loop())
        t2 = asyncio.create_task(stt_worker_loop())
        t3 = asyncio.create_task(canonicalization_worker_loop())
        logger.info("Background workers started")
    yield
    # Cancel workers on shutdown
    if t1:
        t4.cancel()
        t5.cancel()
        t1.cancel()
    if t2:
        t2.cancel()
    if t3:
        t3.cancel()
    logger.info("Background workers shut down")

app = FastAPI(title="Xaiote API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://www.xaiote.com",
        "https://xaiote.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
            }
        },
    )

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(company.router, prefix="/api/company", tags=["company"])
app.include_router(plants.router, prefix="/api/v1/plants", tags=["plants"])
app.include_router(customers.router, prefix="/api/v1/customers", tags=["customers"])
app.include_router(vendors.router, prefix="/api/v1/vendors", tags=["vendors"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(machines.router, prefix="/api/v1/machines", tags=["machines"])
app.include_router(work_orders.router, prefix="/api/v1/work-orders", tags=["work_orders"])
app.include_router(imports.router, prefix="/api/v1/imports", tags=["imports"])
app.include_router(communication.router, prefix="/api/v1/communications", tags=["communications"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(manufacturing_events.router, prefix="/api/v1/events", tags=["events"])
app.include_router(impacts.router, prefix="/api/v1/impacts", tags=["impacts"])
app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(risk.router, prefix="/api/v1", tags=["risk"])
app.include_router(operational.router, prefix="/api/v1", tags=["operational"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
