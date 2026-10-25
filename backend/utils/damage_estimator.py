"""
damage_estimator.py
Damage count se severity level nikalne ka rule-based logic.
"""


def estimate_severity(damage_count):
    """
    Damage instances ki count lekar severity level return karta hai.
    """
    if damage_count == 0:
        return "None", "✅"
    elif damage_count <= 2:
        return "Minor", "🟢"
    elif damage_count <= 5:
        return "Moderate", "🟡"
    else:
        return "Severe", "🔴"