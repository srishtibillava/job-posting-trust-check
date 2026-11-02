"""
Module 3: Machine Learning Classification.

Trains an ensemble (Random Forest + XGBoost, soft voting) on the EMSCAD dataset
to estimate the probability that a job posting is fraudulent.

Usage:
    python backend/train_model.py data/fake_job_postings.csv
"""
import sys
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (average_precision_score, classification_report,
                             confusion_matrix)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

try:
    from xgboost import XGBClassifier
except ImportError:  # keeps the script usable without xgboost installed
    XGBClassifier = None

TEXT_COLUMNS = ["title", "company_profile", "description", "requirements", "benefits"]


def build_text(df: pd.DataFrame) -> pd.Series:
    """Join the posting's text fields into one string (the app sends the same fields)."""
    return df[TEXT_COLUMNS].fillna("").agg(" ".join, axis=1)


def main(csv_path: str, out_path: str = "model/model.joblib") -> None:
    df = pd.read_csv(csv_path)
    X, y = build_text(df), df["fraudulent"].astype(int)
    print(f"Postings: {len(df)} | fraudulent: {y.sum()} ({y.mean():.1%})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)

    # Fake postings are rare, so every model is told to weight them more heavily.
    ratio = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    rf = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                n_jobs=-1, random_state=42)
    estimators = [("rf", rf)]
    if XGBClassifier is not None:
        estimators.append(("xgb", XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.1,
            scale_pos_weight=ratio, eval_metric="logloss", random_state=42)))

    model = Pipeline([
        ("tfidf", TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                  max_features=20000, min_df=2)),
        ("clf", VotingClassifier(estimators, voting="soft")),
    ])
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    print("\nConfusion matrix (rows = actual, cols = predicted):")
    print(confusion_matrix(y_test, pred))
    print("\n", classification_report(y_test, pred, target_names=["real", "fake"]))
    print(f"Precision-recall AUC: {average_precision_score(y_test, proba):.3f}")
    print("Judge the model on recall/F1 for 'fake', not accuracy: the data is imbalanced.")

    joblib.dump(model, out_path)
    print(f"\nSaved model to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python backend/train_model.py data/fake_job_postings.csv")
    main(sys.argv[1])
