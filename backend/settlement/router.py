import hashlib
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Buyer, Financier, Supplier, Invoice, Offer, Transaction, Notification
from backend.schemas import SettlementCreate, SettlementResponse
from backend.auth.auth_service import get_current_user, require_role

router = APIRouter(prefix="/api/settlement", tags=["Settlement & Maturity"])

@router.post("/settle", response_model=SettlementResponse)
def settle_invoice(
    settlement_in: SettlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["buyer", "admin"]))
):
    invoice = db.query(Invoice).filter(Invoice.id == settlement_in.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status != "FINANCED":
        raise HTTPException(status_code=400, detail="Settlement requires FINANCED invoice status")

    if settlement_in.payment_amount < invoice.amount:
        raise HTTPException(status_code=400, detail=f"Settlement payment must match full invoice amount (${invoice.amount:,.2f})")

    # Get active offer
    offer = db.query(Offer).filter(Offer.invoice_id == invoice.id, Offer.status == "DISBURSED").first()
    if not offer:
        raise HTTPException(status_code=404, detail="Active disbursed offer not found for this invoice")

    financier = offer.financier
    supplier = invoice.supplier
    buyer = invoice.buyer

    # Financial breakdown
    financier_payout = invoice.amount # Financier receives full invoice amount (earning the discount yield)
    supplier_rebate = 0.0             # Any extra rebate if applicable

    # Hash
    s_hash_str = f"SETTLE:{invoice.id}:{settlement_in.payment_amount}:{datetime.utcnow().isoformat()}"
    s_hash = hashlib.sha256(s_hash_str.encode()).hexdigest()

    # Record Repayment Transaction
    repayment_tx = Transaction(
        invoice_id=invoice.id,
        offer_id=offer.id,
        transaction_type="REPAYMENT",
        amount=invoice.amount,
        sender_account=settlement_in.payer_account,
        recipient_account=f"FINANCIER_POOL_{financier.id[:8].upper()}",
        transaction_hash=s_hash,
        status="COMPLETED"
    )
    db.add(repayment_tx)

    # Return capital + yield to financier liquidity pool
    financier.liquidity_pool += financier_payout
    invoice.status = "SETTLED"
    offer.status = "SETTLED"

    # Reduce buyer used credit limit
    if buyer and buyer.used_credit_limit >= invoice.amount:
        buyer.used_credit_limit -= invoice.amount

    # Send Notifications
    if financier.user_id:
        db.add(Notification(
            user_id=financier.user_id,
            title="Invoice Settled - Funds & Yield Received",
            message=f"Buyer paid full invoice amount ${invoice.amount:,.2f} for invoice #{invoice.invoice_number}. Yield returned to liquidity pool.",
            category="SETTLEMENT"
        ))

    if supplier.user_id:
        db.add(Notification(
            user_id=supplier.user_id,
            title="Invoice Lifecycle Complete",
            message=f"Buyer fully settled invoice #{invoice.invoice_number}. Transaction completed successfully.",
            category="SETTLEMENT"
        ))

    db.commit()

    return SettlementResponse(
        invoice_id=invoice.id,
        total_paid=invoice.amount,
        financier_payout=financier_payout,
        supplier_rebate=supplier_rebate,
        disbursement_hash=s_hash,
        status="SETTLED",
        settled_at=datetime.utcnow()
    )
