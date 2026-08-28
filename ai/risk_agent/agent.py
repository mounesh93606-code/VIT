import os
from typing import Dict, Any
import numpy as np
import pandas as pd

class RiskAgent:
    """AI Agent responsible for credit scoring, default probability estimation, and risk classification.
    Note: Hackathon prototype uses synthetic demo models trained on simulated supply chain datasets.
    """
    
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            import joblib
            model_path = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "risk_model", "risk_model.joblib")
            model_path = os.path.abspath(model_path)
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
        except Exception as e:
            self.model = None

    def evaluate_risk(
        self,
        supplier_history_score: float,
        buyer_credit_rating: str,
        invoice_amount: float,
        tenor_days: int
    ) -> Dict[str, Any]:
        """Calculates composite credit risk combining ML model prediction and domain financial rules."""
        rating_scores = {"AAA": 1, "AA": 2, "A": 3, "BBB": 4, "BB": 5, "B": 6}
        buyer_numeric = rating_scores.get(buyer_credit_rating.upper(), 4)

        if self.model:
            try:
                features = pd.DataFrame([{
                    "supplier_risk_score": supplier_history_score,
                    "buyer_rating_numeric": buyer_numeric,
                    "amount": invoice_amount,
                    "tenor_days": tenor_days
                }])
                default_prob = float(self.model.predict_proba(features)[0][1])
                composite_risk = round(default_prob * 100.0, 2)
            except Exception:
                base_buyer_risk = buyer_numeric * 8.0
                composite_risk = (base_buyer_risk * 0.50) + (supplier_history_score * 0.35) + min(tenor_days / 180.0 * 15, 15)
                composite_risk = round(max(5.0, min(95.0, composite_risk)), 2)
        else:
            base_buyer_risk = buyer_numeric * 8.0
            composite_risk = (base_buyer_risk * 0.50) + (supplier_history_score * 0.35) + min(tenor_days / 180.0 * 15, 15)
            composite_risk = round(max(5.0, min(95.0, composite_risk)), 2)

        if composite_risk < 30.0:
            credit_decision = "APPROVE"
            risk_level = "LOW"
            recommended_base_apr = 6.0 + (composite_risk * 0.1)
        elif composite_risk < 60.0:
            credit_decision = "APPROVE"
            risk_level = "MEDIUM"
            recommended_base_apr = 8.0 + (composite_risk * 0.12)
        else:
            credit_decision = "MANUAL_REVIEW"
            risk_level = "HIGH"
            recommended_base_apr = 12.0 + (composite_risk * 0.15)

        return {
            "composite_risk_score": composite_risk,
            "risk_level": risk_level,
            "credit_decision": credit_decision,
            "recommended_base_apr_pct": round(recommended_base_apr, 2),
            "max_advancement_percentage": 90.0 if composite_risk < 25.0 else (80.0 if composite_risk < 50.0 else 65.0),
            "eval_factors": {
                "supplier_score": supplier_history_score,
                "buyer_rating": buyer_credit_rating,
                "invoice_amount": invoice_amount,
                "tenor_days": tenor_days
            },
            "demo_notice": "Hackathon MVP evaluation based on synthetic demo ML training data."
        }

risk_agent = RiskAgent()
