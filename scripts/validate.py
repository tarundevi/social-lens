"""Validate session JSONL files against Graption events.schema.json (v1.2) + social_cue.schema.json.

Usage: python scripts/validate.py [file.jsonl ...]      (default: data/sample_session.jsonl)

Each line is either a replay envelope {"_replay_t": t, "event": {...}} or a bare event.
type == "social_cue" -> social_cue.schema.json; everything else -> events.schema.json.
Schemas are read from schemas/ (minute-0 contract freeze), falling back to reference/ or
docs/reference/. If the Graption base schema is missing, non-social_cue events are reported as
"unchecked" (not counted as valid).
Exit code: 0 if nothing invalid, 1 otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIRS = [ROOT / "schemas", ROOT / "reference", ROOT / "docs" / "reference"]
BASE_SCHEMA = "events.schema.json"
CUE_SCHEMA = "social_cue.schema.json"


def find_schema(name: str) -> Path | None:
    for d in SCHEMA_DIRS:
        if (d / name).is_file():
            return d / name
    return None


def load_validator(name: str) -> Draft202012Validator | None:
    path = find_schema(name)
    if path is None:
        return None
    return Draft202012Validator(json.loads(path.read_text()), format_checker=FormatChecker())


def iter_events(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Yield (line number, event), unwrapping the replay envelope if present."""
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        yield n, row["event"] if "_replay_t" in row and "event" in row else row


class Checker:
    def __init__(self) -> None:
        self.base = load_validator(BASE_SCHEMA)
        self.cue = load_validator(CUE_SCHEMA)

    def errors(self, ev: dict[str, Any]) -> list[str] | None:
        """Error messages for one event, or None if its schema is unavailable."""
        v = self.cue if ev.get("type") == "social_cue" else self.base
        if v is None:
            return None
        return [e.message for e in v.iter_errors(ev)]


def validate_file(path: Path, checker: Checker | None = None) -> dict[str, Any]:
    """Return {"counts": {type: n}, "invalid": [(line, msg)], "unchecked": n}."""
    checker = checker or Checker()
    counts: dict[str, int] = {}
    invalid: list[tuple[int, str]] = []
    unchecked = 0
    for n, ev in iter_events(path):
        t = ev.get("type", "?")
        counts[t] = counts.get(t, 0) + 1
        errs = checker.errors(ev)
        if errs is None:
            unchecked += 1
        elif errs:
            invalid.append((n, errs[0][:200]))
    return {"counts": counts, "invalid": invalid, "unchecked": unchecked}


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] or [ROOT / "data/sample_session.jsonl"]
    checker = Checker()
    if checker.base is None:
        print(f"WARNING: {BASE_SCHEMA} not found in schemas/; Graption events are unchecked")
    if checker.cue is None:
        print(f"WARNING: {CUE_SCHEMA} not found; social_cue events are unchecked")
    total_bad = 0
    for path in paths:
        res = validate_file(path, checker)
        for n, msg in res["invalid"]:
            print(f"{path}:{n}: {msg}")
        total_bad += len(res["invalid"])
        print(f"{path}: {res['counts']} invalid: {len(res['invalid'])} unchecked: {res['unchecked']}")
    return 1 if total_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
