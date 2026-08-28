import math
from typing import Dict, Any, List

class OfferAgent:
    """AI Agent responsible for dynamic terms calculation, multi-criteria offer evaluation, and institutional yield math (Actual/365, EAR, NPV)."""

    def calculate_terms(
        self,
        invoice_amount: float,
        tenor_days: int,
        risk_score: float,
        advance_rate_pct: float = 90.0,
        origination_fee_pct: float = 0.5,
        day_count_convention: str = "ACTUAL_365"
    ) -> Dict[str, Any]:
        """Calculates dynamic institutional financial terms using Actual/365 day-count conventions and Effective Annual Rate (EAR)."""
        base_annual_rate = 5.5 + (risk_score * 0.12)
        day_count_base = 365.0 if day_count_convention == "ACTUAL_365" else 360.0
        
        # Daily discount rate = (APR / Base) * Tenor
        discount_rate_pct = round((base_annual_rate / day_count_base) * tenor_days, 2)
        
        # Effective Annual Rate (EAR) = (1 + APR/365)^365 - 1
        ear_pct = round(((1.0 + ((base_annual_rate / 100.0) / day_count_base)) ** day_count_base - 1.0) * 100.0, 2)

        gross_advancement = invoice_amount * (advance_rate_pct / 100.0)
        discount_amount = gross_advancement * (discount_rate_pct / 100.0)
        fee_amount = invoice_amount * (origination_fee_pct / 100.0)
        
        offered_amount = round(gross_advancement - discount_amount - fee_amount, 2)
        net_yield = round(invoice_amount - offered_amount, 2)

        return {
            "invoice_amount": invoice_amount,
            "tenor_days": tenor_days,
            "advance_rate_pct": advance_rate_pct,
            "calculated_apr_pct": round(base_annual_rate, 2),
            "effective_annual_rate_ear_pct": ear_pct,
            "day_count_convention": day_count_convention,
            "discount_rate_pct": discount_rate_pct,
            "fee_amount": round(fee_amount, 2),
            "offered_amount": offered_amount,
            "financier_projected_yield": net_yield
        }

    def evaluate_suitability(
        self,
        invoice_amount: float,
        requested_amount: float,
        tenor_days: int,
        preferred_tenor: int,
        urgency: str,
        offered_amount: float,
        apr_pct: float,
        advance_rate_pct: float,
        financier_liquidity: float,
        financier_max_risk: float,
        calculated_risk_score: float,
        financier_name: str
    ) -> Dict[str, Any]:
        """Evaluates offer suitability (0-100 score) using multi-criteria weighted matrix with explainability reasons."""
        reasons: List[str] = []
        score = 0.0

        # 1. Amount Satisfaction Score (Weight: 25%)
        amount_coverage = min(1.0, offered_amount / max(1.0, requested_amount))
        amount_score = amount_coverage * 25.0
        score += amount_score
        if amount_coverage >= 0.95:
            reasons.append(f"Required amount fully satisfied (${offered_amount:,.2f} vs requested ${requested_amount:,.2f})")
        else:
            reasons.append(f"Partial amount coverage ({round(amount_coverage * 100, 1)}% of requested amount)")

        # 2. Advance Rate Score (Weight: 20%)
        advance_score = (advance_rate_pct / 100.0) * 20.0
        score += advance_score
        if advance_rate_pct >= 85.0:
            reasons.append(f"High advance rate ({advance_rate_pct}%) minimizes supplier capital lockup")

        # 3. Pricing / Cost Competitiveness Score (Weight: 20%)
        apr_diff = max(0.0, 12.0 - apr_pct)
        pricing_score = min(20.0, (apr_diff / 8.0) * 20.0)
        score += pricing_score
        if apr_pct <= 7.5:
            reasons.append(f"Highly competitive financing cost (APR {apr_pct}%)")
        else:
            reasons.append(f"Acceptable financing cost (APR {apr_pct}%)")

        # 4. Tenure & Urgency Alignment Score (Weight: 20%)
        tenor_diff = abs(tenor_days - preferred_tenor)
        tenor_score = max(0.0, 20.0 - (tenor_diff * 0.3))
        score += tenor_score
        if tenor_diff <= 10:
            reasons.append(f"Preferred financing tenure matched ({tenor_days} days)")

        if urgency.upper() in ["HIGH", "URGENT"]:
            reasons.append("Fast automated settlement dispatch enabled for urgent financing request")

        # 5. Financier Capacity & Policy Fit (Weight: 15%)
        has_liquidity = financier_liquidity >= offered_amount
        risk_within_limit = calculated_risk_score <= financier_max_risk
        
        policy_score = 15.0 if (has_liquidity and risk_within_limit) else 5.0
        score += policy_score

        if has_liquidity:
            reasons.append(f"{financier_name} has sufficient active liquidity pool (${financier_liquidity:,.2f})")
        if risk_within_limit:
            reasons.append(f"Invoice risk profile ({calculated_risk_score}%) satisfies financier policy limit ({financier_max_risk}%)")

        final_suitability_score = round(max(0.0, min(100.0, score)), 1)

        return {
            "suitability_score": final_suitability_score,
            "financier_name": financier_name,
            "reasons": reasons,
            "score_breakdown": {
                "amount_satisfaction": round(amount_score, 1),
                "advance_rate": round(advance_score, 1),
                "pricing_cost": round(pricing_score, 1),
                "tenor_urgency": round(tenor_score, 1),
                "policy_capacity": round(policy_score, 1)
            }
        }

offer_agent = OfferAgent()
