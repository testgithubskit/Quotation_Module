import re


def reject_password_spaces(value: str) -> str:
    if " " in value:
        raise ValueError("Password cannot contain spaces")
    return value


def reject_person_name_spaces(value: str, label: str = "Name") -> str:
    if value != value.strip():
        raise ValueError(f"{label} cannot have leading or trailing spaces")
    if re.search(r" {2,}", value):
        raise ValueError(f"{label} cannot have consecutive spaces")
    return value
