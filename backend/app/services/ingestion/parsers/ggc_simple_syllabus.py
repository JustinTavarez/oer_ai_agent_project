"""Parser for GGC Simple Syllabus public pages.

No URLs were available when this was first written, so the parser is
intentionally defensive:

1. Try the rendered HTML DOM first — look for common syllabus section
   headings (Course Description, Learning Outcomes, Required Materials,
   Grading, Policies, Schedule).
2. Fall back to readability-lxml's main-content extraction if no headings
   are found.
3. Extract any CC license link (http or https).
4. Pull title from <title>, <h1>, or the <meta property="og:title"> tag.

Pages that yield fewer than 200 characters of useful text should be logged
to data/normalized/parse_failures.jsonl by the caller.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

try:
    from readability import Document as _ReadabilityDoc
except ImportError:
    _ReadabilityDoc = None

logger = logging.getLogger(__name__)

CC_LICENSE_HREF_RE = re.compile(r"^https?://creativecommons\.org/licenses/", re.IGNORECASE)

SECTION_HEADINGS = (
    "course description",
    "course overview",
    "course objectives",
    "learning outcomes",
    "student learning outcomes",
    "required materials",
    "required texts",
    "textbook",
    "textbooks",
    "grading",
    "grading policy",
    "grade distribution",
    "course policies",
    "policies",
    "attendance",
    "academic integrity",
    "schedule",
    "course schedule",
    "weekly schedule",
    "assessments",
    "assignments",
)

TERM_RE = re.compile(r"\b(Fall|Spring|Summer|Winter)\s+(20\d{2})\b", re.IGNORECASE)


@dataclass
class ParsedGgcSyllabus:
    title: str = ""
    instructor: str = ""
    term: str = ""
    sections: Dict[str, str] = field(default_factory=dict)
    fallback_body: str = ""
    license: str = ""
    license_url: str = ""
    institution: str = "Georgia Gwinnett College"

    def text(self) -> str:
        parts: List[str] = []
        if self.title:
            parts.append(f"# {self.title}")
        header_bits = []
        if self.instructor:
            header_bits.append(f"Instructor: {self.instructor}")
        if self.term:
            header_bits.append(f"Term: {self.term}")
        if self.institution:
            header_bits.append(f"Institution: {self.institution}")
        if header_bits:
            parts.append("\n".join(header_bits))

        for heading, body in self.sections.items():
            if not body.strip():
                continue
            parts.append(f"## {heading.title()}\n\n{body.strip()}")

        if not self.sections and self.fallback_body:
            parts.append(self.fallback_body.strip())

        if self.license:
            line = self.license
            if self.license_url:
                line += f" ({self.license_url})"
            parts.append(f"## License\n\n{line}")

        return "\n\n".join(p for p in parts if p).strip()

    def usable(self) -> bool:
        """Return True when there is enough parsed text to be worth embedding."""
        return len(self.text()) >= 200


def parse(html: str) -> ParsedGgcSyllabus:
    soup = BeautifulSoup(html, "lxml")
    result = ParsedGgcSyllabus()

    result.title = _extract_title(soup)
    result.term = _extract_term(soup)
    result.instructor = _extract_instructor(soup)
    result.license, result.license_url = _extract_license(soup)
    result.sections = _extract_sections(soup)

    if not result.sections:
        result.fallback_body = _readability_fallback(html)

    return result


def _extract_title(soup: BeautifulSoup) -> str:
    og = soup.find("meta", attrs={"property": "og:title"})
    if og and og.get("content"):
        return og["content"].strip()
    if soup.title and soup.title.string:
        return re.sub(r"\s*\|\s*Simple Syllabus.*$", "", soup.title.string.strip(), flags=re.IGNORECASE)
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _extract_term(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)[:2000]
    m = TERM_RE.search(text)
    if m:
        return f"{m.group(1).title()} {m.group(2)}"
    return ""


def _extract_instructor(soup: BeautifulSoup) -> str:
    for el in soup.find_all(string=re.compile(r"\b(Instructor|Professor)\b", re.IGNORECASE)):
        parent = el.parent
        if parent is None:
            continue
        text = parent.get_text(" ", strip=True)
        m = re.search(r"(?:Instructor|Professor)\s*[:\-]\s*([^\n|]{3,80})", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _extract_license(soup: BeautifulSoup) -> tuple[str, str]:
    for a in soup.find_all("a", href=True):
        if CC_LICENSE_HREF_RE.match(a["href"]):
            return a.get_text(" ", strip=True) or "Creative Commons License", a["href"]
    return "", ""


def _extract_sections(soup: BeautifulSoup) -> Dict[str, str]:
    """Walk through heading tags and treat following siblings as that section's body."""
    sections: Dict[str, str] = {}
    heading_set = set(SECTION_HEADINGS)

    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        label = h.get_text(" ", strip=True).lower().rstrip(":").strip()
        if not label:
            continue
        match = next((name for name in heading_set if label == name or label.startswith(name)), None)
        if match is None:
            continue

        body_chunks: List[str] = []
        for sib in h.next_siblings:
            name = getattr(sib, "name", None)
            if name in {"h1", "h2", "h3", "h4"}:
                break
            text = sib.get_text(" ", strip=True) if hasattr(sib, "get_text") else str(sib).strip()
            if text:
                body_chunks.append(text)
        body = "\n\n".join(body_chunks).strip()
        if body:
            sections[match] = body

    return sections


def _readability_fallback(html: str) -> str:
    if _ReadabilityDoc is None:
        return ""
    try:
        doc = _ReadabilityDoc(html)
        summary = doc.summary(html_partial=True)
    except Exception as exc:
        logger.warning("readability fallback failed: %s", exc)
        return ""
    soup = BeautifulSoup(summary, "lxml")
    return soup.get_text("\n\n", strip=True)
