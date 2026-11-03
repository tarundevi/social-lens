"""Dedupe: repeat wave suppressed; new question shown."""

from __future__ import annotations

from app.dedupe import DedupeState, decide_notified, jaccard, tokens


def test_jaccard_basic():
    assert jaccard(tokens("Someone is waving at you"), tokens("Someone is waving at you")) == 1.0
    assert jaccard(tokens("a b c"), tokens("a b d")) == 0.5


def test_repeat_wave_suppressed():
    state = DedupeState()
    n1 = decide_notified(
        should_notify=True,
        confidence=0.88,
        cue_type="greeting_gesture",
        cue="Someone is waving at you",
        t=61.0,
        state=state,
    )
    assert n1 is True
    n2 = decide_notified(
        should_notify=True,
        confidence=0.85,
        cue_type="greeting_gesture",
        cue="Someone is waving at you",
        t=64.0,
        state=state,
    )
    assert n2 is False


def test_new_question_shown():
    state = DedupeState()
    assert decide_notified(
        should_notify=True,
        confidence=0.92,
        cue_type="question_to_you",
        cue="They asked you to dinner Friday",
        t=15.0,
        state=state,
    )
    assert decide_notified(
        should_notify=True,
        confidence=0.9,
        cue_type="question_to_you",
        cue="They asked when you are free tomorrow",
        t=20.0,
        state=state,
    )


def test_none_never_notified():
    state = DedupeState()
    assert (
        decide_notified(
            should_notify=True,
            confidence=0.99,
            cue_type="none",
            cue="No cue",
            t=1.0,
            state=state,
        )
        is False
    )


def test_low_confidence_not_notified():
    state = DedupeState()
    assert (
        decide_notified(
            should_notify=True,
            confidence=0.5,
            cue_type="greeting_gesture",
            cue="wave",
            t=1.0,
            state=state,
        )
        is False
    )
