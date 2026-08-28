import csv
import io
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Invoice, Transaction
from backend.auth.auth_service import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Financial Reports"])

@router.get("/export-csv")
def export_financial_report_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates downloadable CSV financial ledger reports for SAP, QuickBooks, and Xero ERP integration."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Write Header
    writer.writerow([
        "Invoice ID",
        "Invoice Number",
        "Supplier",
        "Buyer",
        "Amount (USD)",
        "Status",
        "Issue Date",
        "Due Date",
        "Document SHA256 Hash",
        "Exported By"
    ])

    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    for inv in invoices:
        writer.writerow([
            inv.id,
            inv.invoice_number,
            inv.supplier.company_name if inv.supplier else "N/A",
            inv.buyer.company_name if inv.buyer else "N/A",
            f"{inv.amount:.2f}",
            inv.status,
            inv.issue_date,
            inv.due_date,
            inv.document_hash or "N/A",
            current_user.email
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scf_nexus_financial_ledger.csv"}
    )
