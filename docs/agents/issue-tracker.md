# Issue tracker: Forgejo

Issues, specs and tickets for this repo live as issues in the primary Forgejo repository (the `origin` remote). The GitHub repository is a read-only push mirror: never create issues, pull requests or comments there.

`tea` and `gh` don't work here. Use the Forgejo REST API with `curl`.

## Conventions

- **Base URL**: `https://<forgejo-host>/api/v1/repos/<owner>/<repo>`, derived from the `origin` remote.
- **Auth**: header `Authorization: token <token>`, using the repo-scoped token configured for your environment. Never print the token or write it to a file, log or commit. On errors print only the HTTP status (`-o /dev/null -w "%{http_code}"`): Forgejo can echo the token in error bodies.
- **List issues**: `GET /issues?type=issues&state=open` (add `&labels=<name>` to filter). Without `type=issues` the list includes pull requests.
- **Read an issue**: `GET /issues/<n>` and `GET /issues/<n>/comments`.
- **Create an issue**: `POST /issues` with `title`, `body` and `labels` (label ids from `GET /labels`).
- **Make an issue part of a parent**: put `Part of #<parent>` as the first line of the child body and list the child in the parent body.
- **Comment on an issue**: `POST /issues/<n>/comments` with `body`.
- **Apply / remove labels**: `POST /issues/<n>/labels` with `labels: [<id>]` / `DELETE /issues/<n>/labels/<id>`.
- **Close**: `PATCH /issues/<n>` with `state: "closed"`.
- A bare `#n` means Forgejo. Refer to old issues on the mirror as `GitHub #n`; the two number spaces collide.

## Approval

- **No approval needed** for: new issues, comments, adding/removing labels, creating labels, dependencies, assignments, editing and closing the bot's own issues, comment-only reviews on any PR. These go out directly, without showing a draft first. This overrides the general approval rule for this repo only.
- **Approval still needed** for: deleting anything (comments, labels, branches other than the bot's own `sb/` branches); editing other people's issues, PR descriptions or comments; closing other people's issues or PRs; approve or request-changes reviews on PRs not opened by the bot; @-mentioning anyone other than the maintainer who commissioned the agent. Show the draft and wait.
- Every issue body, comment and review starts with the attribution line the maintainer requires (who commissioned the agent, which model). Triage's own disclaimer goes on the line below.
- No personal data (names, mail addresses) and no secrets in titles, bodies or comments.

## Pull requests as a triage surface

**PRs as a request surface: no.** _(Set to `yes` if this repo treats external PRs as feature requests; `/triage` reads this flag.)_

## When a skill says "publish to the issue tracker"

Create a Forgejo issue.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body.
- **Child ticket**: an issue with `Part of #<map>` as its first line, listed in the map body. Labels: `wayfinder:<type>` (`research`/`prototype`/`grilling`/`task`). Once claimed, the ticket is assigned to the driving dev.
- **Blocking**: Forgejo's native issue dependencies: `POST /issues/<child>/dependencies` with `{"owner": "<owner>", "repo": "<repo>", "index": <blocker>}`; read with `GET /issues/<child>/dependencies`. Where that fails, fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body. A ticket is unblocked when every blocker is closed.
- **Frontier query**: list the map's open children, drop any with an open blocker or an assignee; first in map order wins.
- **Claim**: `PATCH /issues/<n>` with `assignees: ["<login>"]`, the session's first write.
- **Resolve**: comment with the answer, close the issue, then append a context pointer (gist + link) to the map's Decisions-so-far.
