import sys
import os
import io
import uuid
import pytest
from datetime import date
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.database import SessionLocal
from backend.models import User, Supplier, Buyer, Invoice
from backend.auth.auth_service import hash_password
from ai.offer_agent.agent import offer_agent

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_enterprise_context():
    db = SessionLocal()
    pwd_hash = hash_password("Password123!")
    uid = uuid.uuid4().hex[:8]

    # Create supplier
    user_sup = User(email=f"ent_sup_{uid}@enterprise.com", hashed_password=pwd_hash, full_name="Enterprise Supplier", role="supplier")
    db.add(user_sup)
    db.flush()
    sup_profile = Supplier(user_id=user_sup.id, company_name="Enterprise Supplier", tax_id=f"TAX-ENT-SUP-{uid}")
    db.add(sup_profile)

    # Create buyer
    user_buyer = User(email=f"ent_buyer_{uid}@enterprise.com", hashed_password=pwd_hash, full_name="Enterprise Buyer", role="buyer")
    db.add(user_buyer)
    db.flush()
    buyer_profile = Buyer(user_id=user_buyer.id, company_name="Enterprise Buyer", tax_id=f"TAX-ENT-BUY-{uid}")
    db.add(buyer_profile)

    db.commit()

    # Login to get token
    token = client.post("/api/auth/login", json={
        "email": f"ent_sup_{uid}@enterprise.com",
        "password": "Password123!"
    }).json()["access_token"]

    yield {
        "token": token,
        "buyer_id": buyer_profile.id,
        "supplier_tax_id": f"TAX-ENT-SUP-{uid}",
        "uid": uid
    }
    db.close()

def test_1_file_upload_document_parsing(setup_enterprise_context):
    token = setup_enterprise_context["token"]
    dummy_invoice_pdf = b"INVOICE INV-PDF-2026-909 Amount $125,000.00 Net 60 TAX-PDF-TEST-99"
    
    file_payload = ("test_invoice.pdf", io.BytesIO(dummy_invoice_pdf), "application/pdf")
    res = client.post("/api/invoices/upload-document", headers={"Authorization": f"Bearer {token}"}, files={"file": file_payload})
    
    assert res.status_code == 200
    data = res.json()
    assert data["parsed_invoice_number"] == "INV-PDF-2026-909"
    assert data["parsed_amount"] == 125000.0
    assert data["extracted_tax_id"] == "TAX-PDF-TEST-99"
    assert "sha256_fingerprint" in data

def test_2_double_financing_fraud_prevention(setup_enterprise_context):
    token = setup_enterprise_context["token"]
    buyer_id = setup_enterprise_context["buyer_id"]
    inv_number = f"INV-FRAUD-CHECK-{setup_enterprise_context['uid']}"

    # 1. First submission succeeds
    res1 = client.post("/api/invoices", headers={"Authorization": f"Bearer {token}"}, json={
        "invoice_number": inv_number,
        "buyer_id": buyer_id,
        "amount": 75000.0,
        "currency": "USD",
        "issue_date": "2026-01-01",
        "due_date": "2026-03-01",
        "description": "Legitimate Submission"
    })
    assert res1.status_code == 201

    # 2. Duplicate submission triggers anti-double-financing HTTP 409 Conflict
    res2 = client.post("/api/invoices", headers={"Authorization": f"Bearer {token}"}, json={
        "invoice_number": inv_number,
        "buyer_id": buyer_id,
        "amount": 75000.0,
        "currency": "USD",
        "issue_date": "2026-01-01",
        "due_date": "2026-03-01",
        "description": "Duplicate Double Financing Fraud Attempt"
    })
    assert res2.status_code == 409
    assert "Double-financing attack detected" in res2.json()["detail"]

def test_3_institutional_ear_financial_terms():
    terms = offer_agent.calculate_terms(
        invoice_amount=100000.0,
        tenor_days=60,
        risk_score=15.0,
        advance_rate_pct=90.0,
        day_count_convention="ACTUAL_365"
    )
    assert "effective_annual_rate_ear_pct" in terms
    assert terms["day_count_convention"] == "ACTUAL_365"
    assert terms["effective_annual_rate_ear_pct"] >= terms["calculated_apr_pct"]
    assert terms["offered_amount"] < 100000.0

def test_4_csv_financial_report_export(setup_enterprise_context):
    token = setup_enterprise_context["token"]
    res = client.get("/api/reports/export-csv", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/csv; charset=utf-8"
    assert "Invoice Number" in res.text
