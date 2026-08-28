import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.models import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = "127.0.0.1",
    details: Optional[Dict[str, Any]] = None
):
    """Persists a security audit trail log entry into the database.
    NEVER records passwords, hashes, or sensitive secret tokens.
    """
    try:
        # Sanitize details to guarantee no password keys are saved
        sanitized_details = {}
        if details:
            for k, v in details.items():
                if any(secret_kw in k.lower() for secret_kw in ["password", "token", "secret", "key"]):
                    sanitized_details[k] = "[REDACTED]"
                else:
                    sanitized_details[k] = v

        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details_json=json.dumps(sanitized_details) if sanitized_details else None
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to record audit log: {e}")
