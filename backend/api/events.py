from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from backend.db import delete_event, get_event as get_saved_event, list_events, save_event
from backend.schemas.event import EventRequest

from backend.engine.package_data_loader import load_package_data
from backend.engine.json_serializer import to_json_safe

router = APIRouter(prefix="/api/events", tags=["Events"])

@router.get("")
def get_saved_events():
    return {"events": to_json_safe(list_events()), "storage": "sqlite"}

@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(request: EventRequest):
    event_id = f"USER-{uuid4().hex[:12].upper()}"
    return {"event": to_json_safe(save_event(event_id, request.model_dump(mode="json"))), "storage": "sqlite"}

@router.put("/{event_id}")
def update_event(event_id: str, request: EventRequest):
    if not get_saved_event(event_id):
        raise HTTPException(status_code=404, detail="Saved event not found")
    return {"event": to_json_safe(save_event(event_id, request.model_dump(mode="json"))), "storage": "sqlite"}

@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_event(event_id: str):
    if not delete_event(event_id):
        raise HTTPException(status_code=404, detail="Saved event not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{event_id}")
def get_event(event_id: str):
    saved = get_saved_event(event_id)
    if saved:
        return {"event": to_json_safe(saved), "data_origin": "sqlite_user_event", "is_vendor_confirmed": False}
    events_df, _ = load_package_data()

    if "event_id" not in events_df.columns:
        raise HTTPException(
            status_code=500,
            detail="Event ID column not found"
        )

    matches = events_df[
        events_df["event_id"].astype(str) == event_id
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    event = matches.iloc[0].to_dict()

    return {
        "event": to_json_safe(event),
        "data_origin": "synthetic_simulation",
        "is_vendor_confirmed": False
    }


