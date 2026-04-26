"""Parse fetched raw HTML into normalized records.jsonl.

Usage (from backend/):
    python -m scripts.parse_and_normalize

Reads from  data/raw/{openalg,ggc_syllabi}/*.html
Writes:
    data/normalized/records.jsonl         (unified schema)
    data/normalized/parse_failures.jsonl  (reasons for any skipped pages)
"""

from __future__ import annotations

import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingestion.normalize import (  # noqa: E402
    normalize_from_raw,
    write_failures,
    write_records,
)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    project_root = Path(__file__).resolve().parent.parent.parent
    raw_root = project_root / "data" / "raw"
    out_dir = project_root / "data" / "normalized"
    records_path = out_dir / "records.jsonl"
    failures_path = out_dir / "parse_failures.jsonl"

    print(f"raw root: {raw_root}")
    result = normalize_from_raw(raw_root)

    n_rec = write_records(result.records, records_path)
    n_fail = write_failures(result.failures, failures_path)

    source_counts = Counter(r.source for r in result.records)
    course_counts = Counter(r.course_code for r in result.records)

    print(f"\nwrote {n_rec} records -> {records_path}")
    print(f"wrote {n_fail} failures -> {failures_path}")
    print(f"records by source: {dict(source_counts)}")
    print(f"records by course_code: {dict(course_counts)}")
    if result.failures:
        print("failure reasons:")
        reasons = Counter(f.reason for f in result.failures)
        for reason, count in reasons.most_common():
            print(f"  {count:3d}  {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
