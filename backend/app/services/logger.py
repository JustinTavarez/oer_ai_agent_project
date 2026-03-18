import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings


def log_search_request(
    query: str,
    course_code: Optional[str],
    source: Optional[str],
    top_k: int,
    result_count: int,
    grounded: bool,
    message: str = "",
) -> None:
    log_path = Path(settings.search_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "course_code": course_code or "",
        "source": source or "",
        "top_k": top_k,
        "result_count": result_count,
        "grounded": grounded,
        "message": message,
    }

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
