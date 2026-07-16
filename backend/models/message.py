from sqlalchemy import Column, DateTime, Integer, String, Text, func

from backend.database.session import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    # project_id is a logical grouping key, not a hard foreign key — this
    # matches how /documents/upload already treats project_id (a free-form tag
    # stored as vector metadata). Keeping it FK-free means /chat can log an
    # exchange for any project id without first requiring a real project row,
    # which is what Phase 4's simple {project_id, message} contract implies.
    project_id = Column(Integer, nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
