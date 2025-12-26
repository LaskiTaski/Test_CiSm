from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.services.queue_service import QueueService


@asynccontextmanager
async def lifespan(app: FastAPI):
    queue_service = QueueService()
    await queue_service.connect()
    app.state.queue_service = queue_service
    yield
    await queue_service.disconnect()


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}