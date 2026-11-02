"""Module 2: Rule-Based Screening. Fast checks for the red flags found in the survey."""
import re

GENERIC_DOMAINS = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com",
                   "rediffmail.com", "ymail.com", "proton.me", "protonmail.com"}

# (flag name, regex, weight, explanation shown to the user)
TEXT_RULES = [
    ("upfront_payment",
     r"registration fee|security deposit|training fee|processing fee|refundable|"
     r"pay (?:rs|inr|₹)|deposit (?:rs|inr|₹)|kit charges?|joining fee|pay .{0,20}to (?:apply|join|confirm)",
     0.40, "Asks for money (fee/deposit) before or during hiring"),
    ("sensitive_documents",
     r"aadhaar|aadhar|\bpan card\b|\bpan number\b|bank (?:account|details)|passport copy|"
     r"cancelled cheque|\botp\b",
     0.25, "Asks for Aadhaar/PAN/bank details at the application stage"),
    ("chat_only_contact",
     r"whatsapp|telegram|text us on|message us on",
     0.15, "Contact or interview only through WhatsApp/Telegram"),
    ("too_good_to_be_true",
     r"guaranteed (?:income|salary|job|placement)|earn .{0,15}(?:per day|daily|weekly)|"
     r"no experience (?:needed|required).{0,40}(?:lakh|\d{2},\d{3})|work from home.{0,40}earn|"
     r"100% placement",
     0.20, "Unrealistic pay or guaranteed income promised"),
    ("urgency_pressure",
     r"limited (?:seats|slots|vacancies)|apply immediately|urgent(?:ly)? hiring|"
     r"confirm (?:today|within \d+ hours)|last chance",
     0.10, "Uses urgency or pressure to push a quick decision"),
]


def email_domain(email: str) -> str:
    return email.split("@")[-1].strip().lower() if email and "@" in email else ""


def screen(posting: dict) -> dict:
    """Return {'score': 0-1 risk, 'flags': [explanations], 'hard_flag': bool}."""
    text = " ".join(str(posting.get(k, "")) for k in ("title", "description", "requirements")).lower()
    score, flags = 0.0, []

    for name, pattern, weight, message in TEXT_RULES:
        if re.search(pattern, text):
            score += weight
            flags.append(message)

    domain = email_domain(posting.get("recruiter_email", ""))
    if domain in GENERIC_DOMAINS:
        score += 0.25
        flags.append(f"Recruiter uses a generic email domain ({domain}), not a company domain")

    if not str(posting.get("company_website", "")).strip():
        score += 0.20
        flags.append("No company website provided")

    if len(text.split()) < 25:
        score += 0.10
        flags.append("Very vague job description")

    score = min(score, 1.0)
    # an explicit payment demand is serious enough to mark High Risk on its own
    hard = any("money" in f for f in flags)
    return {"score": round(score, 3), "flags": flags, "hard_flag": hard}
