"""Single FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import get_settings
from app.services.dataset import DatasetRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    repository = DatasetRepository(settings.data_directory, settings.knowledge_base_directory)
    repository.summary()  # Eager loading makes invalid provided data a startup failure.
    app.state.dataset_repository = repository
    yield


app = FastAPI(title="US Delivery AI", version="0.1.0", description="Foundation for the US Delivery internship technical task.", lifespan=lifespan)
app.include_router(router)
