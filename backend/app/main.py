from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_v1_router
from app.api.websockets import router as ws_router
from app.seed import seed_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("nexdial")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NEXDIAL backend database and services...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed data if empty
    try:
        await seed_data()
    except Exception as e:
        logger.warning(f"Seed data exception (may already be initialized): {e}")

    logger.info("NEXDIAL backend ready to accept connections.")
    yield
    logger.info("Shutting down NEXDIAL backend...")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent SmartDialer & Predictive Contact Center Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API & WebSockets
app.include_router(api_v1_router, prefix="/api")
app.include_router(ws_router)

@app.get("/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }

@app.get("/")
async def root():
    return {
        "platform": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs",
        "api_v1": "/api/v1",
        "websocket": "/ws/live"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
