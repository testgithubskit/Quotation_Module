from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import register_exception_handlers
from app.core.seed import seed_roles_and_permissions
from app.models import *  # noqa: F403
from app.routers import (
    activities,
    audit_logs,
    auth,
    custom_fields,
    customers,
    notifications,
    organizations,
    pdf_render,
    license,
    permissions,
    quotation_templates,
    quotations,
    roles,
    users,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db = SessionLocal()
    try:
        seed_roles_and_permissions(db)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Multi-tenant quotation management API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

register_exception_handlers(app)


class LicenseGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        open_path = (
            request.method == "OPTIONS"
            or path.startswith(f"{settings.api_v1_prefix}/license")
            or not path.startswith(settings.api_v1_prefix)
        )
        if open_path:
            return await call_next(request)

        from app.core.database import SessionLocal
        from app.services import license as license_service

        db = SessionLocal()
        try:
            current = license_service.status(db)
        finally:
            db.close()
        if current["licensed"]:
            return await call_next(request)
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "error": {
                    "code": "license_required",
                    "detail": current["message"],
                    "status": 403,
                },
            },
        )


app.add_middleware(LicenseGateMiddleware)

# Private LAN and localhost are allowed on every install. A customer opens the
# app at that PC's own address, so no per-customer IP is listed here.
_cors_kwargs = {
    "allow_origins": settings.cors_origin_list,
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "allow_origin_regex": (
        r"https?://("
        r"localhost|127\.0\.0\.1|"
        r"192\.168\.\d{1,3}\.\d{1,3}|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
        r")(:\d+)?"
    ),
}

app.add_middleware(CORSMiddleware, **_cors_kwargs)

prefix = settings.api_v1_prefix
app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["Auth"])
app.include_router(users.router, prefix=f"{prefix}/users", tags=["Users"])
app.include_router(roles.router, prefix=f"{prefix}/roles", tags=["Roles"])
app.include_router(permissions.router, prefix=f"{prefix}/permissions", tags=["Permissions"])
app.include_router(organizations.router, prefix=f"{prefix}/organizations", tags=["Organizations"])
app.include_router(customers.router, prefix=f"{prefix}/customers", tags=["Customers"])
app.include_router(activities.router, prefix=f"{prefix}/activities", tags=["Activities"])
app.include_router(quotations.router, prefix=f"{prefix}/quotations", tags=["Quotations"])
app.include_router(
    quotation_templates.router,
    prefix=f"{prefix}/quotation-templates",
    tags=["Quotation Templates"],
)
app.include_router(custom_fields.router, prefix=f"{prefix}/custom-fields", tags=["Custom Fields"])
app.include_router(notifications.router, prefix=f"{prefix}/notifications", tags=["Notifications"])
app.include_router(audit_logs.router, prefix=f"{prefix}/audit-logs", tags=["Audit Logs"])
app.include_router(pdf_render.router, prefix=f"{prefix}/pdf", tags=["PDF"])
app.include_router(license.router, prefix=f"{prefix}/license", tags=["License"])


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "ok", "name": settings.app_name}


class SpaStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or "." in Path(path).name:
                raise
            return await super().get_response("index.html", scope)


_frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", SpaStaticFiles(directory=_frontend_dist), name="frontend")
