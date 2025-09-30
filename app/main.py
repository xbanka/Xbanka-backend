from fastapi import FastAPI
from app.db.database import engine
from app.api.v1.routes import api_version_one
from app.models.base_model import Base
from app import models

app = FastAPI()
app.include_router(api_version_one)

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}


Base.metadata.create_all(bind=engine)
