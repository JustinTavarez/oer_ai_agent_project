import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

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
    log_id: str = "",
    retrieved_doc_count: int = 0,
    final_result_count: int = 0,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    llm_success: bool = False,
    llm_duration_ms: int = 0,
    llm_parse_failures: int = 0,
    fallback_used: bool = False,
    retrieval_duration_ms: int = 0,
    total_duration_ms: int = 0,
    cache_hit: bool = False,
    evaluation_mode: str = "rule_based",
    response_status: str = "success",
    cache_version: str = "",
) -> None:
    log_path = Path(settings.search_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    entry: Dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "log_id": log_id,
        "query": query,
        "course_code": course_code or "",
        "source": source or "",
        "top_k": top_k,
        "result_count": result_count,
        "grounded": grounded,
        "message": message,
        "retrieved_doc_count": retrieved_doc_count,
        "final_result_count": final_result_count,
        "llm_success": llm_success,
        "llm_duration_ms": llm_duration_ms,
        "llm_parse_failures": llm_parse_failures,
        "fallback_used": fallback_used,
        "retrieval_duration_ms": retrieval_duration_ms,
        "total_duration_ms": total_duration_ms,
        "cache_hit": cache_hit,
        "evaluation_mode": evaluation_mode,
        "response_status": response_status,
        "cache_version": cache_version or settings.cache_version,
    }

    if skipped_hits:
        entry["skipped_hits"] = skipped_hits
    if skip_reasons:
        entry["skip_reasons"] = skip_reasons
    if warnings:
        entry["warnings"] = warnings
    if errors:
        entry["errors"] = errors

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
