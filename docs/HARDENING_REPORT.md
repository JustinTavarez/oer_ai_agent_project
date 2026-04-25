# OER AI Agent — Final Hardening Report

This document captures the project state after the final hardening pass:
what changed, what works, what is honest about its limits, and how to demo
it. It supersedes any prior status notes.

---

## 1. Files changed during hardening

### Backend

| File | Change |
| --- | --- |
| `backend/app/services/retrieval.py` | Detect course codes in free-text queries, over-fetch from Chroma, re-rank exact `course_code` matches with a fixed boost, and run a course-code-filtered fallback query when the boost alone cannot surface the canonical resource. Forward `content_kind` from metadata. |
| `backend/app/services/lmstudio.py` | Accept an optional `max_resources` cap so the API can return more cards than the LLM context uses; allow course-matched `metadata_reference` entries to bypass the score threshold; propagate `term` and `content_kind` into the context pack. |
| `backend/app/models/schemas.py` | Add `content_kind`, `term`, `section`, `crn` to `EvaluatedResource` so GGC reference rows carry their identifying metadata to the UI. |
| `backend/app/routes/search.py` | Detect `metadata_reference` rows; render an honest, generic description for them; emit a tailored "open live syllabus" integration tip; parse Section/CRN out of GGC titles; cap the cards returned to the UI to a sensible number while still feeding the LLM a smaller pack. |
| `backend/scripts/validate_search.py` | Call the full `app.services.retrieval.search` pipeline (not raw Chroma) so the validator measures what users actually see. Print boost markers and use boosted scores when scoring top-1 correctness. |
| `backend/scripts/acceptance_demo.py` | New end-to-end acceptance script that hits the live `/search` endpoint for the 8 required courses, a nonsense query, and a cache-hit query, and reports the fields needed for the demo (top result, source, content kind, license/rubric/tips presence, ranking issues). |

### Frontend

| File | Change |
| --- | --- |
| `frontend/src/components/ChatPage.jsx` | Fix the source filter dropdown so the GGC option matches the backend `source` value exactly (`"GGC Simple Syllabus"`). |
| `frontend/src/components/ResourceCard.jsx` | Visually distinguish reference rows (violet border + "Syllabus reference" pill), display Term / Section / CRN, hide rubric and license badges that are not meaningful for metadata-only rows, and rename the link to "Open live syllabus →" for those rows. |

### Why each change was needed

- **Course-code boost + fallback** fixed weak retrieval on bare-code queries
  (HIST 2111, HIST 2112, ITEC 1001, ENGL 1102) without hard-filtering
  natural-language queries.
- **`metadata_reference` end-to-end plumbing** lets us include real GGC
  syllabus links without ever pretending we extracted their body text.
- **Per-card honesty (description / tips / license / rubric defaults)** makes
  every card consistent and presentable, and keeps fallback / debug strings
  out of the user-facing UI.
- **`acceptance_demo.py`** turns Phase 4 into something we can re-run on demand
  before the demo.

---

## 2. Phase 1 — `validate_search` summary (post-boost)

All 8 required courses now rank the correct resource at top-1 on bare course-code
queries. Items that were rescued by the new logic are marked.

| Course | Bare-code top-1 | Mechanism |
| --- | --- | --- |
| ARTS 1100 | OK | Open ALG textbook (natural similarity) |
| ENGL 1101 | OK | Open ALG textbook + GGC reference, course-code boost on top |
| ENGL 1102 | OK (`[BOOST]`) | Course-code re-rank lifted the matching Open ALG entry |
| HIST 2111 | OK (`[BOOST]`) | Course-code re-rank lifted the Yawp ancillary |
| HIST 2112 | OK (`[BOOST]`) | Course-code re-rank lifted the Yawp Vol II ancillary |
| ITEC 1001 | OK (fallback) | Course-code-filtered fallback query (corpus too small for the boost alone) |
| BIOL 1101K | OK | Open ALG lab manual + course-code boost |
| BIOL 1102 | OK | Open ALG lab manual + course-code boost |

Natural-language queries continue to behave as expected (subject-neighbor
behavior preserved, no aggressive hard-filter).

---

## 3. Phase 4 — Final acceptance results

Run via `python -m scripts.acceptance_demo` with the backend up and
`CHROMA_ACTIVE_COLLECTION=oer_resources_real`.

| Test | Top-1 title (excerpt) | Source | License visible | Rubric visible | Tips visible | Ranking issue |
| --- | --- | --- | --- | --- | --- | --- |
| ARTS 1100 (code) | Introduction to Art | Open ALG | yes | yes | yes | none |
| ARTS 1100 (NL) | Introduction to Art | Open ALG | yes | yes | yes | none |
| ENGL 1101 (code) | Composition I curated resources | Open ALG | yes | yes | yes | none |
| ENGL 1101 (NL) | Composition I curated resources | Open ALG | yes | yes | yes | none |
| ENGL 1102 (code) | Composition II OER project | Open ALG | yes | yes | yes | none |
| ENGL 1102 (NL) | Composition II OER project | Open ALG | yes | yes | yes | none |
| HIST 2111 (code) | The American Yawp ancillary | Open ALG | yes | yes | yes | none |
| HIST 2112 (code) | The American Yawp Vol. II ancillary | Open ALG | yes | yes | yes | none |
| ITEC 1001 (code) | Computing Fundamentals curated resources | Open ALG | yes | yes | yes | none (rescued by fallback) |
| BIOL 1101K (code) | Biology 1101K Lab Manual | Open ALG | yes | yes | yes | none |
| BIOL 1102 (code) | Biology 1102 Lab Manual | Open ALG | yes | yes | yes | none |
| Nonsense ("flibberty zonk") | (low-score result, marked clearly) | varies | yes | yes | yes | acceptable — no hard 0-result is shown unless under threshold |
| Repeated query (cache) | identical to first run | — | — | — | — | `_debug.cache_hit = true` confirmed |
| LM Studio down (manual) | n/a | — | — | — | — | `200 OK`, `results=[]`, friendly error string in `errors`, `evaluation_mode = error` |

GGC reference rows verified separately:
- Render with the violet "Syllabus reference" pill.
- Display Term / Section / CRN extracted from the title.
- Show the honest generic description, no synthesized syllabus body.
- Link reads "Open live syllabus →".
- Rubric and license badges are hidden for these rows (not meaningful).

### Failures by priority
- **High** — none.
- **Medium** — natural-language `"history since 1877"` may surface HIST 2111 above HIST 2112 because they are embedding-near; explicitly typing the course code resolves it.
- **Low** — nonsense queries can still return a low-score card above the 0.4 threshold; we keep the threshold low to avoid suppressing real matches.

---

## 4. Phase 5 — Rubric review

| Rubric area | Status | Weakness | Quick fix before demo |
| --- | --- | --- | --- |
| Search & discovery | Strong | Bare-code queries depend on the course-code fallback for tiny corpora (ITEC 1001) | None — explain the boost+fallback briefly in the demo |
| User interface | Strong (React + Tailwind, dark glassmorphism, clear pills, animated transitions) | No mobile QA | None — desktop demo |
| Technical reliability | Strong (graceful LM-down, persistent Chroma, response cache, 65 pytest tests passing) | Cache is in-memory, single-process | None — call this out as a known limitation |
| Relevance & comprehensiveness | Good (8/8 required courses with real resources, 4 GGC syllabus references) | 12 GGC (course, term) combos are not publicly indexed | None — explain in known limitations |
| Interactivity & engagement | Good (chat history, retry, expandable rubric per card, source/license filters) | No "compare two resources" view | None |
| Pedagogical soundness | Good (every card has at least one integration tip; reference rows get a tailored "open live syllabus" tip) | Tips are short and not aligned to learning objectives | None |
| Licensing clarity | Good (every Open ALG card classified open/unclear/not_open with details) | Some titles report a CC variant rather than the spelled-out license | None — both forms are detected as open |
| Accessibility compliance | Acceptable (semantic HTML, keyboard-focusable controls, ARIA labels on inputs) | Rubric basis correctly says `inferred` when not declared in manifest | None — honest display is the right behavior |
| Modularity & adaptability | Good (resource_type drives modularity sub-score, content is chunked) | None blocking demo | None |
| Supplementary resources | Honest (defaults to `false`, basis displayed as `unavailable` when not declared) | Would require manual curation per resource | None — the honest display is correct |

---

## 5. Phase 6 — Demo prep

### Suggested demo flow (~5 minutes)

1. **Open the app** at `http://localhost:5173`. One-line description: an
   AI-assisted discovery tool for open educational resources, focused on
   Affordable Learning Georgia and GGC's public syllabus catalog.
2. **Show the data sources panel / source filter.** Two real sources:
   Open ALG (full textbooks and ancillaries) and GGC Simple Syllabus
   (live syllabus references).
3. **Live demo query #1 — ITEC 1001** (proves course-code boost + fallback
   on a tiny corpus).
4. **Live demo query #2 — `"art appreciation visual arts introduction"`**
   (pure natural-language, shows the open textbook surfacing).
5. **Live demo query #3 — `"BIOL 1102 biology lab manual"`** (shows both
   an Open ALG body and a GGC `Syllabus reference` card with Term / CRN).
6. **Open the Rubric drawer** on one card and explain `verified` vs
   `inferred` basis, and how the score is computed.
7. **Mention LM Studio** dependency — and that the API is graceful when it
   is not running (200 with a clear error string, never a 500).
8. **Mention GGC SPA limitation** and the metadata-reference strategy.

### Three best live demo queries + 1 backup

1. `BIOL 1102 biology lab manual`
2. `ITEC 1001`
3. `art appreciation visual arts introduction`
- Backup: `american history civil war reconstruction`

### Why RAG + ChromaDB

- **RAG keeps the app honest** — every recommendation is grounded in a real,
  citable resource we ingested.
- **ChromaDB is local, persistent, and free** — no managed service, easy to
  rebuild, easy to demo offline (other than embeddings).
- **LM Studio for embeddings + generation** — local, no API key, easy for an
  educator to run.

### How Open ALG is used

- Public Manifold pages are listed in `data/manifests/openalg.yaml` with a
  course mapping and a license hint.
- `parse_and_normalize` extracts the body and a license string.
- Records are chunked, embedded with Nomic via LM Studio, and indexed in
  the `oer_resources_real` Chroma collection.

### How GGC is included

- GGC Simple Syllabus is a JavaScript SPA; the public PDF export endpoint
  returns 500. We confirmed this directly.
- Each found public syllabus is indexed as a `metadata_reference` record:
  course code, title, term, section, CRN, source, URL — nothing else.
- The UI clearly labels these rows as "Syllabus reference" and links out
  to the live syllabus. We never synthesize syllabus body text.

### Known limitations (say these out loud in the demo)

- **GGC public site is SPA-limited.** Without a headless browser we cannot
  extract body text. We made the conscious choice not to add Playwright.
- **12 GGC (course, term) combos are not publicly indexed.** GGC publishes
  Core IMPACTS courses and a subset of others; the rest are not on the
  public side at all.
- **Bare course-code retrieval depends on the boost + fallback.** A natural
  query like `"history since 1877"` may surface HIST 2111 above HIST 2112
  because they are embedding-near; typing the code disambiguates.
- **Cache is process-local.** It persists for the lifetime of the running
  `uvicorn` process and 10 minutes per entry; restarting the server clears
  it. This is intentional for a class demo.
- **Nonsense queries** can still return a low-confidence card above the
  similarity threshold. We keep the threshold permissive on purpose — a
  stricter cutoff suppressed legitimate matches in early testing.

---

## 6. Final recommendation

**Ready to demo.**

All required courses retrieve their canonical resource at top-1; cards are
honest about license, rubric basis, and reference-vs-extracted content; the
backend handles LM Studio outages gracefully; the cache works; and the
limitations are documented in this report so they can be acknowledged
plainly in the presentation.
