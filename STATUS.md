# Project Status – Gut gesagt

> Last updated: 2026-07-25

Current Objective: **Polish the MVP and grow usage**

## Goal of the MVP Release

The MVP of Gut gesagt targets active members of Netzbegrünung (10–50 users).
It lets users perform semantic searches over a shared pool of vetted political content,
use existing comments/background info, and contribute their own.

> Focus: a functioning, engaging content search experience — backed by real seed content.

## What's Already Working

* [x] Login via Keycloak (production) and dummy auth (dev/test)
* [x] Anonymous / public search — search and view results without logging in (contribution stays behind login)
* [x] Semantic search using Qdrant v1.18.2 and E5 multilingual embeddings
* [x] Content-type-aware encoding, polarity filtering, and keyword-overlap score boosting
* [x] Content contribution workflows (commentaries, background info / generic text, statements, images)
* [x] Image content type with AI-assisted caption suggestion (GPT-4o mini) and async background description worker — note: no OpenAI key is configured in production, so image ingestion there currently falls back to plain user-entered text
* [x] Post content type (social media posts: Facebook / Instagram / TikTok)
* [x] `ContentTypeSpec` registry — adding a new content type is a spec + model + frontend fragment, not a 500-line clone
* [x] Content reporting and moderation system (incl. anonymous reporting with session tracking)
* [x] Admin area with MVP metrics dashboard
* [x] PostgreSQL persistence for application data (votes, usage tracking, moderation); vectors live in Qdrant
* [x] Backup & restore (with rotation; automated in prod via SaltStack)
* [x] Start page value proposition, recent-content display, help dialog, branding/favicon
* [x] CI/CD via GitHub Actions (build on `main`/PRs, tagged releases); test and production systems deployed

## Open Core Tasks

| Task                          | Status   | Notes                                                       |
| ----------------------------- | -------- | ----------------------------------------------------------- |
| Mobile UI optimization        | ☐ open   | In progress                                                  |
| Post add-form                 | ☐ open   | Post result item shipped but no contribution form yet       |
| Frontend test suite           | ☐ open   | Backend well covered; frontend specs exist but are thin     |
| Seed content for launch       | ☐ open   | Chicken-and-egg: pre-fill, then grow actively               |
| Production monitoring/logging | ☐ open   | No realistic prod observability yet                         |
| Content status feature        | ☐ open   | Not started in this repository                              |
| Export/import backup          | ☐ open   | Not started in this repository                              |

## Growth / Engagement Backlog

Candidate features:

* Simple user registration (with manual Kreisverband approval, rate limiting)
* Trending content feed (top 10 of the week by usage, 🔥 badge)
* Onboarding flow ("add your first contribution" CTA, success states)
* First gamification (XP, daily tasks, leaderboard)
* Catch-all / meta-commentaries for queries with no specific match

## Blockers & Risks

* **Not enough content at launch** (chicken-and-egg) → actively seed and recruit a few early contributors.
* **No production observability yet** → next priority after launch polish.

## Strategic Decisions

* MVP launches **without AI generation of argumentative replies** — Gut gesagt is a curated exchange of human-vetted arguments, not a generator. AI is used only at ingestion time to assist with image captions.
* UI kept **simple and mobile-first** for the MVP.

## Next Steps (high → low priority)

* [ ] Finish mobile responsiveness
* [ ] Add Post contribution form (add-post frontend workflow)
* [ ] Add/refresh seed content
* [ ] Stand up production monitoring/logging
* [ ] Add a frontend unit-test suite
* [ ] Run a beta with 5–10 testers, collect feedback, fix issues
* [ ] Wider release to Netzbegrünung
* [ ] Pick up growth backlog (registration, trending, onboarding)

## Environments

* **Test:** https://contentgruen-test.netzbegruenung.de — SaltStack-managed, tracks `:main`.
  The older https://test.contentgruen.de (manual, `mvp/docker-compose.tst.yml`) is being discontinued.
* **Production:** https://contentgruen.netzbegruenung.de — SaltStack-managed, images pinned by
  digest and bumped by Renovate. https://contentgruen.de redirects here.
