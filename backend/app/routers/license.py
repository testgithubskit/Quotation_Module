import json

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import DbSession
from app.core.exceptions import AppError
from app.services import license as license_service

router = APIRouter()


class LicenseTextRequest(BaseModel):
    license_text: str = Field(..., min_length=2)


def _load_license(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError("Paste the full license JSON", status_code=400, code="invalid_license") from exc
    if not isinstance(data, dict):
        raise AppError("License JSON must be an object", status_code=400, code="invalid_license")
    return data


@router.get("/status")
def license_status(db: DbSession) -> dict:
    return license_service.status(db)


@router.get("/machine-request")
def machine_request() -> dict:
    return license_service.machine_request()


@router.post("/validate")
def validate_license(payload: LicenseTextRequest) -> dict:
    return license_service.validate(_load_license(payload.license_text))


@router.post("/activate")
def activate_license(payload: LicenseTextRequest, db: DbSession) -> dict:
    return license_service.activate(db, _load_license(payload.license_text))
