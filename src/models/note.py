from sqlalchemy import BigInteger, Column, Date, ForeignKey, String, Text, text
from src.config.database import Base


# SQLAlchemy models map Python classes to the existing database tables.
class Note(Base):
    __tablename__ = "notes"

    note_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    note_date = Column(Date, nullable=False, server_default=text("CURRENT_DATE"))
