from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Read the database URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://notes_user:notes_pass@localhost:5432/notes_db"
)

# Create the database engine
engine = create_engine(DATABASE_URL)

# Create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the Base class (all models will inherit from this)
Base = declarative_base()

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()