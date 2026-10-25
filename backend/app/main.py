"""FastAPI entry point. Local: `uvicorn app.main:app --reload` (from backend/). Vercel imports `app` from index.py."""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import FRONTEND_ORIGINS
from app.utils.artifacts import ArtifactMissing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("mil.api")

app = FastAPI(
    title="Market Intelligence Lab API",
    version="1.0.0",
    description="Analytics API over a public retail dataset (UCI Online Retail II) plus labelled synthetic dimensions.",
)
app.add_middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.include_router(router)


@app.middleware("http")
async def access_log(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s -> %s in %.0f ms", request.method, request.url.path, response.status_code, 1000 * (time.perf_counter() - t0))
    return response


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    fields = ", ".join(".".join(str(p) for p in e["loc"] if p != "body") for e in exc.errors())
    return _error(422, f"Invalid request parameters: {fields}")


@app.exception_handler(ValueError)
async def value_error(_: Request, exc: ValueError):
    return _error(400, str(exc))  # messages are written by our own validation code


@app.exception_handler(KeyError)
async def key_error(_: Request, exc: KeyError):
    return _error(404, str(exc).strip("'\""))


@app.exception_handler(ArtifactMissing)
@app.exception_handler(FileNotFoundError)
async def missing(request: Request, exc: Exception):
    log.error("Data artifact missing for %s: %s", request.url.path, exc)
    return _error(503, "Analysis data is temporarily unavailable.")


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return _error(500, "Something went wrong while computing this result.")
