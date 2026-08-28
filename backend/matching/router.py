import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Financier, Invoice, Supplier, Buyer, MatchRecommendation
from backend.schemas import InvoiceResponse
from backend.auth.auth_service import get_current_user
from backend.risk.router import compute_credit_risk
from ai.offer_agent import offer_agent

router = APIRouter(prefix="/api/matching", tags=["AI Matching"])

@router.get("/invoices/{financier_id}", response_model=List[dict])
def get_matched_invoices_for_financier(
    financier_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    financier = db.query(Financier).filter(Financier.id == financier_id).first()
    if not financier:
        # Fallback to financier linked to current user if requested
        financier = db.query(Financier).filter(Financier.user_id == current_user.id).first()
        if not financier:
            raise HTTPException(status_code=404, detail="Financier profile not found")

    # Fetch all verified invoices available for financing
    verified_invoices = db.query(Invoice).filter(Invoice.status.in_(["VERIFIED", "OFFER_EXTENDED"])).all()

    matches = []
    for inv in verified_invoices:
        supplier = inv.supplier
        buyer = inv.buyer
        
        tenor_days = max(1, (inv.due_date - inv.issue_date).days)
        risk = compute_credit_risk(supplier.risk_score, buyer.credit_rating, tenor_days, inv.amount)

        terms = offer_agent.calculate_terms(
            invoice_amount=inv.amount,
            tenor_days=tenor_days,
            risk_score=risk["risk_score"]
        )

        suitability = offer_agent.evaluate_suitability(
            invoice_amount=inv.amount,
            requested_amount=inv.amount,
            tenor_days=tenor_days,
            preferred_tenor=tenor_days,
            urgency="NORMAL",
            offered_amount=terms["offered_amount"],
            apr_pct=max(financier.min_acceptable_apr, terms["calculated_apr_pct"]),
            advance_rate_pct=terms["advance_rate_pct"],
            financier_liquidity=financier.liquidity_pool,
            financier_max_risk=financier.max_risk_tolerance,
            calculated_risk_score=risk["risk_score"],
            financier_name=financier.institution_name
        )

        is_eligible = (
            risk["risk_score"] <= financier.max_risk_tolerance and
            inv.amount <= financier.liquidity_pool
        )

        matches.append({
            "invoice": InvoiceResponse.model_validate(inv),
            "match_score": suitability["suitability_score"],
            "suitability_score": suitability["suitability_score"],
            "is_eligible": is_eligible,
            "calculated_risk_score": risk["risk_score"],
            "recommended_apr": max(financier.min_acceptable_apr, terms["calculated_apr_pct"]),
            "ai_match_rationale": f"Suitability Score {suitability['suitability_score']}/100: Risk level ({risk['risk_level']}) complies with policy.",
            "explainability_reasons": suitability["reasons"]
        })

    matches.sort(key=lambda x: x["suitability_score"], reverse=True)
    return matches
