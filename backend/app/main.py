from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models
from app.config import Settings
from app.db import Base, engine
from app.routers import health, users


def create_app() -> FastAPI:
    settings = Settings()
    Base.metadata.create_all(bind=engine)
    app = FastAPI(title="Local Bitcoin Bank")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(users.router)
    return app


app = create_app()
