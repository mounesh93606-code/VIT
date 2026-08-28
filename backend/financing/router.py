import hashlib
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Financier, Supplier, Invoice, Offer, Transaction, Notification
from backend.schemas import DisbursementRequest, TransactionResponse
from backend.auth.auth_service import get_current_user, require_role, verify_offer_access
from backend.security.audit_logger import log_audit_event

router = APIRouter(prefix="/api/financing", tags=["Financing Disbursement"])

@router.post("/disburse", response_model=TransactionResponse)
def disburse_funds(
    req: DisbursementRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["financier", "admin"]))
):
    offer = db.query(Offer).filter(Offer.id == req.offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    verify_offer_access(offer, current_user, db)

    if offer.status != "ACCEPTED":
        raise HTTPException(status_code=400, detail="Disbursement requires accepted offer status")

    invoice = offer.invoice
    financier = offer.financier
    supplier = invoice.supplier

    if financier.liquidity_pool < offer.offered_amount:
        raise HTTPException(status_code=400, detail="Insufficient liquidity pool in financier account")

    tx_str = f"DISBURSE:{offer.id}:{offer.offered_amount}:{datetime.utcnow().isoformat()}"
    tx_hash = hashlib.sha256(tx_str.encode()).hexdigest()

    transaction = Transaction(
        invoice_id=invoice.id,
        offer_id=offer.id,
        transaction_type="DISBURSEMENT",
        amount=offer.offered_amount,
        sender_account=f"ACH_WIRE_ROUTING_{financier.id[:8].upper()}",
        recipient_account=req.recipient_account,
        transaction_hash=tx_hash,
        status="COMPLETED"
    )
    db.add(transaction)

    # Update ledger
    financier.liquidity_pool -= offer.offered_amount
    supplier.total_funded_amount += offer.offered_amount
    invoice.status = "FINANCED"
    offer.status = "DISBURSED"

    if supplier.user_id:
        db.add(Notification(
            user_id=supplier.user_id,
            title="Funds Disbursed to Your Bank Account",
            message=f"Bank ACH transfer of ${offer.offered_amount:,.2f} executed for invoice #{invoice.invoice_number}. ACH Tx Hash: {tx_hash[:16]}...",
            category="FINANCING"
        ))

    db.commit()
    db.refresh(transaction)

    client_ip = request.client.host if request.client else "127.0.0.1"
    log_audit_event(
        db,
        action="FINANCING_DISBURSED",
        user_id=current_user.id,
        resource_type="Transaction",
        resource_id=transaction.id,
        ip_address=client_ip,
        details={"disbursed_amount": offer.offered_amount, "recipient": req.recipient_account, "tx_hash": tx_hash}
    )

    return transaction

@router.get("/transactions", response_model=List[TransactionResponse])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    txs = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return txs
