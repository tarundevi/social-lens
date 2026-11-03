"""In-memory sessions + asyncio broadcast for WebSocket clients."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.dedupe import DedupeState


@dataclass
class Session:
    session_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    dedupe: DedupeState = field(default_factory=DedupeState)
    analyze_busy: bool = False
    subscribers: list[asyncio.Queue] = field(default_factory=list)


class Store:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, prefix: str = "live") -> Session:
        sid = f"{prefix}-{uuid.uuid4().hex[:8]}"
        sess = Session(session_id=sid)
        self._sessions[sid] = sess
        return sess

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

    def ensure(self, session_id: str) -> Session:
        sess = self._sessions.get(session_id)
        if sess is None:
            sess = Session(session_id=session_id)
            self._sessions[session_id] = sess
        return sess

    async def append(self, session_id: str, event: dict[str, Any], hud: dict | None) -> None:
        sess = self.ensure(session_id)
        sess.events.append(event)
        msg = {"event": event, "hud": hud}
        dead: list[asyncio.Queue] = []
        for q in sess.subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        if dead:
            sess.subscribers = [q for q in sess.subscribers if q not in dead]

    def subscribe(self, session_id: str) -> asyncio.Queue:
        sess = self.ensure(session_id)
        q: asyncio.Queue = asyncio.Queue(maxsize=64)
        sess.subscribers.append(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue) -> None:
        sess = self._sessions.get(session_id)
        if not sess:
            return
        sess.subscribers = [x for x in sess.subscribers if x is not q]


store = Store()
