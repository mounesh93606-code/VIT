from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Financier, Invoice, Offer, Notification, Supplier
from backend.schemas import OfferCreate, OfferResponse
from backend.auth.auth_service import get_current_user, require_role, verify_offer_access
from backend.security.audit_logger import log_audit_event

router = APIRouter(prefix="/api/offers", tags=["Offers"])

@router.post("/generate", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def generate_offer(
    offer_in: OfferCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["financier", "admin"]))
):
    invoice = db.query(Invoice).filter(Invoice.id == offer_in.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    if invoice.status not in ["VERIFIED", "OFFER_EXTENDED"]:
        raise HTTPException(status_code=400, detail="Offers can only be created for VERIFIED invoices")

    financier = db.query(Financier).filter(Financier.user_id == current_user.id).first()
    if not financier and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only financiers can generate offers")

    financier_id = financier.id if financier else db.query(Financier).first().id

    offered_amt = round(invoice.amount * (1.0 - (offer_in.discount_rate_pct / 100.0)), 2)
    expires_at = datetime.utcnow() + timedelta(hours=offer_in.expires_in_hours)

    offer = Offer(
        invoice_id=invoice.id,
        financier_id=financier_id,
        requested_amount=invoice.amount,
        offered_amount=offered_amt,
        discount_rate_pct=offer_in.discount_rate_pct,
        apr_pct=offer_in.apr_pct,
        tenor_days=offer_in.tenor_days,
        status="EXTENDED",
        expires_at=expires_at
    )
    db.add(offer)
    
    invoice.status = "OFFER_EXTENDED"

    if invoice.supplier and invoice.supplier.user_id:
        notif = Notification(
            user_id=invoice.supplier.user_id,
            title="New Financing Offer Received",
            message=f"Financier {financier.institution_name if financier else 'Financier'} offered ${offered_amt:,.2f} ({offer_in.discount_rate_pct}% discount) for invoice #{invoice.invoice_number}.",
            category="OFFER"
        )
        db.add(notif)

    db.commit()
    db.refresh(offer)

    client_ip = request.client.host if request.client else "127.0.0.1"
    log_audit_event(
        db,
        action="OFFER_CREATED",
        user_id=current_user.id,
        resource_type="Offer",
        resource_id=offer.id,
        ip_address=client_ip,
        details={"offered_amount": offer.offered_amount, "apr_pct": offer.apr_pct}
    )

    res = OfferResponse.model_validate(offer)
    res.financier_name = financier.institution_name if financier else "Financier"
    return res

@router.get("", response_model=List[OfferResponse])
def get_offers(
    invoice_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Offer)
    
    if current_user.role == "financier":
        financier = db.query(Financier).filter(Financier.user_id == current_user.id).first()
        if financier:
            query = query.filter(Offer.financier_id == financier.id)
        else:
            return []
    elif current_user.role == "supplier":
        supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
        if supplier:
            query = query.join(Invoice).filter(Invoice.supplier_id == supplier.id)
        else:
            return []

    if invoice_id:
        query = query.filter(Offer.invoice_id == invoice_id)

    offers = query.order_by(Offer.created_at.desc()).all()
    
    res_list = []
    for o in offers:
        item = OfferResponse.model_validate(o)
        if o.financier:
            item.financier_name = o.financier.institution_name
        res_list.append(item)

    return res_list

@router.post("/{offer_id}/accept", response_model=OfferResponse)
def accept_offer(
    offer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["supplier", "admin"]))
):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Enforce Object-Level Access Control (IDOR Defense)
    verify_offer_access(offer, current_user, db)

    if offer.status != "EXTENDED":
        raise HTTPException(status_code=400, detail=f"Offer is not in EXTENDED state (current: {offer.status})")

    offer.status = "ACCEPTED"
    offer.invoice.status = "FINANCING_APPROVED"

    if offer.financier and offer.financier.user_id:
        notif = Notification(
            user_id=offer.financier.user_id,
            title="Offer Accepted by Supplier",
            message=f"Supplier accepted financing terms of ${offer.offered_amount:,.2f} for invoice #{offer.invoice.invoice_number}.",
            category="OFFER"
        )
        db.add(notif)

    db.commit()
    db.refresh(offer)

    client_ip = request.client.host if request.client else "127.0.0.1"
    log_audit_event(
        db,
        action="OFFER_ACCEPTED",
        user_id=current_user.id,
        resource_type="Offer",
        resource_id=offer.id,
        ip_address=client_ip,
        details={"invoice_id": offer.invoice_id, "amount": offer.offered_amount}
    )

    res = OfferResponse.model_validate(offer)
    if offer.financier:
        res.financier_name = offer.financier.institution_name
    return res
