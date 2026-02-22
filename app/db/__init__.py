# app/db/init.py
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


def ensure_txn_sequence(db: Session):
    year = datetime.now().year
    db.execute(text(f"CREATE SEQUENCE IF NOT EXISTS txn_{year}_seq START 1;"))
    db.commit()
