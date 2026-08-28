# Re-export core database models from database/models/ for backward compatibility
from database.models import (
    User,
    Supplier,
    Buyer,
    Financier,
    Invoice,
    Verification,
    RiskAssessment,
    Offer,
    MatchRecommendation,
    Transaction,
    Notification,
    AuditLog,
    generate_uuid
)

__all__ = [
    "User",
    "Supplier",
    "Buyer",
    "Financier",
    "Invoice",
    "Verification",
    "RiskAssessment",
    "Offer",
    "MatchRecommendation",
    "Transaction",
    "Notification",
    "AuditLog",
    "generate_uuid"
]
