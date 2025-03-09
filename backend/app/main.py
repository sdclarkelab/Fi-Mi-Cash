from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api_v1.routers.category_rules_router import router as category_rules_router
from app.api.api_v1.routers.transactions_router import router as transactions_router
from app.config import get_settings
from app.core.logger import logger
from app.db.base_class import Base
from app.db.database import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Transaction API")

    # Initialize database tables
    logger.info("Creating database tables if they don't exist")
    Base.metadata.create_all(bind=engine)

    yield

    # Shutdown
    logger.info("Shutting down Transaction API")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Update this to only allow specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(transactions_router, prefix=settings.API_V1_STR)
app.include_router(category_rules_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
