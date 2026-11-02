"""Application tier: ties the modules together and exposes them to the browser extension.

Run:  cd backend && uvicorn app:app --reload
"""
import sqlite3
from pathlib import Path

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rules import screen
from scoring import trust_score
from verify import verify

BASE = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE / "model" / "model.joblib"
DB_PATH = BASE / "data" / "reports.db"

app = FastAPI(title="Job Posting Trust Score")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


class Posting(BaseModel):
    title: str = ""
    company_name: str = ""
    company_website: str = ""
    recruiter_email: str = ""
    description: str = ""
    requirements: str = ""
    url: str = ""


class Report(BaseModel):
    url: str = ""
    company_name: str = ""
    reason: str = ""


def _db():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, company_name TEXT, reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    return con


def _label(score: int) -> str:
    return "Green" if score >= 70 else "Yellow" if score >= 40 else "Red"


@app.get("/health")
def health():
    return {"ok": True, "ml_model_loaded": model is not None}


@app.post("/analyze")
def analyze(p: Posting, lookups: bool = True):
    posting = p.model_dump()

    rule_result = screen(posting)                       # fast rule-based screening
    ml_prob = None
    if model is not None:                               # ML classification
        text = " ".join([p.title, p.company_name, p.description, p.requirements])
        ml_prob = float(model.predict_proba([text])[0][1])
    verify_result = verify(posting, lookups=lookups)    # web presence + domain age

    result = trust_score(ml_prob, rule_result, verify_result)

    con = _db()                                         # community reports for the same company/URL
    n = con.execute("SELECT COUNT(*) FROM reports WHERE (url != '' AND url = ?) OR "
                    "(company_name != '' AND lower(company_name) = lower(?))",
                    (p.url, p.company_name)).fetchone()[0]
    con.close()
    if n:
        result["trust_score"] = max(0, result["trust_score"] - min(30, 10 * n))
        result["label"] = _label(result["trust_score"])

    result["reasons"] = rule_result["flags"] + verify_result["notes"]
    result["community_reports"] = n
    result["ml_probability"] = None if ml_prob is None else round(ml_prob, 3)
    return result


@app.post("/report")
def report(r: Report):
    con = _db()
    con.execute("INSERT INTO reports (url, company_name, reason) VALUES (?, ?, ?)",
                (r.url, r.company_name, r.reason))
    con.commit()
    con.close()
    return {"saved": True}
