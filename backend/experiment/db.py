from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'replifactory.db')
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)