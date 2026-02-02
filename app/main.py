from app import models
from app.api.v1.routes import api_version_one
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.db import ensure_txn_sequence
from app.db.database import SessionLocal

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

app = FastAPI()
app.include_router(api_version_one)

logger = logging.getLogger(__name__)

origins = [
    "http://localhost:3000",  # local dev FE
    "https://www.xbankang.com",  # production FE (affiliate domain)
    "https://erp.xbankang.com",  # production FE (erp domain)
    "https://adminerp.vercel.app",  
]

# Add the middleware to your FastAPI app
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
        errors.append({ "field": field, "message": message })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation Error",
            "errors": errors,
            "hint": "Check the data format and required fields."
        },
    )

@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(
    request: Request,
    exc: ResponseValidationError
):
    
    # Customize the response content
    errors = []
    for error in exc.errors():
        field = error["loc"][-1]
        message = error["msg"]
        errors.append({ "field": field, "message": message })

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

