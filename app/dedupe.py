"""Cue dedupe: same cue_type + token-Jaccard > 0.6 within window → duplicate."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


def _window_s() -> float:
    try:
        return float(os.getenv("CUE_DEDUPE_WINDOW_S", "20"))
    except ValueError:
        return 20.0


_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> set[str]:
    return set(_TOKEN.findall((text or "").lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


@dataclass
class DedupeState:
    """Recent notified cues for one session."""

    recent: list[tuple[float, str, str]] = field(default_factory=list)
    # (t, cue_type, cue text)

    def is_duplicate(self, t: float, cue_type: str, cue: str) -> bool:
        if cue_type == "none":
            return False
        window = _window_s()
        self.recent = [(tt, ct, c) for tt, ct, c in self.recent if t - tt <= window]
        cue_toks = tokens(cue)
        for tt, ct, c in self.recent:
            if ct != cue_type:
                continue
            if jaccard(cue_toks, tokens(c)) > 0.6:
                return True
        return False

    def remember(self, t: float, cue_type: str, cue: str) -> None:
        if cue_type == "none":
            return
        self.recent.append((t, cue_type, cue))


def decide_notified(
    *,
    should_notify: bool,
    confidence: float,
    cue_type: str,
    cue: str,
    t: float,
    state: DedupeState,
) -> bool:
    """notified = should_notify && conf ≥ 0.6 && !dup; cue_type none never notified."""
    if cue_type == "none":
        return False
    if not should_notify or confidence < 0.6:
        return False
    if state.is_duplicate(t, cue_type, cue):
        return False
    state.remember(t, cue_type, cue)
    return True
