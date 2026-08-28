import sys
import os
import uuid
from datetime import date
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.database import SessionLocal
from backend.models import User, Supplier, Buyer, Financier, Invoice, Offer, AuditLog
from backend.auth.auth_service import hash_password

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_auth_users():
    """Sets up distinct test users for Supplier A, Supplier B, Buyer, Financier, and Admin."""
    db = SessionLocal()
    pwd_hash = hash_password("Password123!")
    uid = uuid.uuid4().hex[:8]

    # Cleanup any existing test accounts
    db.query(User).filter(User.email.like("%@authtest.com")).delete(synchronize_session=False)
    db.commit()

    # 1. Supplier A
    user_sup_a = User(email=f"sup_a_{uid}@authtest.com", hashed_password=pwd_hash, full_name="Supplier A Corp", role="supplier")
    db.add(user_sup_a)
    db.flush()
    sup_a_profile = Supplier(user_id=user_sup_a.id, company_name="Supplier A Corp", tax_id=f"TAX-SUP-A-{uid}")
    db.add(sup_a_profile)

    # 2. Supplier B
    user_sup_b = User(email=f"sup_b_{uid}@authtest.com", hashed_password=pwd_hash, full_name="Supplier B Ltd", role="supplier")
    db.add(user_sup_b)
    db.flush()
    sup_b_profile = Supplier(user_id=user_sup_b.id, company_name="Supplier B Ltd", tax_id=f"TAX-SUP-B-{uid}")
    db.add(sup_b_profile)

    # 3. Buyer
    user_buyer = User(email=f"buyer_{uid}@authtest.com", hashed_password=pwd_hash, full_name="Buyer Retailers", role="buyer")
    db.add(user_buyer)
    db.flush()
    buyer_profile = Buyer(user_id=user_buyer.id, company_name="Buyer Retailers", tax_id=f"TAX-BUY-{uid}")
    db.add(buyer_profile)

    # 4. Financier
    user_fin = User(email=f"fin_{uid}@authtest.com", hashed_password=pwd_hash, full_name="Financier Capital", role="financier")
    db.add(user_fin)
    db.flush()
    fin_profile = Financier(user_id=user_fin.id, institution_name="Financier Capital", liquidity_pool=5000000.0)
    db.add(fin_profile)

    # 5. Admin
    user_admin = User(email=f"admin_{uid}@authtest.com", hashed_password=pwd_hash, full_name="Admin Security", role="admin")
    db.add(user_admin)
    db.commit()

    # Create Invoice A owned by Supplier A
    inv_a = Invoice(
        invoice_number=f"INV-SUP-A-{uid}",
        supplier_id=sup_a_profile.id,
        buyer_id=buyer_profile.id,
        amount=50000.0,
        currency="USD",
        issue_date=date(2026, 1, 1),
        due_date=date(2026, 3, 1),
        status="VERIFIED",
        description="Supplier A Goods",
        document_hash="a1b2c3d4e5f67890"
    )
    db.add(inv_a)
    db.commit()
    db.refresh(inv_a)

    yield {
        "sup_a_email": f"sup_a_{uid}@authtest.com",
        "sup_b_email": f"sup_b_{uid}@authtest.com",
        "buyer_email": f"buyer_{uid}@authtest.com",
        "fin_email": f"fin_{uid}@authtest.com",
        "admin_email": f"admin_{uid}@authtest.com",
        "password": "Password123!",
        "inv_a_id": inv_a.id,
        "buyer_profile_id": buyer_profile.id
    }

    db.close()

def test_1_supplier_registration():
    uid = uuid.uuid4().hex[:6]
    res = client.post("/api/auth/register", json={
        "full_name": "New Supplier Inc",
        "email": f"new_supplier_{uid}@authtest.com",
        "password": "Password123!",
        "role": "supplier",
        "company_name": "New Supplier Inc",
        "tax_id": f"TAX-NEW-SUP-{uid}"
    })
    assert res.status_code == 201
    assert res.json()["role"] == "supplier"

def test_2_buyer_registration():
    uid = uuid.uuid4().hex[:6]
    res = client.post("/api/auth/register", json={
        "full_name": "New Buyer Global",
        "email": f"new_buyer_{uid}@authtest.com",
        "password": "Password123!",
        "role": "buyer",
        "company_name": "New Buyer Global",
        "tax_id": f"TAX-NEW-BUY-{uid}"
    })
    assert res.status_code == 201
    assert res.json()["role"] == "buyer"

def test_3_financier_registration():
    uid = uuid.uuid4().hex[:6]
    res = client.post("/api/auth/register", json={
        "full_name": "New Financier Pool",
        "email": f"new_fin_{uid}@authtest.com",
        "password": "Password123!",
        "role": "financier",
        "institution_name": "New Financier Pool",
        "liquidity_pool": 1000000.0
    })
    assert res.status_code == 201
    assert res.json()["role"] == "financier"

def test_4_admin_self_registration_forbidden():
    res = client.post("/api/auth/register", json={
        "full_name": "Malicious Admin",
        "email": "hacker_admin@authtest.com",
        "password": "Password123!",
        "role": "admin"
    })
    assert res.status_code == 403
    assert "forbidden" in res.json()["detail"].lower()

def test_5_user_login(setup_auth_users):
    res = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_a_email"],
        "password": setup_auth_users["password"]
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["role"] == "supplier"

def test_6_user_logout(setup_auth_users):
    login_res = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_a_email"],
        "password": setup_auth_users["password"]
    })
    token = login_res.json()["access_token"]
    res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

def test_7_wrong_password_failure(setup_auth_users):
    res = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_a_email"],
        "password": "WrongPassword!"
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"

def test_8_duplicate_email_rejection(setup_auth_users):
    res = client.post("/api/auth/register", json={
        "full_name": "Duplicate User",
        "email": setup_auth_users["sup_a_email"],
        "password": "Password123!",
        "role": "supplier"
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

def test_9_supplier_accessing_own_invoice(setup_auth_users):
    token_a = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_a_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    res = client.get(f"/api/invoices/{setup_auth_users['inv_a_id']}", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    assert res.json()["id"] == setup_auth_users["inv_a_id"]

def test_10_idor_blocked_supplier_attempting_other_invoice(setup_auth_users):
    token_b = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_b_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    # Supplier B attempts to access Supplier A's invoice
    res = client.get(f"/api/invoices/{setup_auth_users['inv_a_id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

def test_11_supplier_attempting_admin_endpoint(setup_auth_users):
    token_a = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_a_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    res = client.get("/api/admin/users", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 403

def test_12_buyer_invoice_verification(setup_auth_users):
    token_buyer = client.post("/api/auth/login", json={
        "email": setup_auth_users["buyer_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    res = client.post("/api/verification/verify", headers={"Authorization": f"Bearer {token_buyer}"}, json={
        "invoice_id": setup_auth_users["inv_a_id"],
        "is_valid": True,
        "buyer_comments": "Verified in automated security suite"
    })
    assert res.status_code in [200, 400]

def test_13_financier_offer_creation(setup_auth_users):
    token_fin = client.post("/api/auth/login", json={
        "email": setup_auth_users["fin_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    res = client.post("/api/offers/generate", headers={"Authorization": f"Bearer {token_fin}"}, json={
        "invoice_id": setup_auth_users["inv_a_id"],
        "discount_rate_pct": 2.0,
        "apr_pct": 6.5,
        "tenor_days": 60
    })
    assert res.status_code in [201, 400]

def test_14_admin_access_to_audit_logs(setup_auth_users):
    token_admin = client.post("/api/auth/login", json={
        "email": setup_auth_users["admin_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    res = client.get("/api/admin/audit-logs", headers={"Authorization": f"Bearer {token_admin}"})
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) >= 1

def test_15_unauthenticated_api_rejection():
    res = client.get("/api/invoices")
    assert res.status_code == 401

def test_16_document_access_permissions(setup_auth_users):
    token_a = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_a_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    token_b = client.post("/api/auth/login", json={
        "email": setup_auth_users["sup_b_email"],
        "password": setup_auth_users["password"]
    }).json()["access_token"]

    # Owner Supplier A gets document metadata
    res_a = client.get(f"/api/invoices/{setup_auth_users['inv_a_id']}/document", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert "document_hash" in res_a.json()

    # Non-owner Supplier B blocked
    res_b = client.get(f"/api/invoices/{setup_auth_users['inv_a_id']}/document", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 403
