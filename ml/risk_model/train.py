import os
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

def generate_synthetic_data(num_samples: int = 1000):
    """Generates synthetic dataset for Supply Chain Financing risk prediction."""
    np.random.seed(42)
    
    supplier_risk_scores = np.random.uniform(5.0, 50.0, num_samples) # 0-100 scale (lower is better)
    buyer_ratings_numeric = np.random.choice([1, 2, 3, 4], size=num_samples, p=[0.4, 0.3, 0.2, 0.1]) # 1: AAA, 2: AA, 3: A, 4: BBB
    amounts = np.random.uniform(10000.0, 500000.0, num_samples)
    tenors = np.random.choice([30, 45, 60, 90, 120], size=num_samples)
    
    # Calculate synthetic default probability
    # Higher risk score, lower buyer rating, larger amount, longer tenor -> higher default probability
    default_prob = (
        (supplier_risk_scores / 100.0) * 0.4 +
        (buyer_ratings_numeric / 4.0) * 0.3 +
        (amounts / 500000.0) * 0.15 +
        (tenors / 120.0) * 0.15
    )
    
    defaults = (default_prob > 0.45).astype(int)

    df = pd.DataFrame({
        "supplier_risk_score": supplier_risk_scores,
        "buyer_rating_numeric": buyer_ratings_numeric,
        "amount": amounts,
        "tenor_days": tenors,
        "is_default": defaults
    })
    
    return df

def train_and_save_model():
    """Trains a RandomForest risk prediction model and saves artifacts."""
    print("Generating synthetic financial data...")
    df = generate_synthetic_data()
    
    X = df[["supplier_risk_score", "buyer_rating_numeric", "amount", "tenor_days"]]
    y = df["is_default"]

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Save model
    model_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "risk_model.joblib")
    joblib.dump(model, model_path)
    print(f"Risk model saved to {model_path}")

    # Save demo training data sample
    data_dir = os.path.abspath(os.path.join(model_dir, "..", "training_data"))
    os.makedirs(data_dir, exist_ok=True)
    sample_path = os.path.join(data_dir, "synthetic_invoices.json")
    df.head(50).to_json(sample_path, orient="records", indent=2)
    print(f"Sample synthetic dataset saved to {sample_path}")

if __name__ == "__main__":
    train_and_save_model()
