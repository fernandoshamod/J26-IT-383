"""
Integration layer (proposal Section 4.3): event bus, audit log,
notifications, and the Component 4 interface.

Section 4.3: "Components publish state changes to the bus and subscribe to
the changes relevant to them rather than calling one another directly.
This keeps each component independently testable while allowing a change
in one to propagate to the others, and it means a component can be
developed against a published interface before its sibling is complete."

That last sentence is exactly how Component 4 is handled here: Component 3
PUBLISHES a cost signal on the topic `cost_signal.issued` (FR-14) and does
not know or care who consumes it. `Component4Stub` is a stand-in
subscriber that records what it receives; the real financial component
replaces it by subscribing to the same topic, with no change to Component 3.

The bus is in-process and synchronous (a subscriber runs inside
`publish`). That is enough for one process; swapping it for a networked
broker (e.g. Redis pub/sub) would only change this class, not its callers.
"""

from __future__ import annotations

import itertools
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# Topics Component 3 publishes. Kept in one place so the interface other
# components develop against is explicit.
TOPIC_SCHEDULE_PLANNED = "schedule.planned"
TOPIC_CHECK_IN = "checkin.received"
TOPIC_DISRUPTION = "disruption.detected"
TOPIC_DISRUPTION_ABSORBED = "disruption.absorbed"
TOPIC_PROPOSAL = "proposal.created"
TOPIC_PROPOSAL_REJECTED = "proposal.rejected"
TOPIC_PROPOSAL_SUPERSEDED = "proposal.superseded"
TOPIC_SCHEDULE_CHANGED = "schedule.changed"
TOPIC_COST_SIGNAL = "cost_signal.issued"  # FR-14: consumed by Component 4


def to_jsonable(value: Any) -> Any:
    """Dataclasses, enums, tuples and sets -> plain JSON types."""
    if is_dataclass(value) and not isinstance(value, type):
        return to_jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in value]
    return value


@dataclass(frozen=True)
class BusMessage:
    sequence: int
    topic: str
    payload: dict
    published_at: str  # wall-clock UTC, ISO 8601


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[BusMessage], None]]] = defaultdict(list)
        self._sequence = itertools.count(1)
        self.history: list[BusMessage] = []

    def subscribe(self, topic: str, handler: Callable[[BusMessage], None]) -> None:
        """`topic` "*" receives every message."""
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, payload: dict) -> BusMessage:
        message = BusMessage(next(self._sequence), topic, to_jsonable(payload),
                             datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self.history.append(message)
        for handler in self._subscribers[topic] + self._subscribers["*"]:
            handler(message)
        return message


@dataclass(frozen=True)
class AuditEntry:
    sequence: int
    recorded_at: str       # wall-clock UTC: when the system recorded it
    event_minute: int      # position on the event timeline (see models.py)
    kind: str              # e.g. "disruption.detected", "schedule.changed"
    actor: str             # "system", "planner:<name>", "checkin:<activity>"
    summary: str           # one human-readable line
    details: dict = field(default_factory=dict)


class AuditLog:
    """FR-16: append-only, timestamped log of every detection, simulation
    and schedule change. Entries are never edited or removed. If `path` is
    given, each entry is also appended to a JSON-lines file as it happens,
    so the record survives a restart (NFR-03)."""

    def __init__(self, path: Path | None = None) -> None:
        self._entries: list[AuditEntry] = []
        self._path = path
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_minute: int, kind: str, actor: str, summary: str,
               details: dict | None = None) -> AuditEntry:
        entry = AuditEntry(len(self._entries) + 1, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           event_minute, kind, actor, summary, to_jsonable(details or {}))
        self._entries.append(entry)
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(to_jsonable(entry)) + "\n")
        return entry

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        return tuple(self._entries)  # read-only view: callers can't alter history


@dataclass(frozen=True)
class Notification:
    """FR-15: one message to one affected staff member or vendor."""

    resource_id: str
    resource_name: str
    activity_id: str
    message: str
    event_minute: int


class NotificationService:
    """Subscribes to `schedule.changed` and writes one notification per
    (resource, moved activity). Delivery (SMS, push, WhatsApp) is a
    transport detail outside this research component; the outbox is what
    a delivery adapter would send."""

    def __init__(self, bus: EventBus, resource_names: dict[str, str]) -> None:
        self.outbox: list[Notification] = []
        self._names = resource_names
        bus.subscribe(TOPIC_SCHEDULE_CHANGED, self._on_schedule_changed)

    def _on_schedule_changed(self, message: BusMessage) -> None:
        for change in message.payload["changes"]:
            for rid in change["resource_ids"]:
                self.outbox.append(Notification(
                    resource_id=rid,
                    resource_name=self._names.get(rid, rid),
                    activity_id=change["activity_id"],
                    message=(f"Schedule change: {change['activity_name']} now "
                             f"{_hhmm(change['new_start'])}-{_hhmm(change['new_end'])} "
                             f"(was {_hhmm(change['old_start'])}-{_hhmm(change['old_end'])})."),
                    event_minute=message.payload["event_minute"],
                ))


class Component4Stub:
    """Stand-in for Component 4 (financial intelligence). Records every
    cost signal it receives; the real component subscribes to the same
    topic with the same payload. Deliberately computes NO money amount —
    costing is Component 4's responsibility (proposal Table 8)."""

    def __init__(self, bus: EventBus) -> None:
        self.received: list[dict] = []
        bus.subscribe(TOPIC_COST_SIGNAL, lambda m: self.received.append(m.payload))


def _hhmm(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"
