"""Module 4: Verification. Checks the company's web presence and domain age."""
import datetime as dt
from urllib.parse import urlparse

import requests

try:
    import whois
except ImportError:
    whois = None

from rules import GENERIC_DOMAINS, email_domain


def _host(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if "//" not in url:
        url = "http://" + url
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def domain_age_days(domain: str):
    """Age of a domain in days via WHOIS, or None if it cannot be found."""
    if not whois or not domain:
        return None
    try:
        created = whois.whois(domain).creation_date
        if isinstance(created, list):
            created = created[0]
        if created is None:
            return None
        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        return (dt.datetime.utcnow() - created).days
    except Exception:
        return None


def website_reachable(host: str) -> bool:
    if not host:
        return False
    try:
        r = requests.head("https://" + host, timeout=5, allow_redirects=True)
        return r.status_code < 500
    except requests.RequestException:
        return False


def verify(posting: dict, lookups: bool = True) -> dict:
    """Return {'risk': 0-1, 'notes': [...]}. Set lookups=False to skip network calls."""
    risk, notes = 0.0, []
    host = _host(posting.get("company_website", ""))
    mail = email_domain(posting.get("recruiter_email", ""))

    if not host:
        risk += 0.4
        notes.append("Company website missing, so it cannot be verified")
    elif lookups:
        if not website_reachable(host):
            risk += 0.3
            notes.append(f"Company website {host} could not be reached")
        age = domain_age_days(host)
        if age is None:
            notes.append(f"Domain age of {host} could not be determined")
        elif age < 180:
            risk += 0.3
            notes.append(f"Company domain is only {age} days old")
        else:
            notes.append(f"Company domain is {age // 365} year(s) old")

    if host and mail and mail not in GENERIC_DOMAINS and not (mail == host or mail.endswith("." + host) or host.endswith("." + mail)):
        risk += 0.2
        notes.append(f"Email domain ({mail}) does not match the company website ({host})")

    # No free, reliable API exists for company-registration records, so this stays a manual step.
    notes.append("Company registration: confirm manually on the MCA portal (not automated)")
    return {"risk": round(min(risk, 1.0), 3), "notes": notes}
