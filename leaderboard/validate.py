#!/usr/bin/env python3
"""
ATFD Benchmark — Submission Validator

Usage:
    python validate.py <submission.json>

Validates a submission JSON file against leaderboard/schema.json.
Exits 0 on success, 1 on validation error.
"""

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("✗ Missing dependency: jsonschema. Install with: pip install jsonschema")
    sys.exit(1)


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"✗ File not found: {path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON in {path}: {e}")
        sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python validate.py <submission.json>")
        sys.exit(1)

    submission_path = Path(sys.argv[1])
    schema_path = Path(__file__).parent / "schema.json"

    schema = load_json(schema_path)
    submission = load_json(submission_path)

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(submission), key=lambda e: list(e.absolute_path))

    if not errors:
        print(f"✓ Valid — {submission_path}")
        sys.exit(0)
    else:
        print(f"✗ Invalid — {submission_path}")
        for error in errors:
            path = " → ".join(str(p) for p in error.absolute_path) if error.absolute_path else "(root)"
            print(f"  • [{path}] {error.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
