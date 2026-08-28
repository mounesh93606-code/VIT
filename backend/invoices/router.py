import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Supplier, Buyer, Invoice, Notification
from backend.schemas import InvoiceCreate, InvoiceResponse, InvoiceStatusUpdate
from backend.auth.auth_service import get_current_user, require_role, verify_invoice_access
from backend.security.audit_logger import log_audit_event
from ai.invoice_agent.agent import invoice_agent

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

@router.post("/upload-document", response_model=dict)
async def upload_and_parse_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["supplier", "admin"]))
):
    """File Upload Endpoint: Accepts raw document files (PDF/txt), calculates cryptographic SHA-256 fingerprint, and extracts structured invoice fields."""
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024: # 5MB limit
        raise HTTPException(status_code=413, detail="File size exceeds maximum 5MB limit")
    
    parsed_metadata = invoice_agent.parse_document_buffer(file_bytes, file.filename)
    return parsed_metadata

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    invoice_in: InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["supplier", "admin"]))
):
    supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
    if not supplier and current_user.role != "admin":
        raise HTTPException(status_code=404, detail="Supplier profile not found")

    supplier_id = supplier.id if supplier else db.query(Supplier).first().id

    buyer = db.query(Buyer).filter(Buyer.id == invoice_in.buyer_id).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Selected buyer not found")

    client_ip = request.client.host if request.client else "127.0.0.1"

    # Anti-Double-Financing Fingerprint Check
    doc_hash_str = f"{invoice_in.invoice_number}:{invoice_in.amount}:{invoice_in.due_date}"
    doc_hash = hashlib.sha256(doc_hash_str.encode()).hexdigest()

    existing_inv_num = db.query(Invoice).filter(Invoice.invoice_number == invoice_in.invoice_number).first()
    existing_doc_hash = db.query(Invoice).filter(Invoice.document_hash == doc_hash).first()

    if existing_inv_num or existing_doc_hash:
        log_audit_event(
            db,
            action="FRAUD_ALERT_DOUBLE_FINANCING",
            user_id=current_user.id,
            resource_type="Invoice",
            resource_id=invoice_in.invoice_number,
            ip_address=client_ip,
            details={
                "attempted_invoice_number": invoice_in.invoice_number,
                "amount": invoice_in.amount,
                "reason": "Duplicate invoice submission / Double-financing attack attempt detected"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Anti-Fraud Alert: Double-financing attack detected. Invoice or document fingerprint already exists in platform ledger."
        )

    invoice = Invoice(
        invoice_number=invoice_in.invoice_number,
        supplier_id=supplier_id,
        buyer_id=invoice_in.buyer_id,
        amount=invoice_in.amount,
        currency=invoice_in.currency,
        issue_date=invoice_in.issue_date,
        due_date=invoice_in.due_date,
        status="PENDING_VERIFICATION",
        description=invoice_in.description,
        document_hash=doc_hash
    )
    db.add(invoice)
    db.flush()

    # Notify Buyer
    if buyer.user_id:
        notification = Notification(
            user_id=buyer.user_id,
            title="New Invoice Submitted",
            message=f"Supplier {supplier.company_name if supplier else 'Supplier'} submitted invoice #{invoice.invoice_number} for verification.",
            category="INVOICE"
        )
        db.add(notification)

    db.commit()
    db.refresh(invoice)

    log_audit_event(
        db,
        action="INVOICE_SUBMITTED",
        user_id=current_user.id,
        resource_type="Invoice",
        resource_id=invoice.id,
        ip_address=client_ip,
        details={"invoice_number": invoice.invoice_number, "amount": invoice.amount}
    )

    res = InvoiceResponse.model_validate(invoice)
    res.supplier_company_name = supplier.company_name if supplier else "Supplier"
    res.buyer_company_name = buyer.company_name
    return res

@router.get("", response_model=List[InvoiceResponse])
def get_invoices(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Invoice)
    
    if current_user.role == "supplier":
        supplier = db.query(Supplier).filter(Supplier.user_id == current_user.id).first()
        if supplier:
            query = query.filter(Invoice.supplier_id == supplier.id)
        else:
            return []
    elif current_user.role == "buyer":
        buyer = db.query(Buyer).filter(Buyer.user_id == current_user.id).first()
        if buyer:
            query = query.filter(Invoice.buyer_id == buyer.id)
        else:
            return []
    elif current_user.role == "financier":
        query = query.filter(Invoice.status.in_(["VERIFIED", "OFFER_EXTENDED", "FINANCED", "SETTLED"]))

    if status_filter:
        query = query.filter(Invoice.status == status_filter)

    invoices = query.order_by(Invoice.created_at.desc()).all()
    
    res_list = []
    for inv in invoices:
        item = InvoiceResponse.model_validate(inv)
        if inv.supplier:
            item.supplier_company_name = inv.supplier.company_name
        if inv.buyer:
            item.buyer_company_name = inv.buyer.company_name
        res_list.append(item)
        
    return res_list

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice_by_id(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    verify_invoice_access(invoice, current_user, db)

    res = InvoiceResponse.model_validate(invoice)
    if invoice.supplier:
        res.supplier_company_name = invoice.supplier.company_name
    if invoice.buyer:
        res.buyer_company_name = invoice.buyer.company_name
    return res

@router.get("/{invoice_id}/document", response_model=dict)
def get_invoice_document(
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Secure Document Access Endpoint: Verifies ownership before exposing document cryptographic metadata."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    verify_invoice_access(invoice, current_user, db)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "document_hash": invoice.document_hash,
        "verification_status": invoice.status,
        "authorized_viewer": current_user.email,
        "role": current_user.role
    }

@router.patch("/{invoice_id}/status", response_model=InvoiceResponse)
def update_invoice_status(
    invoice_id: str,
    status_in: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    verify_invoice_access(invoice, current_user, db)
    
    invoice.status = status_in.status
    db.commit()
    db.refresh(invoice)

    res = InvoiceResponse.model_validate(invoice)
    if invoice.supplier:
        res.supplier_company_name = invoice.supplier.company_name
    if invoice.buyer:
        res.buyer_company_name = invoice.buyer.company_name
    return res
