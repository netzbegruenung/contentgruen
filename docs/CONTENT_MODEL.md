# Gut gesagt Content Model — Architecture

> Status: **largely implemented.** This document describes the content-type architecture and
> the reasoning behind it. The registry, the ingestion seam, the `SearchOrchestrator` and the
> frontend content-type registry all ship today; `post` and `image` are built entirely through
> this path.
>
> **Still open:** `statement`, `reference`, `commentary` and `generic_text` retain hand-written
> service and repository classes. Registry specs exist for `commentary` and `generic_text` but
> nothing resolves them yet, so those two are declared twice. Do not copy the hand-written
> pattern for new types — use the registry path described below.

## Motivation

`commentary` and `generic_text` grew as near-identical clones, maintained separately through
every layer of every tier (frontend components, Python services/repositories/DTOs, the search
handler). Adding a new type meant copying ~500 lines of mechanism. The roadmap calls for **many**
more types — speeches, debates, newspapers, papers, song texts, images, graphics — so the cost of
that duplication compounds with every type, and the copies had already drifted.

The goal of this document is an architecture where **adding a content type is cheap** and each type
**keeps room to diverge**, without re-cloning the engine.

## Core principle: one deep engine, three thin seams

Two kinds of duplication exist, and only one should be removed:

- **Mechanism** (incidental) — voting, scoring, enrichment, embedding, search, persistence, HTTP.
  A song text and a debate are voted on, scored, and indexed *identically*. This must be written
  **once**, type-agnostic. It is the deep shared module.
- **Domain shape & behavior** (essential) — fields, rendering, and how a type's searchable text is
  produced. This *will* diverge and must have a small, isolated home per type.

The unifying insight that keeps the engine uniform: **every content type reduces to text that gets
embedded into a vector.** Even media does — an image's searchable text is an AI-generated
description (see below). So the embed → store → search → enrich pipeline never needs to know which
type it is handling.

That leaves exactly **three seams** where types are allowed to differ:

| Seam | What varies | Example |
|------|-------------|---------|
| **1. Ingestion / text-derivation** | how `searchable_text` is produced | image → call vision API for a description; comment → user types it |
| **2. Content model** | extra fields beyond the base | `image_url`, `speaker`, `doi`, `publication_date` |
| **3. Rendering** | how a result is displayed | image card shows the picture; speech shows speaker + date |

Everything else is shared.

## The text→vector substrate (incl. images)

```
                       ┌─────────────────────────────────────────────┐
  raw input ──▶ [INGESTION STRATEGY] ──▶ searchable_text ──▶ embed ──▶ store ──▶ search ──▶ enrich ──▶ render
  (per type)        (SEAM 1)                                 └──────────── shared engine ───────────┘   (SEAM 3)
                                                                                  ▲
                                                                          content model (SEAM 2)
```

- For most types the ingestion strategy is **identity**: `searchable_text = user input`.
- For an **image/graphic**, ingestion calls an external AI vision endpoint, receives a textual
  description, and stores it as `searchable_text`. From that point on the image is just another
  text-bearing content item — matched on its description, rendered as a picture.
- The derived text is **persisted, never recomputed**: the AI call happens once at ingestion. Search
  is thereafter cheap and deterministic, and the one-time AI cost is at index time, not query time.

This also keeps the "MVP launches without AI generation" stance intact: the AI describes/indexes at
ingestion — it does **not** generate content shown to users. Different thing, deliberately.

## Backend design (Python)

The foundation already exists and should be leaned on, not rebuilt:

- `domain/models/base_content.py` — `BaseContent (text, content_type)` → `BaseContentDbEntry (metadata)`
  → `BaseContentSearchResult (score)`. **Seam 2** extends these per type.
- `services/content/base_content_service.py` — already `Generic[TRepository, TContentDbEntry, TContentSearchResult]`.
  This is the deep engine; it should own *all* CRUD/search/embedding and stop being subclassed for
  pure configuration.
- `domain/models/content_type.py` — the `ContentType` enum is the discriminator.

### What changes

**1. A content-type registry replaces the per-type class tower.** *(shipped —
`domain/content_registry.py`)*
Each legacy type drags a `Service + ServiceInterface + Repository + RepoInterface + Factory` chain
where most layers are empty/pass-through (empty `I*Repository` markers, no-op
`initialize_with_initial_data`, a single-implementation `IRepositoryFactory`). It is replaced by one
declarative registry entry per type:

```python
# domain/content_registry.py  (illustrative)
@dataclass(frozen=True)
class ContentTypeSpec:
    content_type: ContentType
    index_name: str
    db_entry_model: type[BaseContentDbEntry]      # SEAM 2
    search_result_model: type[BaseContentSearchResult]
    ingestion: IngestionStrategy                  # SEAM 1
    extra_behavior: ContentBehavior | None = None # e.g. Statement dedup

REGISTRY: dict[ContentType, ContentTypeSpec] = {
    ContentType.COMMENTARY:    ContentTypeSpec(..., ingestion=DirectText()),
    ContentType.GENERIC_TEXT:  ContentTypeSpec(..., ingestion=DirectText()),
    ContentType.IMAGE:         ContentTypeSpec(..., ingestion=AiVisionDescription(client)),
    ...
}
```

The generic `BaseContentService` is instantiated from a spec — no per-type subclass except where
there is **real** behavior (e.g. `StatementService`'s similarity/dedup stays a subclass or a
`ContentBehavior` strategy).

**2. Ingestion strategy (Seam 1) — the only place type-specific input handling lives.**

```python
class IngestionStrategy(Protocol):
    async def derive_text(self, raw: ContentInput) -> DerivedContent: ...
    # DerivedContent = searchable_text + any extra fields to persist (e.g. image_url)

class DirectText:        # comment, generic_text, speech transcript, paper abstract
    async def derive_text(self, raw): return DerivedContent(text=raw.text)

class AiVisionDescription:   # image, graphic
    def __init__(self, client): self._client = client
    async def derive_text(self, raw):
        description = await self._client.describe(raw.image_url)   # external AI call
        return DerivedContent(text=description, extra={"image_url": raw.image_url})
```

**3. Per-type models (Seam 2)** stay tiny — just the extra fields:

```python
class ImageContentDbEntry(BaseContentDbEntry):
    image_url: str
    description_source: str          # which model produced `text`

class SpeechContentDbEntry(BaseContentDbEntry):
    speaker: str
    spoken_at: datetime
```

**4. The search handler is type-agnostic.** *(shipped —
`services/search/search_orchestrator.py`)* The former ~580-line `api/v1/search.py`, with its
duplicated commentary/generictext branches and the four-times-repeated scoring formula
(`statement_score*0.7 + relevance*0.3`), collapsed into one `SearchOrchestrator` that loops over the
requested content types, applying one shared scoring step and one `enrich(item)` step. `search.py`
is now ~280 lines and new types are searched automatically — no new branch.

### Asynchronous ingestion for AI-dependent types

Types whose ingestion calls an external service must not block creation or search:

```
POST image ──▶ persist row {status: PENDING_DESCRIPTION, image_url} ──▶ 202 Accepted
                       │
            background ▼  (queue / task)
              AiVisionDescription.derive_text()
                       │
                 success ▼                         failure ▼
        text + embedding stored,            status: DESCRIPTION_FAILED
        status: NEW_CONTENT_STATUS          (retryable; surfaced in moderation)
        (sofort auffindbar)
```

*(shipped — `services/vision/image_description_worker.py`.)* The `ContentStatus` enum carries
`PENDING_DESCRIPTION` and `DESCRIPTION_FAILED` alongside the other lifecycle states. The search
engine simply ignores items without an embedding — no special-casing in the query path.

## Frontend design (Angular)

The same split: shared mechanism written once, per-type rendering isolated.

### What changes

**1. A `BaseContentResult` DTO** (in a new `services/dtos/commonDtos.ts`) holds the ~20 fields shared
by `CommentaryResult` and `GenerictextResult` today; each type extends it with only its extras. This
both removes the DTO duplication (and the 6 copy-pasted camelCase TODOs) and is the type foundation
that makes the component unification clean.

```ts
export interface BaseContentResult {
  id: string; text: string; title: string; content_type: ContentType;
  score: number; usage_count: number; votes: VoteInfo; references: ContentReference[]; /* ... */
}
export interface CommentaryResult extends BaseContentResult { short_text: string; long_text: string; style: string; }
export type    GenerictextResult = BaseContentResult;
export interface ImageResult     extends BaseContentResult { image_url: string; }
export interface SpeechResult    extends BaseContentResult { speaker: string; spoken_at: string; }
```

**2. The result-item duplication becomes a deep base + thin per-type views — NOT a `[contentType]`
flag with a forest of `*ngIf`.** A flag-driven blob gets worse with every type; polymorphism gets
better. Voting, the 401/403/429 snackbar handling, debounce, badges, and score display live in an
abstract `BaseResultItemComponent` (or a host component that projects a per-type fragment). Each type
supplies only its presentation:

```
BaseResultItemComponent           ← voting, auth handling, badges, score (the mechanism, once)
 ├─ CommentaryResultItem          ← text-mode toggle (short/std/long) + 💬 label
 ├─ GenerictextResultItem         ← 📄 label
 ├─ ImageResultItem               ← <img> + caption (description), matched-on-text shown on demand
 └─ SpeechResultItem              ← speaker + date header
```

Same treatment for the add-forms and search-results headers: shared base behavior + a per-type
config (label, icon, count selector, extra form controls).

**3. A content-type registry on the frontend too** *(shipped — `shared/content-type-registry.ts`)*
— one place mapping `content_type → { icon, label, resultComponent, resultField }` — so a new type is
registered once and picked up by search results, recent-content, and contribution menus
automatically. This also retired the false-abstraction `unified-result-item`.

**4. A shared HTTP layer** *(still open)*: an `X-Session-Id` interceptor, an
`ApiUrlService` for the `/api/v1` base, and a reusable `handleHttpError` operator — removing the
per-service URL/header/error duplication that every type's service still re-copies. Today
`X-Session-Id` is set per-service in `search.service.ts` and `moderation.service.ts`.

## What is shared vs per-type (the contract)

| Concern | Shared (write once) | Per-type (Seam) |
|---------|--------------------|------------------|
| Embedding & vector search | ✅ engine | — |
| Combined-score formula | ✅ one helper | — |
| Reference / usage / vote enrichment | ✅ one helper | — |
| Voting, auth/rate-limit handling (FE) | ✅ base component | — |
| Persistence / Qdrant access | ✅ generic repo | — |
| HTTP base URL / session / errors (FE) | ✅ interceptor + helper | — |
| **How searchable_text is produced** | — | Seam 1 (ingestion) |
| **Extra fields** | — | Seam 2 (model/DTO) |
| **Display** | — | Seam 3 (template fragment) |
| Special behavior (e.g. dedup) | — | optional behavior strategy |

**Adding a new type =** one registry entry + a model/DTO with its extra fields + an ingestion
strategy (usually `DirectText`) + a template fragment. No engine changes, no cloning.

## Incremental migration path

This was executed in safe, independently-shippable steps. Steps 1–8 are **done**; they are kept
here because they document the order in which the architecture arrived and the reasoning for it.
The backend test suite (well-covered) was the safety net.

1. ✅ **Delete dead code first** (no behavior change): BFF `OLD_DtosFrontend/`, the dead frontend
   components (`social-wall`, `topics`, `editor-mode`, `add-statement-modal`, `add-reference`,
   `workflow/WorkflowOverlayComponent`), the empty backend `repositories/base/` and dead
   `implementations/txtai/` packages. Smaller surface before refactoring.
2. ✅ **Introduce the shared DTO base** (`BaseContentResult`/`ContentReference`) and re-type the existing
   commentary/generictext DTOs onto it. No runtime change; unblocks the component work.
3. ✅ **Extract the frontend mechanism** into `BaseResultItemComponent` and have the existing two
   result-items extend it. Then retire `unified-result-item`. Repeat for search-results and add-forms.
4. ✅ **Add the frontend content-type registry**; route search-results/recent-content/contribution menus
   through it.
5. ✅ **Backend: introduce the content-type registry + ingestion strategy**, instantiate the generic
   `BaseContentService` from specs, and drop the empty per-type interfaces and the single-impl
   factory. Keep `StatementService` behavior as a strategy/subclass.
6. ✅ **Backend: extract `SearchOrchestrator`** from `api/v1/search.py`; unify the per-type branches into
   one loop with shared scoring/enrichment helpers.
7. ✅ **First new type via the new path** — `post` (not `speech`) served as the proof that adding a
   type is now a registry entry + fields + fragment.
8. ✅ **Image/graphic type** with the `AiVisionDescription` ingestion strategy and the async
   description lifecycle — the worked example that validates the media path.

Steps 1–2 were low-risk prep; 3–6 were the structural payoff; 7–8 proved the result.

**Remaining migration work:** move `commentary` and `generic_text` off their hand-written services
onto the registry specs that already exist for them, then do the same for `statement` (keeping its
dedup behavior as a strategy) and `reference`.

## Decisions

- **snake_case end-to-end on the wire — DECIDED.** The duplicated DTO TODOs (e.g.
  `generictextDtos.ts` "Evaluate usage of camel case and transformation in the backend") asked this
  question; it is now settled. The Python backend already serializes snake_case
  (`references_count`, `usage_count`, `content_type`), so the frontend DTOs adopt snake_case to
  match — no per-field transformation, no `DtoMapper` boundary. This unblocked the shared
  `BaseContentResult` DTO base (`services/dtos/commonDtos.ts`).
- **AI vision provider — DECIDED.** OpenAI `gpt-4o-mini`, called from the search service at
  ingestion time behind the `IngestionStrategy` interface, so the provider stays swappable.
  Configured via `OPENAI_API_KEY` (or `SEMANTIC_SEARCH_OPENAI_API_KEY`); without a key the image
  type falls back to `DirectText`.

## Open decisions
- **Reprocessing**: if the description model improves, do we re-derive text for existing images? (Make
  ingestion idempotent and re-runnable to allow it.)
- **Legacy type migration**: whether to move `statement` and `reference` onto the registry, or leave
  them as the two types with genuinely type-specific behavior.
