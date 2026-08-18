from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models
from app.bitcoin_rpc import BitcoinRpcError
from app.config import Settings
from app.db import Base, engine
from app.routers import faucet, health, mining, transactions, users, wallets


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

    @app.exception_handler(BitcoinRpcError)
    def bitcoin_rpc_error_handler(request: Request, exc: BitcoinRpcError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(health.router)
    app.include_router(faucet.router)
    app.include_router(mining.router)
    app.include_router(transactions.router)
    app.include_router(users.router)
    app.include_router(wallets.router)
    return app


app = create_app()
