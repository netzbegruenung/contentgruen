# Coding standards

Judgement rules the reviewer checks on every pull request. Each rule says why it exists. Mechanical rules live in checks instead (`scripts/check.sh`, pre-commit).

## Domain language

- **Use the glossary term.** Names in code, UI texts, tests, commits and PR texts use the term `GLOSSARY.md` defines and none of its _Avoid_ words for that concept. Why: the glossary is how people, agents and code talk about the same thing; a synonym in one layer splits the concept (see the Einwurf stages, which had four name sets).
- **New term, same PR.** A pull request that introduces a domain concept adds it to `GLOSSARY.md`. Why: the glossary changes only through pull requests (`docs/agents/domain.md`), and a term that lands without it drifts.
- **Decisions follow the ADRs.** A change that contradicts an ADR in `docs/adr/` says so in the PR and why. Why: ADRs record hard-to-reverse trade-offs; silently overriding one loses the reasoning.

## Public repository

- **Operations stay internal.** No internal host names, configuration-management details, secret stores or credentials in code, docs, comments, commit messages or PR texts; public domains are fine. Why: the repository is mirrored publicly to GitHub, and commit messages travel with it.
- **No personal data.** No names or mail addresses of real people in code, fixtures, docs or tracker texts. Why: same mirror, plus data protection.

## Legal texts and data protection

- **Legal texts change through their own ticket.** Changes to the privacy policy, terms of use or imprint are listed in the PR but made in a dedicated ticket that goes through legal review. Why: these texts carry legal weight and need sign-off; a side change in a feature PR skips that.
- **Data handling matches the privacy policy.** A change that stores, logs or derives personal data either fits the current privacy policy or names the needed change as an open point. Why: the policy promises what the code does.

## Documentation

- **Docs move with the code.** A PR that changes behaviour, configuration or operation updates the doc that describes it (`docs/LOESCHKONZEPT.md`, `docs/DEPLOYMENT.md`, the migration README). Why: these docs are used by people acting on production data.
- **Historical documents stay as they are.** Files under `docs/archiv/` and applied migrations keep their content; only the archive note and explicit ticket exceptions change them. Why: they record a past state that later work refers to.

## Git

- **Merge, don't rebase, on shared branches.** Bring `main` in with a merge commit; no force-push on a branch with an open PR. Why: reviews and comments refer to commits.
