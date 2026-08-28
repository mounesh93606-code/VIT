from typing import List, Dict, Any
from ai.offer_agent.agent import offer_agent

class MatchingAgent:
    """AI Agent responsible for matching verified invoices with optimal financier liquidity pools using multi-criteria suitability scoring."""
    
    def find_best_financier(
        self,
        invoice_amount: float,
        requested_amount: float,
        tenor_days: int,
        preferred_tenor: int,
        urgency: str,
        risk_score: float,
        financiers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        scored_matches = []

        for f in financiers:
            terms = offer_agent.calculate_terms(
                invoice_amount=invoice_amount,
                tenor_days=tenor_days,
                risk_score=risk_score
            )

            suitability = offer_agent.evaluate_suitability(
                invoice_amount=invoice_amount,
                requested_amount=requested_amount,
                tenor_days=tenor_days,
                preferred_tenor=preferred_tenor,
                urgency=urgency,
                offered_amount=terms["offered_amount"],
                apr_pct=terms["calculated_apr_pct"],
                advance_rate_pct=terms["advance_rate_pct"],
                financier_liquidity=f.get("liquidity_pool", 0.0),
                financier_max_risk=f.get("max_risk_tolerance", 50.0),
                calculated_risk_score=risk_score,
                financier_name=f.get("institution_name", "Financier")
            )

            is_eligible = (
                f.get("liquidity_pool", 0.0) >= terms["offered_amount"] and
                risk_score <= f.get("max_risk_tolerance", 50.0)
            )

            scored_matches.append({
                "financier": f,
                "terms": terms,
                "suitability": suitability,
                "is_eligible": is_eligible,
                "suitability_score": suitability["suitability_score"]
            })

        scored_matches.sort(key=lambda x: x["suitability_score"], reverse=True)
        top_match = scored_matches[0] if scored_matches else None

        return {
            "top_match": top_match,
            "all_ranked_matches": scored_matches,
            "ai_matching_summary": f"Evaluated {len(financiers)} capital providers across multi-criteria suitability matrix."
        }

matching_agent = MatchingAgent()
