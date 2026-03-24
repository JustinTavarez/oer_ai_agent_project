import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from app.config import settings


def log_search_request(
    query: str,
    course_code: Optional[str],
    source: Optional[str],
    top_k: int,
    result_count: int,
    grounded: bool,
    message: str = "",
    skipped_hits: int = 0,
    skip_reasons: Optional[Dict[str, int]] = None,
) -> None:
    log_path = Path(settings.search_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry: Dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "course_code": course_code or "",
        "source": source or "",
        "top_k": top_k,
        "result_count": result_count,
        "grounded": grounded,
        "message": message,
    }

    if skipped_hits:
        entry["skipped_hits"] = skipped_hits
    if skip_reasons:
        entry["skip_reasons"] = skip_reasons

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
