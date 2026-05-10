"""Download tau-bench (tau2-bench) result and domain files from GitHub.

Usage:
    python datasets/tau_bench/download.py [--data-dir PATH] [--force]

Files are saved under DATA_DIR (defaults to this script's directory).
Already-downloaded files are skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

# Root of the tau2-bench data tree on GitHub (main branch, raw content).
_BASE_URL = "https://raw.githubusercontent.com/sierra-research/tau2-bench/main/data/tau2"

# Result files — one per domain, gpt-4.1 4-trial runs.
_RESULT_FILES = [
    "results/final/gpt-4.1-2025-04-14_retail_default_gpt-4.1-2025-04-14_4trials.json",
    "results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json",
    "results/final/gpt-4.1-2025-04-14_telecom_default_gpt-4.1-2025-04-14_4trials.json",
]

# Domain task & policy files.
_DOMAIN_FILES = [
    "domains/retail/tasks.json",
    "domains/retail/policy.md",
    "domains/airline/tasks.json",
    "domains/airline/policy.md",
    "domains/telecom/tasks.json",
    "domains/telecom/policy.md",
]

_ALL_FILES = _RESULT_FILES + _DOMAIN_FILES


def download(data_dir: Path, force: bool = False) -> None:
    """Download all tau-bench files into *data_dir*."""
    data_dir = data_dir.resolve()
    print(f"Saving to: {data_dir}")

    ok = 0
    errors = 0
    for rel_path in _ALL_FILES:
        dest = data_dir / rel_path
        if dest.exists() and not force:
            print(f"  skip  {rel_path}  (already downloaded)")
            ok += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{_BASE_URL}/{rel_path}"
        print(f"  fetch {rel_path} ...", end="", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
            print(" OK")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            errors += 1

    print(f"\nDone: {ok} files OK, {errors} errors.")
    if errors:
        sys.exit(1)


def main() -> None:
    default_dir = Path(__file__).parent

    parser = argparse.ArgumentParser(description="Download tau-bench dataset files.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=default_dir,
        help=f"Destination directory (default: {default_dir})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even if they already exist.",
    )
    args = parser.parse_args()
    download(args.data_dir, force=args.force)


if __name__ == "__main__":
    main()
