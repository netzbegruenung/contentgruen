# Gut gesagt Roadmap — From Pre-MVP to the Full Platform

> Status: **strategy / direction** (not a commitment). Companion to
> [CONTENT_MODEL.md](./CONTENT_MODEL.md), which describes the *architecture*.
> This document describes the *path*: how to get from the MVP to the long-term vision, one
> independently-useful step at a time.
>
> Rungs 0–2 are complete — see [Current position](#current-position-as-of-july-2026) at the end.
> The rung descriptions below are kept as written, as the record of what each step was for.

## The vision (the direction, not a plan)

A platform that analyzes **any content in any format**, transforms it multimodally, and then
**tags**, **describes**, **mood/stance-checks**, **links it to sources**, and drafts **good
argumentative replies** — built **mainly on semantic search, with LLM as support** — and
**gamified for Green Party members**.

This is a destination to steer toward, not a spec to build in one shot.

## The core principle

You do **not** get there by building toward it. You get there by climbing a ladder where **every
rung is independently useful and dogfoodable**, so you can stop, pivot, or linger on any rung and
still have a real product. The vision sets the direction; each rung is the only thing you actually
commit to at a time.

## Honest reality check

- **AI coding agents are not the bottleneck.** They make *code* 2–4× faster, but the critical path
  of this vision is **judgment, evaluation, data, trust, and ops** — which agents barely touch. The
  whole-project multiplier is ~**1.3–1.8×**, not 3× (Amdahl's law: you accelerate the part that was
  never the long pole).
- **A demo that does everything is cheap (~3–5 months). A version you'd put the party's name on is
  not (~9–18 months focused; 2+ years part-time).** Agents make the *demo* faster, which widens the
  trap: you'll have impressive-but-untrustworthy capability long before it's safe to ship.
- **"Argumentative replies" is the highest-risk item and is deliberately last.** A reply that
  hallucinates a fact or misattributes a position isn't a bug — it's a screenshot that embarrasses
  Netzbegrünung. It stays human-in-the-loop (drafts a member edits) far longer than feels necessary.

## The ladder

Each rung lists its goal, what you build, what it leans on, a rough agent-assisted cost, and the
**gate** that must be true before climbing to the next rung.

### Rung 0 — Launch & dogfood ✅
- **Do now, change nothing.** Ship the current MVP, use it yourself daily, write down every friction
  point. Real usage is the forcing function for everything above it — better signal than any
  refactor instinct.
- **Cost:** this week.
- **Gate:** you have a concrete friction list from real use.

### Rung 1 — Make it sound, proven by a third type (Post) ✅
- Delete the verified dead code (`social-wall`, `topics`, `editor-mode`, `add-statement-modal`,
  `add-reference`, `workflow/`, BFF `OLD_DtosFrontend/`, empty `repositories/base/`, dead `txtai/`).
- Pin a **search-ranking characterization test** before touching `search.py`
  (now `app/tests/unit/api/test_search_ranking.py`).
- Add **Post** (FB/Insta/TikTok) by **extracting the shared base while adding it**, so the feature
  pays for the refactor (rule of three: Post is the legitimate third instance).
- Decide **snake_case end-to-end** (it blocks the shared DTO base; don't defer it a third time) — decided, see CONTENT_MODEL.md.
- **Lean:** existing engine; Post is text-bearing (platform/author/url/engagement = extra fields).
- **Cost:** 3–6 weeks, agent-heavy. **Gate:** adding a content type now feels cheap, not like a
  500-line clone.

### Rung 2 — Multimodal ingestion, the cheap way first ✅
- **Captioned images first:** user types the text → `DirectText` → flows through everything you
  already have. **No AI, no queue.** (This is "erstmal generisch Bild.")
- *Then*, as a separate explicit step, build the **async vision/ASR pipeline once** — the home for
  auto-described images and ASR'd speeches. This is where the task queue (which doesn't exist yet)
  gets built, with retries / dead-letter / idempotency.
- **Lean:** all AI happens at **ingestion**; search stays cheap and deterministic.
- **Cost:** 2–3 months. **Gate:** a non-text type is searchable and the engine treats it uniformly.

### Rung 3 — Analysis layer: tag, describe, mood/stance ⬅ next
- **Discipline shift: build a small labeled eval set *before* you trust any output.** Without eval
  you cannot tell if it's good.
- Lean on **semantic search + light classification, not generation** — most tagging/mood can be
  retrieval, not an LLM call.
- **Cost:** 2–4 months, and the cost is **eval, not code**. **Gate:** tag/mood accuracy measured
  against the labeled set, good enough to show a member.

### Rung 4 — Source linking
- Curate a real **source corpus** (Green positions, KV data, verified facts) and ground retrieval
  against it. This is the **prerequisite** for safe replies — no corpus, no trustworthy reply.
- **Cost:** 1–3 months + ongoing curation. **Gate:** given an input, you reliably surface the
  *right* sources.

### Rung 5 — Argumentative replies — human-in-the-loop only
- It **drafts**; a member **edits and sends**. Never autonomous early. Highest reputational risk;
  comes last on purpose, on top of a trustworthy corpus and measured analysis.
- **Cost:** 3–6 months, never fully "done" (it's a quality treadmill). **Gate:** members actually use
  the drafts and none are screenshot-embarrassing.

### Rung 6 — Gamification + KV social data, woven through
- The fun/engagement layer (streaks, leaderboards, member voting) sits **on top of** the votes/usage
  you already track — additive, decoupled from the engine. **DSGVO** matters the moment you touch
  member data.
- Worthless bolted onto a platform that doesn't yet do anything — hence late, but it's what makes the
  whole thing sticky.
- **Cost:** 1–3 months + ongoing.

## The four rules that keep you honest

1. **Dogfood every rung before climbing the next.** Real use is the gate, not "it compiles."
2. **Eval before trust.** From rung 3 on, every ML/LLM output needs a measured quality bar or you're
   flying blind. This is the part AI agents do **not** shortcut.
3. **Semantic-search-first, LLM as a scalpel.** Every capability done with the existing substrate
   instead of a per-query LLM call is cheaper to build, cheaper to run, and needs no eval harness.
4. **The dangerous thing is always last and always assisted.** Replies for a political party stay
   human-in-the-loop far longer than feels necessary.

## Where the AI agents actually help

- **Rungs 1–2 (code-heavy):** real 2–4× speed-up. Climb fast.
- **Rungs 3–5 (gated by eval, data, trust):** agents help modestly; **discipline matters more than
  typing speed.**
- The agents buy you velocity early and the brakes matter late — backwards from how it will *feel*,
  because the early wins will tempt you to skip the gates. **Don't.**

## Current position (as of July 2026)

Rungs 0–2 are complete:
- **Rung 0** — MVP deployed to test and production, in active use.
- **Rung 1** — `ContentTypeSpec` registry shipped; adding a type is a spec + model + fragment (proven by Post).
- **Rung 2** — Image type shipped: Phase A (user-captioned images, AI caption suggestion via GPT-4o mini) and Phase B (async background description worker for captionless ingestion).

**Next: dogfood rungs 1–2, then decide rung 3.** Use the platform actively, catalogue friction, and
grow real content. Rung 3 (tagging, mood/stance analysis) requires a labelled eval set before any
ML output can be trusted — the eval set is the gate, not the code. Do not start rung 3 without it.
