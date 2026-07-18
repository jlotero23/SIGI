"""Punto de entrada FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import CORS_ORIGINS
from .database import init_db
from .services.data_service import ensure_default_dataset


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_default_dataset()
    yield


app = FastAPI(
    title="Sistema IA - Pronóstico y Reabastecimiento",
    description="PoC académica con Agente 1 (pronóstico) y Agente 2 (reabastecimiento)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    from .config import API_HOST, API_PORT

    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)
