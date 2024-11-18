from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_v1.endpoints import router as api_router
from app.config import get_settings
from app.core.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Transaction API")

    # Your startup code here
    # For example:
    # - Initialize database connections
    # - Set up background tasks
    # - Initialize cache
    # - Warm up ML models

    yield

    # Shutdown
    logger.info("Shutting down Transaction API")
    # Your cleanup code here
    # For example:
    # - Close database connections
    # - Stop background tasks
    # - Clear cache
    # - Release resources


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
