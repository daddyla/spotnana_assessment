"""Print the data-quality report for a flights dataset.

Usage (from backend/):
    python -m scripts.audit_dataset [path/to/flights.json]

Uses exactly the same loader as the API, so what you see here is what the
service will serve.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.core.config import get_settings
from app.data.loader import load_dataset


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.ERROR)  # the report below replaces the log lines
    path = Path(argv[1]) if len(argv) > 1 else get_settings().data_path
    dataset = load_dataset(path)
    report = dataset.report

    print(f"Dataset: {path}")
    print(f"  {report.summary()}")
    for title, issues in (("Dropped", report.dropped), ("Coerced", report.coerced)):
        print(f"\n{title} ({len(issues)}):")
        for issue in issues or []:
            print(f"  - {issue.entity:<7} {issue.id:<8} {issue.reason}")
        if not issues:
            print("  (none)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
