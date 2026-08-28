"""
SCF Nexus - ML Risk Engine
Synthetic training data generator + XGBoost risk model
for hackathon demo. Clearly labeled as prototype.
"""
import os
import json
import random
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, roc_auc_score
import joblib

MODEL_DIR = os.path.dirname(__file__)

# ────────────────────────────────────────────────────────────
# 1. SYNTHETIC TRAINING DATA GENERATION
# ────────────────────────────────────────────────────────────
random.seed(42)
np.random.seed(42)

BUYER_RATINGS = {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5}
SUPPLIER_RATINGS = {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5}

def generate_synthetic_dataset(n=2000):
    rows = []
    for _ in range(n):
        buyer_rating = random.choice(list(BUYER_RATINGS.keys()))
        supplier_rating = random.choice(list(SUPPLIER_RATINGS.keys()))
        invoice_amount = random.uniform(10000, 2000000)
        tenor_days = random.choice([30, 45, 60, 90, 120, 180])
        verification_score = random.uniform(0.5, 1.0)
        num_past_invoices = random.randint(0, 50)
        late_payment_history = random.uniform(0.0, 0.4)
        delivery_confirmed = random.choice([0, 1, 1, 1])
        po_matched = random.choice([0, 1, 1, 1, 1])
        buyer_acknowledged = random.choice([0, 1, 1, 1])

        # Risk score calculation (ground truth label)
        b_risk = BUYER_RATINGS[buyer_rating]
        s_risk = SUPPLIER_RATINGS[supplier_rating]
        base_risk = (b_risk * 8 + s_risk * 5
                    + (tenor_days / 180.0) * 10
                    + late_payment_history * 25
                    - verification_score * 15
                    - delivery_confirmed * 5
                    - po_matched * 4
                    - buyer_acknowledged * 6
                    + (invoice_amount / 2000000.0) * 8
                    - (num_past_invoices / 50.0) * 5)
        base_risk = max(0, min(95, base_risk + random.gauss(0, 5)))

        # Binary label: 1 = HIGH RISK (default likely), 0 = LOW/MEDIUM RISK
        label = 1 if base_risk > 45 else 0

        rows.append({
            "buyer_rating_enc": b_risk,
            "supplier_rating_enc": s_risk,
            "invoice_amount_log": np.log1p(invoice_amount),
            "tenor_days": tenor_days,
            "verification_score": verification_score,
            "num_past_invoices": num_past_invoices,
            "late_payment_history": late_payment_history,
            "delivery_confirmed": delivery_confirmed,
            "po_matched": po_matched,
            "buyer_acknowledged": buyer_acknowledged,
            "raw_risk_score": round(base_risk, 2),
            "default_risk_label": label
        })
    return pd.DataFrame(rows)


# ────────────────────────────────────────────────────────────
# 2. TRAIN THE MODELS
# ────────────────────────────────────────────────────────────
def train_and_save():
    print("Generating synthetic SCF dataset (n=2000)...")
    df = generate_synthetic_dataset(2000)

    features = [
        "buyer_rating_enc", "supplier_rating_enc", "invoice_amount_log",
        "tenor_days", "verification_score", "num_past_invoices",
        "late_payment_history", "delivery_confirmed", "po_matched", "buyer_acknowledged"
    ]
    X = df[features]
    y = df["default_risk_label"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- Model 1: Gradient Boosting Classifier (XGBoost-like) ---
    print("Training GradientBoosting risk classifier...")
    gb_model = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.08, random_state=42)
    gb_model.fit(X_train, y_train)
    gb_preds = gb_model.predict(X_test)
    gb_proba = gb_model.predict_proba(X_test)[:, 1]
    gb_acc = accuracy_score(y_test, gb_preds)
    gb_auc = roc_auc_score(y_test, gb_proba)

    print(f"GBM Accuracy: {gb_acc:.3f} | AUC-ROC: {gb_auc:.3f}")
    print(classification_report(y_test, gb_preds))

    # --- Model 2: Random Forest ---
    print("Training RandomForest risk classifier...")
    rf_model = RandomForestClassifier(n_estimators=150, max_depth=6, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    rf_proba = rf_model.predict_proba(X_test)[:, 1]
    rf_auc = roc_auc_score(y_test, rf_proba)
    print(f"RF AUC-ROC: {rf_auc:.3f}")

    # Scaler
    scaler = StandardScaler()
    scaler.fit(X_train)

    # Save models and metadata
    joblib.dump(gb_model, os.path.join(MODEL_DIR, "gb_risk_model.pkl"))
    joblib.dump(rf_model, os.path.join(MODEL_DIR, "rf_risk_model.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))

    metadata = {
        "model_type": "GradientBoostingClassifier (SCF Prototype - Synthetic Data)",
        "features": features,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "gbm_accuracy": round(gb_acc, 4),
        "gbm_auc_roc": round(gb_auc, 4),
        "rf_auc_roc": round(rf_auc, 4),
        "feature_importances": dict(zip(features, gb_model.feature_importances_.round(4).tolist())),
        "disclaimer": "Trained on SYNTHETIC data for hackathon prototype purposes only."
    }
    with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nModels saved to {MODEL_DIR}")
    print("Feature Importances:")
    for feat, imp in sorted(zip(features, gb_model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {feat:<30} {imp:.4f}")

    return gb_model, rf_model, scaler, metadata


# ────────────────────────────────────────────────────────────
# 3. INFERENCE ENGINE
# ────────────────────────────────────────────────────────────
class SCFRiskModel:
    """
    Production-ready SCF Risk Inference Engine.
    Loads pre-trained GBM + RF models for ensemble risk scoring.
    """

    def __init__(self):
        self.gb_model = None
        self.rf_model = None
        self.scaler = None
        self.metadata = None
        self.load()

    def load(self):
        gb_path = os.path.join(MODEL_DIR, "gb_risk_model.pkl")
        if not os.path.exists(gb_path):
            print("Models not found, training now...")
            train_and_save()

        self.gb_model = joblib.load(os.path.join(MODEL_DIR, "gb_risk_model.pkl"))
        self.rf_model = joblib.load(os.path.join(MODEL_DIR, "rf_risk_model.pkl"))
        self.scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))

        with open(os.path.join(MODEL_DIR, "model_metadata.json")) as f:
            self.metadata = json.load(f)

        print("SCF Risk Model loaded successfully.")

    def predict(self,
                buyer_rating: str,
                supplier_rating: str,
                invoice_amount: float,
                tenor_days: int,
                verification_score: float = 0.9,
                num_past_invoices: int = 5,
                late_payment_history: float = 0.05,
                delivery_confirmed: int = 1,
                po_matched: int = 1,
                buyer_acknowledged: int = 1) -> dict:

        br = BUYER_RATINGS.get(buyer_rating.upper(), 2)
        sr = SUPPLIER_RATINGS.get(supplier_rating.upper(), 2)

        features = np.array([[
            br,
            sr,
            np.log1p(invoice_amount),
            tenor_days,
            verification_score,
            num_past_invoices,
            late_payment_history,
            delivery_confirmed,
            po_matched,
            buyer_acknowledged
        ]])

        gb_prob = self.gb_model.predict_proba(features)[0][1]
        rf_prob = self.rf_model.predict_proba(features)[0][1]
        ensemble_prob = (gb_prob * 0.6 + rf_prob * 0.4)

        risk_score = round(ensemble_prob * 100, 2)

        if risk_score < 20:
            risk_level = "LOW"
            max_advance_pct = 90.0
            base_apr = 6.5
            eligible = True
        elif risk_score < 40:
            risk_level = "MEDIUM"
            max_advance_pct = 85.0
            base_apr = 9.0
            eligible = True
        elif risk_score < 60:
            risk_level = "HIGH"
            max_advance_pct = 70.0
            base_apr = 13.5
            eligible = True
        else:
            risk_level = "CRITICAL"
            max_advance_pct = 50.0
            base_apr = 18.0
            eligible = False

        verification_tier = (
            "🟢 VERIFIED" if verification_score >= 0.85 and delivery_confirmed and po_matched and buyer_acknowledged
            else ("🟡 PARTIALLY_VERIFIED" if verification_score >= 0.65
                  else "🔴 DISPUTED")
        )

        confidence_pct = round(
            (delivery_confirmed * 20 + po_matched * 20 +
             buyer_acknowledged * 25 + verification_score * 20 +
             (1 - late_payment_history) * 15), 1)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "eligible_for_financing": eligible,
            "max_advance_pct": max_advance_pct,
            "recommended_base_apr_pct": base_apr,
            "gb_model_probability": round(gb_prob * 100, 2),
            "rf_model_probability": round(rf_prob * 100, 2),
            "ensemble_default_probability_pct": round(ensemble_prob * 100, 2),
            "verification_tier": verification_tier,
            "invoice_confidence_pct": min(confidence_pct, 98.0),
            "ai_analysis": (
                f"Ensemble ML (GBM+RF) assessed Buyer({buyer_rating}) + Supplier({supplier_rating}) "
                f"composite default probability at {risk_score:.1f}%. "
                f"Verification confidence: {confidence_pct:.0f}%. "
                f"Max financing advance: {max_advance_pct:.0f}% at {base_apr:.1f}% base APR."
            ),
            "suitability_for_matching": round(max(0, 100 - risk_score), 1)
        }


# Singleton instance
_risk_model_instance = None

def get_risk_model() -> SCFRiskModel:
    global _risk_model_instance
    if _risk_model_instance is None:
        _risk_model_instance = SCFRiskModel()
    return _risk_model_instance


if __name__ == "__main__":
    print("Training SCF ML Risk Models...")
    train_and_save()

    print("\n--- Inference Demo ---")
    model = get_risk_model()

    test_cases = [
        {"buyer_rating": "AA", "supplier_rating": "A", "invoice_amount": 250000, "tenor_days": 60, "delivery_confirmed": 1, "po_matched": 1, "buyer_acknowledged": 1},
        {"buyer_rating": "BBB", "supplier_rating": "BB", "invoice_amount": 800000, "tenor_days": 90, "delivery_confirmed": 1, "po_matched": 0, "buyer_acknowledged": 0},
        {"buyer_rating": "B", "supplier_rating": "B", "invoice_amount": 1500000, "tenor_days": 180, "delivery_confirmed": 0, "po_matched": 0, "buyer_acknowledged": 0},
    ]

    for tc in test_cases:
        result = model.predict(**tc)
        print(f"\nBuyer: {tc['buyer_rating']} | Supplier: {tc['supplier_rating']} | Amount: ${tc['invoice_amount']:,}")
        print(f"  Risk: {result['risk_level']} ({result['risk_score']:.1f}%) | Confidence: {result['invoice_confidence_pct']:.0f}%")
        print(f"  Tier: {result['verification_tier']} | Eligible: {result['eligible_for_financing']}")
