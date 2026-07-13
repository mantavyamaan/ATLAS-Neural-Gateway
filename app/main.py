"""
ATLAS Neural Gateway service entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Then visit http://127.0.0.1:8000/docs for interactive API docs.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as atlas_gateway
from app.config import CORS_ORIGINS, ROUTER_VERSION

from contextlib import asynccontextmanager

from app.core.database import init_db
from app.core.openrouter_sync import sync_openrouter_models

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Pull live models from OpenRouter (only seeds if DB is empty)
    sync_openrouter_models()
    yield

app = FastAPI(
    title="ATLAS Neural Gateway",
    description=(
        "Adaptive Task and LLM Allocation System — a complete, end-to-end AI agent "
        "and neural routing gateway. ATLAS decides which model should handle a request "
        "using Bayesian inference, and acts as an intelligent proxy to actively generate "
        "and stream the final response back to the user."
    ),
    version=ROUTER_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(atlas_gateway, tags=["atlas-gateway"])


@app.get("/", tags=["meta"])
async def root():
    return {
        "service": "ATLAS Neural Gateway",
        "version": ROUTER_VERSION,
        "docs": "/docs",
    }
