from sqlalchemy import BigInteger, Column, Text
from src.config.database import Base


# SQLAlchemy models keep table mapping separate from API schemas.
class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, index=True)
    user_name = Column(Text, nullable=False)
    user_email = Column(Text, nullable=False, unique=True, index=True)
