import re
from typing import Tuple, Optional, Dict

# Allowed status values (keep in sync with UI dropdown)
ALLOWED_STATUS = {"New", "In Progress", "Selected", "Rejected"}


def validate_required_fields(candidate: Dict) -> Tuple[bool, Optional[str]]:
    """
    Check required fields are present and not empty.
    """
    required_fields = ["candidate_name", "email", "phone", "status"]

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


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Validate phone number (numeric and length).
    """
    phone = phone.strip()

    if not phone.isdigit():
        return False, "Phone number must contain only digits."

    if len(phone) != 10:
        return False, "Phone number must be 10 digits long."

    return True, None


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

    # Phone
    is_valid, error = validate_phone(candidate["phone"])
    if not is_valid:
        return False, error

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
