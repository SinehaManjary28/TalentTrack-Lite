import re
from typing import Tuple, Optional, Dict

# Allowed status values (keep in sync with UI dropdown)
ALLOWED_STATUS = {"New", "In Progress", "Selected", "Rejected"}

# Country-wise phone rules (code : required digits)
COUNTRY_PHONE_RULES = {
    "+91": 10,  # India
    "+1": 10,   # USA / Canada
    "+44": 10,  # UK (simplified)
    "+61": 9,   # Australia
    "+81": 10,  # Japan
    "+49": 11,  # Germany
    "+971": 9,  # UAE
    "+65": 8    # Singapore
}


def validate_required_fields(candidate: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check required fields are present and not empty.
    """
    required_fields = ["candidate_name", "email", "phone", "status", "country_code"]

    for field in required_fields:
        if field not in candidate or not str(candidate[field]).strip():
            return False, f"{field.replace('_', ' ').title()} is required."

    return True, None


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format.
    """
    email = email.strip().lower()
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"

    if not re.match(email_regex, email):
        return False, "Invalid email format."

    return True, None


def validate_phone(phone: str, country_code: str):
    """
    Validate phone number based on selected country code
    and normalize it to +<country_code><number>.
    """
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
    """
    Validate candidate status.
    """
    if status not in ALLOWED_STATUS:
        return False, f"Status must be one of {', '.join(ALLOWED_STATUS)}."

    return True, None


def validate_candidate(candidate: Dict) -> Tuple[bool, Optional[str]]:
    """
    Master validation function to be called before DB insert/update.
    """
    # Required fields
    is_valid, error = validate_required_fields(candidate)
    if not is_valid:
        return False, error

    # Email
    is_valid, error = validate_email(candidate["email"])
    if not is_valid:
        return False, error

    # Phone (with country code)
    is_valid, error, normalized_phone = validate_phone(
        candidate["phone"],
        candidate["country_code"]
    )
    if not is_valid:
        return False, error

    # overwrite phone with normalized value
    candidate["phone"] = normalized_phone

    # Status
    is_valid, error = validate_status(candidate["status"])
    if not is_valid:
        return False, error

    return True, None


def check_duplicate_logic(existing_record) -> Tuple[bool, Optional[str]]:
    """
    Decide duplicate outcome based on DB response.
    existing_record is the output of find_duplicate() from db.py
    """
    if existing_record:
        return True, "Duplicate candidate found (email or phone already exists)."

    return False, None
