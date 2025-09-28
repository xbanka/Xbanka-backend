from fastapi import FastAPI
from .db.database import Base, engine
from .api.v1.routes import api_version_one

app = FastAPI()
app.include_router(api_version_one)

@app.get("/")
def read_root():
    return {"message": "Hello, world!"}


Base.metadata.create_all(bind=engine)
