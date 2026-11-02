"""Module 5: Trust Score. Combines rule, ML and verification results into one 0-100 score."""

# Design choice: change these weights, test them, and justify your final values in the report.
WEIGHTS = {"ml": 0.45, "rules": 0.35, "verify": 0.20}


def trust_score(ml_prob, rule_result: dict, verify_result: dict) -> dict:
    parts = {"rules": rule_result["score"], "verify": verify_result["risk"]}
    if ml_prob is not None:
        parts["ml"] = ml_prob

    total_w = sum(WEIGHTS[k] for k in parts)          # re-normalise if the ML model is missing
    risk = sum(WEIGHTS[k] * v for k, v in parts.items()) / total_w
    score = round(100 * (1 - risk))

    if rule_result["hard_flag"]:                       # explicit money demand overrides the blend
        score = min(score, 30)

    label = "Green" if score >= 70 else "Yellow" if score >= 40 else "Red"
    return {"trust_score": score, "label": label,
            "risk_breakdown": {k: round(v, 3) for k, v in parts.items()}}
