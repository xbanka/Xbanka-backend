from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine
from app.api.v1.routes import api_version_one
from app.models.base_model import Base
from app import models

app = FastAPI()
app.include_router(api_version_one)

origins = [
    "http://localhost:3000",  # local dev FE
    "https://www.xbankang.com",  # production FE (affiliate domain)
    "https://erp.xbankang.com",  # production FE (erp domain)
]

# Add the middleware to your FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to XBanka API"}
