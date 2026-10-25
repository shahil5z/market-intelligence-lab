"""FastAPI entry point: uvicorn app.main:app --reload (run from backend/)."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import FRONTEND_ORIGINS
from app.utils.artifacts import ArtifactMissing

logging.basicConfig(level=logging.INFO)
app = FastAPI(
    title="Market Intelligence Lab API",
    version="0.1.0",
    description="Analytics API over a public retail dataset (UCI Online Retail II) plus labelled synthetic dimensions.",
)
app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])
app.include_router(router)


@app.exception_handler(ValueError)
async def value_error(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(KeyError)
async def key_error(_: Request, exc: KeyError):
    return JSONResponse(status_code=404, content={"detail": str(exc).strip("'\"")})


@app.exception_handler(ArtifactMissing)
@app.exception_handler(FileNotFoundError)
async def missing(_: Request, exc: Exception):
    return JSONResponse(status_code=503, content={"detail": str(exc)})
