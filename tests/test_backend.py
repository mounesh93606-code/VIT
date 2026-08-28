import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from database.models import User, Supplier, Buyer, Financier, RiskAssessment, MatchRecommendation
from ai.offer_agent import offer_agent
from ai.invoice_agent import invoice_agent
from ai.risk_agent import risk_agent

client = TestClient(app)

def test_health_check_and_security_headers():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    # Verify OWASP Security Headers
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert "strict-transport-security" in response.headers

def test_system_stats():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_users"] >= 4
    assert data["total_suppliers"] >= 1

def test_user_login():
    response = client.post("/api/auth/login", json={
        "email": "supplier@apex.com",
        "password": "Password123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "supplier"

def test_invoices_retrieval():
    login_res = client.post("/api/auth/login", json={
        "email": "supplier@apex.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]

    response = client.get("/api/invoices", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    invoices = response.json()
    assert isinstance(invoices, list)
    assert len(invoices) >= 1

def test_ai_risk_evaluation_authenticated():
    login_res = client.post("/api/auth/login", json={
        "email": "supplier@apex.com",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]

    # Test unauthenticated access rejected
    unauth_response = client.post("/api/ai/evaluate-risk?supplier_score=20&buyer_rating=AA&amount=100000&tenor_days=60")
    assert unauth_response.status_code == 401

    # Test authenticated access succeeds
    response = client.post(
        "/api/ai/evaluate-risk?supplier_score=20&buyer_rating=AA&amount=100000&tenor_days=60",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "composite_risk_score" in data
    assert data["credit_decision"] in ["APPROVE", "MANUAL_REVIEW"]
    assert "demo_notice" in data

def test_ai_invoice_parse():
    sample_text = "Invoice <script>alert('xss')</script> INV-2026-888 for $150,000.00 from TAX-SUP-APEX-998 with Net 60 payment terms."
    res = invoice_agent.parse_invoice_text(sample_text)
    assert res["parsed_invoice_number"] == "INV-2026-888"
    assert res["parsed_amount"] == 150000.0
    assert res["verification_confidence"] >= 0.8
    assert res["verification_status"] == "AUTO_VERIFIED"

def test_ai_offer_suitability():
    suitability = offer_agent.evaluate_suitability(
        invoice_amount=100000.0,
        requested_amount=100000.0,
        tenor_days=60,
        preferred_tenor=60,
        urgency="HIGH",
        offered_amount=98000.0,
        apr_pct=6.5,
        advance_rate_pct=90.0,
        financier_liquidity=5000000.0,
        financier_max_risk=40.0,
        calculated_risk_score=20.0,
        financier_name="Horizon Capital Group"
    )
    assert suitability["suitability_score"] >= 80.0
    assert len(suitability["reasons"]) >= 4
    assert any("Required amount fully satisfied" in r for r in suitability["reasons"])
