import re
from typing import Tuple, Optional, Dict

# Allowed status values (keep in sync with UI dropdown)
ALLOWED_STATUS = {"New", "In Progress", "Selected", "Rejected"}

# Country-wise phone rules (code : required digits)
COUNTRY_PHONE_RULES = {
    "+91": 10,
    "+1": 10,
    "+44": 10,
    "+61": 9,
    "+81": 10,
    "+49": 11,
    "+971": 9,
    "+65": 8
}


def validate_required_fields(candidate: Dict) -> Tuple[bool, Optional[str]]:
    required_fields = ["candidate_name", "email", "phone", "status", "country_code"]

    for field in required_fields:
        if field not in candidate or not str(candidate[field]).strip():
            return False, f"{field.replace('_', ' ').title()} is required."

    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    email = email.strip().lower()
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    if not re.match(email_regex, email):
        return False, "Invalid email format."

    return True, None


def validate_phone(phone: str, country_code: str):
    if not phone:
        return False, "Phone number is required.", None

    phone = phone.strip()

    if not phone.isdigit():
        return False, "Phone number must contain only digits.", None

    if country_code not in COUNTRY_PHONE_RULES:
        return False, "Unsupported country code.", None

    required_length = COUNTRY_PHONE_RULES[country_code]

    if len(phone) != required_length:
        return False, f"Phone number must be {required_length} digits.", None

    normalized_phone = country_code + phone
    return True, None, normalized_phone


def validate_status(status: str) -> Tuple[bool, Optional[str]]:
    if status not in ALLOWED_STATUS:
        return False, f"Status must be one of {', '.join(ALLOWED_STATUS)}."

    return True, None


# 🔴 NEW: Name existence warning logic
def name_exists_warning(existing_name_record) -> Optional[str]:
    """
    Returns warning message if candidate name already exists.
    This is NOT a blocking validation.
    """
    if existing_name_record:
        return "Candidate with this name already exists."
    return None


def validate_candidate(candidate: Dict) -> Tuple[bool, Optional[str]]:
    # Required fields
    is_valid, error = validate_required_fields(candidate)
    if not is_valid:
        return False, error

    # Email
    is_valid, error = validate_email(candidate["email"])
    if not is_valid:
        return False, error

    # Phone
    is_valid, error, normalized_phone = validate_phone(
        candidate["phone"],
        candidate["country_code"]
    )
    if not is_valid:
        return False, error

    candidate["phone"] = normalized_phone

    # Status
    is_valid, error = validate_status(candidate["status"])
    if not is_valid:
        return False, error

    return True, None


def check_duplicate_logic(existing_record) -> Tuple[bool, Optional[str]]:
    if existing_record:
        return True, "Duplicate candidate found (email or phone already exists)."

    return False, None
