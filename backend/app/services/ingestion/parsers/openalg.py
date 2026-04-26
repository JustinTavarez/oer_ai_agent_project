"""Parser for OpenALG (Manifold) project pages.

Verified against live /projects/<slug> pages on 2026-04-22. The page is a
server-rendered React app; the body contains:
  - <title>Title | OpenALG</title>
  - <meta name="description"> with the full abstract
  - A "Metadata" section rendered as inline <span> labels
    (rights, isbn, original publisher, original publisher place,
     publisher, publisher place) followed by their values
  - A Creative Commons license anchor (http or https)

Institution is parsed, not hardcoded: prefer `original publisher`,
falling back to `publisher`. If both are empty, institution stays empty.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CC_LICENSE_HREF_RE = re.compile(r"^https?://creativecommons\.org/licenses/", re.IGNORECASE)
METADATA_LABELS = (
    "rights",
    "isbn",
    "original publisher",
    "original publisher place",
    "publisher",
    "publisher place",
)


@dataclass
class ParsedOpenAlg:
    title: str = ""
    description: str = ""
    license: str = ""
    license_url: str = ""
    institution: str = ""
    isbn: str = ""
    publisher: str = ""
    original_publisher: str = ""
    contributors: List[str] = field(default_factory=list)
    raw_metadata: Dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        """Combine parsed fields into the normalized ``text`` body used downstream."""
        parts: List[str] = []
        if self.title:
            parts.append(f"# {self.title}")
        if self.description:
            parts.append(self.description)
        if self.contributors:
            parts.append("## Contributors\n\n" + ", ".join(self.contributors))

        meta_lines = []
        if self.license:
            line = self.license
            if self.license_url:
                line += f" ({self.license_url})"
            meta_lines.append(f"- License: {line}")
        if self.isbn:
            meta_lines.append(f"- ISBN: {self.isbn}")
        if self.original_publisher:
            meta_lines.append(f"- Original publisher: {self.original_publisher}")
        if self.publisher:
            meta_lines.append(f"- Publisher: {self.publisher}")
        if meta_lines:
            parts.append("## Metadata\n\n" + "\n".join(meta_lines))

        return "\n\n".join(parts).strip()


def parse(html: str) -> ParsedOpenAlg:
    soup = BeautifulSoup(html, "lxml")
    result = ParsedOpenAlg()

    result.title = _extract_title(soup)
    result.description = _extract_description(soup)
    result.license, result.license_url = _extract_license(soup)

    labels = _extract_labels(soup)
    result.raw_metadata = labels
    result.isbn = labels.get("isbn", "")
    result.publisher = labels.get("publisher", "")
    result.original_publisher = labels.get("original publisher", "")

    result.institution = result.original_publisher or result.publisher or ""

    result.contributors = _extract_contributors(soup)

    return result


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        t = soup.title.string.strip()
        t = re.sub(r"\s*\|\s*OpenALG\s*$", "", t, flags=re.IGNORECASE)
        if t:
            return t

    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _extract_description(soup: BeautifulSoup) -> str:
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()

    og = soup.find("meta", attrs={"property": "og:description"})
    if og and og.get("content"):
        return og["content"].strip()

    longest = ""
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if len(t) > len(longest):
            longest = t
    return longest if len(longest) > 120 else ""


def _extract_license(soup: BeautifulSoup) -> tuple[str, str]:
    best_text = ""
    best_href = ""
    for a in soup.find_all("a", href=True):
        if not CC_LICENSE_HREF_RE.match(a["href"]):
            continue
        text = a.get_text(" ", strip=True)
        if text and not best_text:
            best_text = text
            best_href = a["href"]
        elif not best_href:
            best_href = a["href"]

    if not best_text and best_href:
        m = re.search(r"/licenses/([a-z\-]+)/(\d+\.\d+)", best_href)
        if m:
            code = m.group(1).upper().replace("-", "-")
            best_text = f"CC {code} {m.group(2)}"

    return best_text, best_href


def _extract_labels(soup: BeautifulSoup) -> Dict[str, str]:
    out: Dict[str, str] = {}
    label_set = {lbl.lower() for lbl in METADATA_LABELS}

    for span in soup.find_all("span"):
        raw = span.string
        if raw is None:
            continue
        key = raw.strip().lower()
        if key not in label_set:
            continue

        parent = span.parent
        if parent is None:
            continue
        full = parent.get_text(" ", strip=True)
        pattern = r"^" + re.escape(raw.strip()) + r"\s*"
        value = re.sub(pattern, "", full, count=1, flags=re.IGNORECASE).strip()
        value = value.rstrip(".").strip()
        if value and key not in out:
            out[key] = value

    return out


def _extract_contributors(soup: BeautifulSoup) -> List[str]:
    """Best-effort: contributor blocks use 'Author'/'Contributor' roles inline.

    We do not assert structure here — if the heuristic finds nothing, we return
    an empty list rather than inventing names.
    """
    names: List[str] = []
    seen: set[str] = set()
    role_words = {"author", "contributor", "editor", "translator"}

    for tag in soup.find_all(["li", "div", "span"]):
        text = tag.get_text(" ", strip=True)
        if not text or len(text) > 160:
            continue
        lower = text.lower()
        if not any(w in lower for w in role_words):
            continue
        cleaned = re.sub(
            r"\b(Author|Contributor|Editor|Translator)\b",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()
        if 2 < len(cleaned) < 80 and cleaned not in seen:
            seen.add(cleaned)
            names.append(cleaned)
        if len(names) >= 10:
            break
    return names
