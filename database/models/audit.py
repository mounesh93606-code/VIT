import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from database.connection.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True) # LOGIN_SUCCESS, LOGIN_FAILED, INVOICE_SUBMITTED, etc.
    resource_type = Column(String(50), nullable=True)        # User, Invoice, Offer, Transaction, Verification
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    details_json = Column(Text, nullable=True)               # Non-sensitive JSON details
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
