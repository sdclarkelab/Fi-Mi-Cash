from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_v1.dependencies import verify_api_key
from app.api.api_v1.routers.category_rules_router import router as category_rules_router
from app.api.api_v1.routers.sync_router import router as sync_router
from app.api.api_v1.routers.transactions_router import router as transactions_router
from app.config import get_settings
from app.core.logger import logger
from app.db.base_class import Base
from app.db.database import engine
from app.db.migrations import run_startup_migrations

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Transaction API")

    # Initialize database tables
    logger.info("Creating database tables if they don't exist")
    Base.metadata.create_all(bind=engine)
    run_startup_migrations(engine)

    yield

    # Shutdown
    logger.info("Shutting down Transaction API")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS: only the local frontend may call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router — every route requires the X-API-Key header
app.include_router(
    transactions_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    category_rules_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    sync_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
