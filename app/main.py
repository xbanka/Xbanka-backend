import asyncio
import logging
import sentry_sdk
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exception_handlers import (
    http_exception_handler as default_http_exception_handler,
)
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.core.logging import redact, setup_logging
from app.core.middleware import RequestLoggingMiddleware
from app.utils.settings import settings

SECRET_KEY = settings.SECRET_KEY
ENVIRONMENT = settings.ENVIRONMENT

# Configure logging before the rest of the app imports so module loggers
# created at import time pick it up.
setup_logging(ENVIRONMENT, settings.LOG_LEVEL)

from app.api.v1.routes import api_version_one  # noqa: E402
# from app.api.v2.routes import api_version_two
from app.services.websocket_manager import notification_manager  # noqa: E402

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     db = SessionLocal()
#     try:
#         ensure_txn_sequence(db)
#     finally:
#         db.close()
#     yield
#     # Shutdown
#     pass

logger = logging.getLogger(__name__)


def _scrub_event(event, hint):
    """Mask credentials in anything Sentry is about to send."""
    return redact(event)


if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        # Request headers, cookies and IPs stay out of events.
        send_default_pii=False,
        enable_logs=True,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        environment=ENVIRONMENT,
        before_send=_scrub_event,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # notification_manager pushes are triggered from sync (threadpool) route
    # handlers, so it needs a handle on the loop to hop back onto it.
    notification_manager.set_loop(asyncio.get_running_loop())
    logger.info(
        "application startup",
        extra={"environment": ENVIRONMENT, "sentry_enabled": bool(settings.SENTRY_DSN)},
    )
    yield
    logger.info("application shutdown")


app = FastAPI(lifespan=lifespan)
app.include_router(api_version_one)
# app.include_router(api_version_two)

origins = [
    "http://localhost:3000",  # local dev FE
    "https://www.xbankang.com",  # production FE (affiliate domain)
    "https://erp.xbankang.com",  # production FE (erp domain)
    "https://adminerp.vercel.app",
    "https://admin-testing-lyart.vercel.app",
    "https://stagingerp.xbankang.com"
]

# Add the middleware to your FastAPI app
# --- Middleware ---
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Added last so it is outermost and times the whole stack.
app.add_middleware(RequestLoggingMiddleware)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code >= 500:
        logger.error(
            "http %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    else:
        logger.info(
            "http %s on %s %s: %s",
            exc.status_code, request.method, request.url.path, exc.detail,
        )
    return await default_http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _request_id(request)
    logger.exception(
        "unhandled exception on %s %s",
        request.method, request.url.path,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Internal server error", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log field locations and error types only; the submitted input can hold
    # passwords and other secrets.
    logger.warning(
        "validation error on %s %s",
        request.method, request.url.path,
        extra={
            "errors": [
                {"loc": ".".join(str(p) for p in e["loc"]), "type": e["type"]}
                for e in exc.errors()
            ]
        },
    )

    # Customize the response content
    errors = []
    for error in exc.errors():
        field = error["loc"][-1]
        message = error["msg"]
        errors.append({"field": field, "message": message})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation Error",
            "errors": errors,
            "hint": "Check the data format and required fields.",
        },
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(
    request: Request, exc: ResponseValidationError
):

    # Customize the response content
    errors = []
    for error in exc.errors():
        field = error["loc"][-1]
        message = error["msg"]
        errors.append({"field": field, "message": message})

    logger.exception(
        "response validation error on %s %s",
        request.method, request.url.path,
        extra={"errors": errors},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal response validation error",
            "path": request.url.path,
        },
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to XBanka API"}


if ENVIRONMENT.lower() not in ("production", "prod"):

    @app.get("/sentry-debug")
    def sentry():
        div_by_zero = 1 / 0
        return {"result": div_by_zero}
