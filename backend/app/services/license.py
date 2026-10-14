import hashlib
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.license import LicenseInfo

PRODUCT_NAME = "Quotation Modal"
_LICENSE_FILE = Path(__file__).resolve().parents[3] / "License" / "client_license.py"
_spec = importlib.util.spec_from_file_location("quotation_client_license", _LICENSE_FILE)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"License validator not found: {_LICENSE_FILE}")
_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_client)


def machine_request() -> dict:
    return dict(_client.get_machine_info())


def _parse_expiry(value: str | None) -> datetime | None:
    if not value:
        return None
    clean = value.rstrip("Z")
    parsed = datetime.fromisoformat(clean)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _check(license_data: dict) -> tuple[bool, str, dict]:
    if not isinstance(license_data, dict):
        return False, "Paste the license JSON", {}
    valid, message, details = _client.verify_license_data(license_data)
    product = str(details.get("product") or license_data.get("Product") or "").strip()
    if valid and product != PRODUCT_NAME:
        return False, f'This license is for "{product or "another product"}", not {PRODUCT_NAME}', details
    return valid, message, details


def status(db: Session) -> dict:
    info = machine_request()
    payload = {
        "licensed": False,
        "message": "No license activated for this computer",
        "license_id": None,
        "product": None,
        "expiry": None,
        "fingerprint": info["Fingerprint"],
    }
    row = (
        db.query(LicenseInfo)
        .filter(LicenseInfo.is_active.is_(True))
        .order_by(LicenseInfo.activated_at.desc())
        .first()
    )
    if row is None:
        return payload

    valid, message, details = _check(row.license_json)
    payload.update(
        {
            "licensed": valid,
            "message": message,
            "license_id": details.get("license_id") or row.license_id,
            "product": details.get("product") or row.product,
            "expiry": details.get("expiry") or (row.expiry.isoformat() if row.expiry else None),
        }
    )
    return payload


def validate(license_data: dict) -> dict:
    valid, message, details = _check(license_data)
    return {
        "valid": valid,
        "message": message,
        "license_id": details.get("license_id"),
        "product": details.get("product"),
        "expiry": details.get("expiry"),
        "fingerprint": machine_request()["Fingerprint"],
    }


def activate(db: Session, license_data: dict) -> dict:
    valid, message, details = _check(license_data)
    if not valid:
        raise AppError(message, status_code=400, code="invalid_license")

    license_id = str(license_data.get("LicenseId", "")).strip()
    fingerprint = str(license_data.get("Fingerprint", "")).strip().upper()
    product = str(license_data.get("Product", "")).strip()
    expiry = str(license_data.get("Expiry", "")).strip()
    signature = str(license_data.get("Signature", "")).strip()
    canonical = f"{license_id}|{fingerprint}|{product}|{expiry}"

    for row in db.query(LicenseInfo).filter(LicenseInfo.is_active.is_(True)).all():
        row.is_active = False

    db.add(
        LicenseInfo(
            license_id=license_id,
            product=product,
            fingerprint=fingerprint,
            expiry=_parse_expiry(expiry),
            signature=signature,
            payload_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            license_json=license_data,
            is_active=True,
        )
    )
    db.commit()
    return status(db)
