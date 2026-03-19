from typing import Dict, List, Optional

from app.services.chroma_client import get_collection
from app.services.embeddings import get_embedding


async def search(
    query: str,
    top_k: int = 5,
    course_code: Optional[str] = None,
    source: Optional[str] = None,
    license_filter: Optional[str] = None,
) -> List[Dict]:
    query_embedding = await get_embedding(query)
    collection = get_collection()

    where_filter = _build_where_filter(course_code, source, license_filter)

    kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    results = collection.query(**kwargs)

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output: List[Dict] = []
    for i, doc_id in enumerate(ids):
        meta = metadatas[i] if i < len(metadatas) else {}
        score = 1.0 - distances[i] if i < len(distances) else 0.0
        output.append({
            "id": doc_id,
            "content": documents[i] if i < len(documents) else "",
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "course_code": meta.get("course_code", ""),
            "license": meta.get("license", ""),
            "url": meta.get("url", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "score": round(score, 4),
            "metadata": {
                "resource_type": meta.get("resource_type", ""),
                "subject": meta.get("subject", ""),
                "term": meta.get("term", ""),
                "institution": meta.get("institution", ""),
                "has_accessibility_info": meta.get("has_accessibility_info", False),
                "has_supplementary_materials": meta.get("has_supplementary_materials", False),
            },
        })

    return output


def _build_where_filter(
    course_code: Optional[str],
    source: Optional[str],
    license_filter: Optional[str],
) -> Optional[Dict]:
    conditions: List[Dict] = []

    if course_code and course_code.lower() != "all":
        conditions.append({"course_code": {"$eq": course_code}})
    if source and source.lower() != "all":
        conditions.append({"source": {"$eq": source}})
    if license_filter and license_filter.lower() != "all":
        conditions.append({"license": {"$eq": license_filter}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}
