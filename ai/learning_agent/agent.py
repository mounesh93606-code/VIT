from typing import Dict, Any, List

class LearningAgent:
    """AI Agent responsible for feedback learning based on historical transaction outcomes and offer acceptances."""

    def __init__(self):
        self.feedback_log = []

    def record_offer_feedback(self, offer_id: str, financier_id: str, was_accepted: bool, feedback_notes: str = None) -> Dict[str, Any]:
        """Logs user choice on financing offers to refine future weightings."""
        record = {
            "offer_id": offer_id,
            "financier_id": financier_id,
            "was_accepted": was_accepted,
            "notes": feedback_notes
        }
        self.feedback_log.append(record)
        return {"status": "RECORDED", "total_feedback_logs": len(self.feedback_log)}

    def update_model_weights(self, historical_transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(historical_transactions)
        if total == 0:
            return {"status": "INSUFFICIENT_DATA", "weight_adjustment": 0.0, "feedback_count": len(self.feedback_log)}

        on_time_count = sum(1 for tx in historical_transactions if tx.get("status") == "SETTLED")
        success_rate = on_time_count / total

        # If success rate is high (>95%), reduce overall risk penalty by 2.5%
        adjustment = -2.5 if success_rate >= 0.95 else (5.0 if success_rate < 0.85 else 0.0)

        return {
            "historical_count": total,
            "repayment_success_rate": round(success_rate * 100, 1),
            "risk_weight_adjustment": adjustment,
            "feedback_count": len(self.feedback_log),
            "recommendation": "Maintain standard underwriting rules" if adjustment == 0 else "Refine credit policy"
        }

learning_agent = LearningAgent()
