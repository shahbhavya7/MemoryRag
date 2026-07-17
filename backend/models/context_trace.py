from sqlalchemy import Column, DateTime, Integer, Text, func

from backend.database.session import Base


class ContextTrace(Base):
    __tablename__ = "context_traces"

    id = Column(Integer, primary_key=True, index=True)
    # The assistant message this trace explains (the answer that used this context).
    message_id = Column(Integer, nullable=False, index=True)
    # The full trace, stored as JSON text (kept/dropped chunks + token breakdown).
    trace_json = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
