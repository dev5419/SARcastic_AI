import re
from datetime import datetime

PROHIBITED_WORDS = ["guilty", "criminal", "definitely", "certainly", "obviously"]


def contains_prohibited_language(text):
    for word in PROHIBITED_WORDS:
        if word.lower() in text.lower():
            return True
    return False


def has_5w1h(narrative):
    required_sections = ["who", "what", "when", "where", "why", "how"]
    found = 0

    text = narrative.lower()
    for section in required_sections:
        if section in text:
            found += 1

    return found == 6


def has_transaction_details(transactions):
    return len(transactions) >= 1


def has_structuring(transactions):
    cash_tx = [t for t in transactions if t["type"] == "cash"]
    if not cash_tx:
        return False

    range_tx = [t for t in cash_tx if 9000 <= t["amount"] <= 9999]

    if len(cash_tx) > 0 and len(range_tx) / len(cash_tx) >= 0.8:
        return True

    return False


def calculate_confidence(score):
    if score >= 13:
        return "HIGH", 0.9
    elif score >= 9:
        return "MEDIUM", 0.75
    else:
        return "LOW", 0.5


def evaluate_rules(data):
    """
    Expected data:
    {
        "kyc": {},
        "accounts": [],
        "transactions": [],
        "activity_start": "",
        "activity_end": "",
        "total_amount": float,
        "subject_identified": True/False,
        "narrative": ""
    }
    """

    triggered_rules = []
    errors = []
    warnings = []
    score = 0

    kyc = data["kyc"]
    accounts = data["accounts"]
    transactions = data["transactions"]
    narrative = data.get("narrative", "")

    # RULE 01 & 02 Filing Threshold
    if data["subject_identified"] and data["total_amount"] >= 5000:
        triggered_rules.append("RULE 01: Filing Mandatory (30 days)")
        score += 1

    if not data["subject_identified"] and data["total_amount"] >= 25000:
        triggered_rules.append("RULE 02: Filing Mandatory (60 days)")
        score += 1

    # RULE 03 Subject Validation
    if not kyc.get("full_name"):
        errors.append("Full name missing")
    else:
        score += 1

    # RULE 04 Account Validation
    if not accounts:
        errors.append("No account information provided")
    else:
        score += 1

    # RULE 05 Date Validation
    try:
        start = datetime.strptime(data["activity_start"], "%m/%d/%Y")
        end = datetime.strptime(data["activity_end"], "%m/%d/%Y")
        if end < start:
            errors.append("End date before start date")
        else:
            score += 1
    except:
        errors.append("Invalid or missing activity dates")

    # RULE 06 Amount Validation
    if data["total_amount"] <= 0:
        errors.append("Invalid suspicious amount")
    else:
        score += 1

    # RULE 07 Red Flag Presence
    if has_structuring(transactions):
        triggered_rules.append("RULE 10: STRUCTURING detected (31 U.S.C. § 5324)")
        score += 2

    # RULE 08 5W1H
    if narrative:
        if has_5w1h(narrative):
            score += 2
        else:
            warnings.append("Narrative missing full 5W1H elements")

    # RULE 09 Narrative Length
    if narrative:
        if len(narrative) >= 500:
            score += 1
        else:
            warnings.append("Narrative below 500 characters")

    # RULE 11 Prohibited Language
    if narrative and contains_prohibited_language(narrative):
        errors.append("Prohibited language detected")
    else:
        score += 1

    # RULE 12 Transaction Details
    if has_transaction_details(transactions):
        score += 1
    else:
        warnings.append("No transaction details provided")

    # RULE 13 Investigation Section
    if narrative and "investigation" in narrative.lower():
        score += 1
    else:
        warnings.append("Investigation steps not documented")

    # RULE 14 Conclusion Section
    if narrative and "conclusion" in narrative.lower():
        score += 1
    else:
        warnings.append("Conclusion section missing")

    confidence_label, confidence_score = calculate_confidence(score)

    return {
        "triggered_rules": triggered_rules,
        "errors": errors,
        "warnings": warnings,
        "confidence_label": confidence_label,
        "confidence_score": confidence_score
    }
