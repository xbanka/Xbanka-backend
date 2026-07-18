from app.db.database import SessionLocal
from app.models import *

db = SessionLocal()

print("Database session available as `db`")
