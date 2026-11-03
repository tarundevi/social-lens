"""Validate every event in a session file against Graption's schemas/events.schema.json (v1.2)."""
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "schemas/events.schema.json").read_text())
v = Draft202012Validator(schema, format_checker=FormatChecker())
path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data/sample_session.jsonl"
bad = 0
counts = {}
for n, line in enumerate(path.read_text().splitlines(), 1):
    ev = json.loads(line)["event"]
    counts[ev["type"]] = counts.get(ev["type"], 0) + 1
    errs = list(v.iter_errors(ev))
    if errs:
        bad += 1
        print(f"line {n}: {errs[0].message[:200]}")
print(counts, "invalid:", bad)
sys.exit(1 if bad else 0)
