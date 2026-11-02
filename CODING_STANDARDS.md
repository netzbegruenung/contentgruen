# Coding standards

Judgement rules the reviewer checks on every pull request. Each rule says why it exists. Mechanical rules live in checks instead (`scripts/check.sh`, pre-commit).

## Severity of findings

Every review finding carries one of three severities; tracker texts use the German word in brackets.

- **must** („muss“): the PR is not ready to merge until the finding is fixed or the maintainer decides otherwise. An open Fachfrage is always a must.
- **should** („sollte“): fixed in this PR; deferring it needs a stated reason and the ticket it moves to.
- **optional**: an improvement the author may leave out; one outside the PR's scope goes to a follow-up ticket instead of into the PR.

Why: "must" decides whether a PR can merge, and a reviewer and an author who read the same word differently either block a finished PR or merge an unfinished one.

## Domain language

- **Use the glossary term.** Names in code, UI texts, tests, commits and PR texts use the term `GLOSSARY.md` defines and none of its _Avoid_ words for that concept. Why: the glossary is how people, agents and code talk about the same thing; a synonym in one layer splits the concept (see the Einwurf stages, which had four name sets).
- **New term, same PR.** A pull request that introduces a domain concept adds it to `GLOSSARY.md`. Why: the glossary changes only through pull requests (`docs/agents/domain.md`), and a term that lands without it drifts.
- **Decisions follow the ADRs.** A change that contradicts an ADR in `docs/adr/` says so in the PR and why. Why: ADRs record hard-to-reverse trade-offs; silently overriding one loses the reasoning.

## Scope

- **Behaviour beyond the ticket is a Fachfrage.** A PR that changes what a person sees or can do, beyond the ticket's acceptance criteria, gets a blocking ("must") finding: a Fachfrage, a product question only the maintainer decides. A PR with an open Fachfrage is not ready to merge. Why: a change people notice needs a decision before it ships, not a side note in the PR description (as with #316, which hid older images without an Unterschrift from their authors).

  Format, read by tooling: the PR description contains the heading `## Fachfrage` once, followed by one item per change up to the next `## ` heading. Heading and items start at the beginning of the line, not indented and not inside a code block or quote. Open: `- [ ] <the change, the question for the maintainer>`. Decided: `- [x] <the decision> (<link to the comment or ticket>)`. Without such a change the heading is left out.

## Product principles

- **Visible numbers are real.** Counters, badges, points and statistics shown to people come from real events; no pre-filled or estimated values, also not in seeds that could reach test or production. Why: the product asks people to trust usage as a quality signal (`docs/VISION.md`, ADR 0004).
- **Organisation-neutral where it costs nothing.** New code takes texts, names and links specific to Netzbegrünung or the Greens from one place (configuration or a single constant) rather than scattering them; existing code stays until it is touched for another reason. Why: later instances for other organisations are planned (`docs/VISION.md`, Ausbaustufen), and scattered literals make that expensive.

- **A Titel is a claim, not a topic.** The Titel of a Kommentar or a Hintergrundinfo is exactly one sentence stating a claim with a stance, 3–120 characters (`GLOSSARY.md`, Titel). Questions and topics belong in the Aussage the Beitrag answers. In the Destillieren flow the Satz field „Was ist der Punkt? Ein Satz.“ is this Titel. Right: „Wärmepumpe lohnt sich auch im Altbau“. Wrong: a question („Lohnt sich Wärmepumpe im Altbau?“), a topic („Wärmepumpen im Altbau“), a label („Faktenhammer“). Bild titles (descriptive, up to 200 characters) and Post titles do not follow this rule. Why: the product helps people find arguments, and a topic as Titel shows no argument on the card. The limit and the card height belong together: the Titel box of the search card is measured for this length, so a change to the limit re-measures the card, and loosening the rule needs a product decision.

## Public repository

- **Operations stay internal.** No internal host names, configuration-management details, secret stores or credentials in code, docs, comments, commit messages or PR texts; public domains are fine. Why: the repository is mirrored publicly to GitHub, and commit messages travel with it.
- **No personal data.** No names or mail addresses of real people in code, fixtures, docs or tracker texts. Why: same mirror, plus data protection.

## Legal texts and data protection

- **Legal texts change through their own ticket.** Changes to the privacy policy, terms of use or imprint are listed in the PR under `## Fachfrage` but made in a dedicated ticket that goes through legal review. Why: these texts carry legal weight and need sign-off; a side change in a feature PR skips that.
- **Data handling matches the privacy policy.** A change that stores, logs or derives personal data either fits the current privacy policy or names the needed change as an item under `## Fachfrage`. Why: the policy promises what the code does, and only the maintainer can have it extended.

## Documentation

- **Docs move with the code.** A PR that changes behaviour, configuration or operation updates the doc that describes it (`docs/LOESCHKONZEPT.md`, `docs/DEPLOYMENT.md`, the migration README). Why: these docs are used by people acting on production data.
- **Historical documents stay as they are.** Files under `docs/archiv/` and applied migrations keep their content; only the archive note and explicit ticket exceptions change them. Why: they record a past state that later work refers to.

## Git

- **Merge, don't rebase, on shared branches.** Bring `main` in with a merge commit; no force-push on a branch with an open PR. Why: reviews and comments refer to commits.
