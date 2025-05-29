from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Use the same database path as Flask
script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, '../db/replifactory.db')
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 