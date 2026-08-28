import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Buyer, Invoice, Verification, Notification
from backend.schemas import VerificationCreate, VerificationResponse
from backend.auth.auth_service import get_current_user, require_role, verify_invoice_access
from backend.security.audit_logger import log_audit_event

router = APIRouter(prefix="/api/verification", tags=["Verification"])

@router.post("/verify", response_model=VerificationResponse)
def verify_invoice(
    verification_in: VerificationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["buyer", "admin"]))
):
    invoice = db.query(Invoice).filter(Invoice.id == verification_in.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Enforce Object-Level Access Control (IDOR Prevention)
    verify_invoice_access(invoice, current_user, db)

    buyer = db.query(Buyer).filter(Buyer.user_id == current_user.id).first()
    if not buyer and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only assigned buyer can verify invoices")
    
    buyer_id = buyer.id if buyer else invoice.buyer_id

    existing_ver = db.query(Verification).filter(Verification.invoice_id == invoice.id).first()
    if existing_ver:
        raise HTTPException(status_code=400, detail="Invoice already verified")

    v_hash_str = f"VERIFY:{invoice.id}:{verification_in.is_valid}:{datetime.utcnow().isoformat()}"
    v_hash = hashlib.sha256(v_hash_str.encode()).hexdigest()

    verification = Verification(
        invoice_id=invoice.id,
        buyer_id=buyer_id,
        verified_by_user_id=current_user.id,
        is_valid=verification_in.is_valid,
        verification_hash=v_hash,
        buyer_comments=verification_in.buyer_comments
    )
    db.add(verification)

    if verification_in.is_valid:
        invoice.status = "VERIFIED"
        if invoice.supplier and invoice.supplier.user_id:
            notif = Notification(
                user_id=invoice.supplier.user_id,
                title="Invoice Verified by Buyer",
                message=f"Your invoice #{invoice.invoice_number} has been verified and is ready for financing offers.",
                category="VERIFICATION"
            )
            db.add(notif)
    else:
        invoice.status = "REJECTED"

    db.commit()
    db.refresh(verification)

    client_ip = request.client.host if request.client else "127.0.0.1"
    log_audit_event(
        db,
        action="INVOICE_VERIFIED" if verification_in.is_valid else "INVOICE_DISPUTED",
        user_id=current_user.id,
        resource_type="Invoice",
        resource_id=invoice.id,
        ip_address=client_ip,
        details={"invoice_number": invoice.invoice_number, "is_valid": verification_in.is_valid}
    )

    return verification

@router.get("/invoice/{invoice_id}", response_model=VerificationResponse)
def get_verification_for_invoice(invoice_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    verify_invoice_access(invoice, current_user, db)

    ver = db.query(Verification).filter(Verification.invoice_id == invoice.id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Verification record not found for this invoice")
    return ver
