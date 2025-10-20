import re
from uuid import UUID


def is_valid_phone(phone: str):
    phone_regex = r"^(?:\+234[789][01]\d{8}|0[789][01]\d{8}|\+\d{1,15})$"
    
    if not re.match(phone_regex, phone):
        return False
    
    return True


def is_valid_email(email: str):
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_regex, email):
        return False

    return True


def is_valid_password(password: str):
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>_-])[A-Za-z\d!@#$%^&*(),.?":{}|<>_-]{8,}$'

    if not re.match(password_regex, password):
        return False

    return True


def is_valid_uuid(uuid_id):
    try:
        uuid_obj = UUID(uuid_id, version=4)
        return str(uuid_obj) == uuid_id
    except ValueError:
        return False
