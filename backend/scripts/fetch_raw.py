"""Fetch raw HTML for manifest entries into data/raw/.

Usage (from backend/):
    python -m scripts.fetch_raw --manifest ../data/manifests/openalg.yaml
    python -m scripts.fetch_raw --manifest ../data/manifests/ggc_syllabi.yaml
    python -m scripts.fetch_raw --all-manifests
    python -m scripts.fetch_raw --all-manifests --force   # ignore If-None-Match caches

Idempotent: reruns use If-None-Match / If-Modified-Since when the server
exposes those headers and skip writing new HTML on 304. TODO rows in the
manifest are reported but not fetched.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ingestion.fetcher import (  # noqa: E402
    build_client,
    build_limiter,
    fetch_entry,
)
from app.services.ingestion.manifest import load_manifest  # noqa: E402

DEFAULT_MANIFESTS = [
    Path("../data/manifests/openalg.yaml"),
    Path("../data/manifests/ggc_syllabi.yaml"),
]
RAW_ROOT = Path("../data/raw")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, action="append", default=[])
    ap.add_argument("--all-manifests", action="store_true")
    ap.add_argument("--force", action="store_true", help="ignore cache, refetch everything")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    manifests = list(args.manifest)
    if args.all_manifests or not manifests:
        manifests = list(DEFAULT_MANIFESTS)

    raw_root = (Path(__file__).resolve().parent.parent / RAW_ROOT).resolve()
    raw_root.mkdir(parents=True, exist_ok=True)

    overall = Counter()
    client = build_client()
    limiter = build_limiter()

    try:
        for manifest_path in manifests:
            resolved = (Path(__file__).resolve().parent.parent / manifest_path).resolve()
            print(f"\n=== manifest: {resolved} ===")
            loaded = load_manifest(resolved)
            if loaded.errors:
                print("manifest errors:")
                for e in loaded.errors:
                    print(f"  - {e}")
            print(f"fetchable entries: {len(loaded.entries)}  | skipped TODO: {len(loaded.skipped_todo)}")

            per_manifest = Counter()
            for entry in loaded.entries:
                outcome = fetch_entry(entry, raw_root, client, limiter, force=args.force)
                overall[outcome.status] += 1
                per_manifest[outcome.status] += 1
                label = f"[{outcome.status}]"
                if outcome.http_status is not None:
                    label += f" ({outcome.http_status})"
                print(f"  {label} {entry.course_code} :: {entry.url}")
                if outcome.status == "error":
                    print(f"      error: {outcome.error}")

            if loaded.skipped_todo:
                print("skipped TODO rows:")
                for e in loaded.skipped_todo:
                    print(f"  - {e.course_code} / {e.term}  (source: {e.source})")

            print(f"summary: {dict(per_manifest)}")
    finally:
        client.close()

    print(f"\noverall: {dict(overall)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
