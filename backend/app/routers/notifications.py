from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import DbSession, Pagination, require_permission
from app.core.database import SessionLocal
from app.core.exceptions import UnauthorizedError
from app.crud import user as user_crud
from app.models import User
from app.realtime.notifications import notification_hub
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.notification import NotificationAcknowledgeRequest, NotificationResponse
from app.services.auth import auth_service
from app.services.notification import notification_service

router = APIRouter()


@router.websocket("/ws")
async def notifications_socket(websocket: WebSocket, token: str = Query(default="")) -> None:
    await websocket.accept()
    db = SessionLocal()
    try:
        user = auth_service.user_from_access_token(db, token)
        if not user.is_active:
            raise UnauthorizedError("User account is inactive")
        if "notifications:read" not in set(user_crud.list_permissions(user)):
            raise UnauthorizedError("Insufficient permissions")
        user_id = user.id
    except Exception:
        await websocket.close(code=1008)
        return
    finally:
        db.close()

    notification_hub.register(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)


@router.get("", response_model=PaginatedResponse[NotificationResponse])
def list_notifications(
    db: DbSession,
    pagination: Pagination,
    current_user: User = Depends(require_permission("notifications:read")),
    unacknowledged_only: bool = Depends(lambda: False),
) -> PaginatedResponse[NotificationResponse]:
    items, total = notification_service.list_for_user(
        db,
        current_user,
        page=pagination["page"],
        page_size=pagination["page_size"],
        unacknowledged_only=unacknowledged_only,
    )
    return PaginatedResponse.build(
        [NotificationResponse.model_validate(item) for item in items],
        total,
        pagination["page"],
        pagination["page_size"],
    )


@router.get("/unread-count", response_model=dict)
def unread_notification_count(
    db: DbSession,
    current_user: User = Depends(require_permission("notifications:read")),
) -> dict:
    return {"count": notification_service.unacknowledged_count(db, current_user)}


@router.post("/acknowledge", response_model=MessageResponse)
def acknowledge_notifications(
    payload: NotificationAcknowledgeRequest,
    db: DbSession,
    current_user: User = Depends(require_permission("notifications:update")),
) -> MessageResponse:
    count = notification_service.acknowledge(db, current_user, payload.ids)
    return MessageResponse(message=f"Acknowledged {count} notification(s)")
