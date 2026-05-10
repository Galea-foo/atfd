"""Download tau-bench result files from GitHub."""
import json
import os
from pathlib import Path
from urllib.request import urlretrieve

DATA_DIR = Path(__file__).parent / "data"
BASE_URL = "https://raw.githubusercontent.com/sierra-research/tau2-bench/main/data/tau2"

RESULT_FILES = [
    "results/final/gpt-4.1-2025-04-14_retail_default_gpt-4.1-2025-04-14_4trials.json",
    "results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json",
    "results/final/gpt-4.1-2025-04-14_telecom_default_gpt-4.1-2025-04-14_4trials.json",
]

DOMAIN_FILES = [
    "domains/retail/tasks.json",
    "domains/retail/policy.md",
    "domains/airline/tasks.json",
    "domains/airline/policy.md",
    "domains/telecom/tasks.json",
    "domains/telecom/policy.md",
]


def download():
    for rel_path in RESULT_FILES + DOMAIN_FILES:
        dest = DATA_DIR / rel_path
        if dest.exists():
            print(f"  skip {rel_path} (exists)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        url = f"{BASE_URL}/{rel_path}"
        print(f"  fetch {rel_path}...")
        try:
            urlretrieve(url, dest)
        except Exception as e:
            print(f"  ERROR: {e}")


if __name__ == "__main__":
    print("Downloading tau-bench data...")
    download()
    print("Done.")
