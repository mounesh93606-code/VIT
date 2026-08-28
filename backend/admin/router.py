from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, AuditLog
from backend.schemas import UserResponse
from backend.auth.auth_service import require_role
from backend.security.audit_logger import log_audit_event

router = APIRouter(prefix="/api/admin", tags=["Admin Operations"])

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    role_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    query = db.query(User)
    if role_filter:
        query = query.filter(User.role == role_filter.lower())
    return query.order_by(User.created_at.desc()).all()

@router.get("/audit-logs", response_model=List[dict])
def get_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "details": log.details_json,
            "created_at": log.created_at
        }
        for log in logs
    ]

@router.patch("/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: str,
    is_active: bool,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Target user not found")

    user.is_active = is_active
    db.commit()
    db.refresh(user)

    client_ip = request.client.host if request.client else "127.0.0.1"
    log_audit_event(
        db,
        action="ADMIN_USER_STATUS_UPDATED",
        user_id=current_user.id,
        resource_type="User",
        resource_id=user.id,
        ip_address=client_ip,
        details={"target_user": user.email, "is_active": is_active}
    )

    return user
