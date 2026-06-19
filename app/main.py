import logging
import sentry_sdk

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.routes import api_version_one
# from app.api.v2.routes import api_version_two
from app.utils.settings import settings


SECRET_KEY = settings.SECRET_KEY
ENVIRONMENT = settings.ENVIRONMENT

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

sentry_sdk.init(
    dsn="https://3b0caa4bd51b30c493e60d5a746c1e78@o4511098605862912.ingest.de.sentry.io/4511098608549968",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    # Enable sending logs to Sentry
    enable_logs=True,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for tracing.
    traces_sample_rate=1.0,
    # Set profile_session_sample_rate to 1.0 to profile 100%
    # of profile sessions.
    profile_session_sample_rate=1.0,
    # Set profile_lifecycle to "trace" to automatically
    # run the profiler on when there is an active transaction
    profile_lifecycle="trace",
    environment=ENVIRONMENT,
)

app = FastAPI()
app.include_router(api_version_one)
# app.include_router(api_version_two)

logger = logging.getLogger(__name__)

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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log the details for debugging purposes
    print(f"Validation error on request {request.url}: {exc}")

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

    logger.exception("response validation error", extra={"errors": errors})

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


@app.get("/sentry-debug")
def sentry():
    div_by_zero = 1 / 0
    return {"result": div_by_zero}
