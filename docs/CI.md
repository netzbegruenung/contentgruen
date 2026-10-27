# CI on Woodpecker

Every pull request on Forgejo runs the pipeline `.woodpecker/ci.yaml` (workflow `ci`) on
verdigado's Woodpecker. It checks what `scripts/check.sh --integration` checks locally, and
its status `ci/woodpecker/pr/ci` is required before a merge into `main` once a person has
completed the [setup](#setup-by-a-person).

The GitHub Actions on the mirror (`.github/workflows/`) are unchanged: they run after the
merge and build the images.

## What runs

| Step | Image | Runs |
|---|---|---|
| `retired-words` | `node:22` (frontend Dockerfile; has git and python3) | `check.sh --schritt retired-words`, lines added since the branch left the target branch; pull requests only (push, tag and manual runs have no target branch) |
| `python-installieren` | `python:3.13-slim` (semantic-search Dockerfile) | venv at `mvp/backend/semantic-search-service/venv`, `requirements.txt` |
| `lint` | same | `check.sh --schritt lint`: Ruff and Black with the versions pinned in `requirements.txt` |
| `unit` | same | `check.sh --schritt unit`: Python unit tests and `scripts/tests/` |
| `integration` | same | `check.sh --schritt integration` with `INTEGRATION_STACK_PFLICHT=1` against the services below |
| `frontend` | `node:22` | Chromium from Debian (`scripts/ci-chromium.sh`), `npm ci`, `check.sh --schritt frontend` |
| `bff` | `mcr.microsoft.com/dotnet/sdk:9.0` (BFF Dockerfile) | `check.sh --schritt bff` with `CHECK_OHNE_DOCKER=1` |
| `ci-bericht` | `python:3.13-slim` | red pull-request runs only, see below |

Services: `qdrant` (version of `mvp/docker-compose.dev.yml`, `entrypoint: /qdrant/qdrant`;
without the absolute path the service does not start) and `postgres` (base image of
`mvp/backend/postgres-app`). The integration step reaches them through `QDRANT_URL` and
`POSTGRES_TEST_DATABASE_URL`, after `scripts/ci_dienste_warten.py` has waited (up to two
minutes) until both accept connections; the throwaway container of the suite is not used, the runner
has no Docker socket.

Rules the pipeline keeps, checked by `scripts/tests/test_woodpecker_ci.py` (part of
`check.sh`):

- **One source for versions.** Woodpecker cannot read a Dockerfile, so the images appear a
  second time in `ci.yaml`. The test fails if they differ from the Dockerfiles and the
  compose file. When raising a version, change both.
- **One source for commands.** Each step calls `check.sh --schritt <name>`, one pipeline step
  per step of `check.sh` (the test compares the names). `CHECK_VOLL=1`
  makes `check.sh` print the full output instead of its summary lines.
- **No path filter on the workflow.** A skipped workflow reports no status, and the
  required status then blocks the pull request. Filters only per step, and only so that
  `ci` still reports.
- **Events:** `pull_request`, `push` on `main`, `tag` and `manual`. Without `manual`,
  "Run pipeline" in the Woodpecker UI filters the workflow out.
- The clone step fetches the full history and the target branch (`fetch-target-branch`),
  so `retired-words` can find where the branch started.

## CI report

Woodpecker logs need a Woodpecker login, which agents do not have. If a pull-request run is
red, the last step `ci-bericht` writes one comment into the pull request: the red steps with
the last 80 lines of their output, and the steps that did not run.

- Each step runs its commands through `scripts/ci-protokoll.sh`: output to the Woodpecker
  log and appended to `.ci/<step>.log`, exit code to `.ci/<step>.status`. A log without a
  status counts as aborted.
- `scripts/ci_bericht.py` builds the comment (standard library only, so it also reports a
  failed installation). The output is stripped of ANSI codes and control characters, the
  token value is replaced if it shows up, the comment stays below 60 000 characters.
- One attempt, at most 30 seconds. If Forgejo refuses, the step turns red and logs only the
  HTTP status, never the response body (Forgejo echoes an invalid token in it). Without a
  token value the step logs a line and ends green.
- **Known limit:** the step runs `ci.yaml` and `scripts/` from the pull-request branch with
  the token. Anyone who can push a branch, or whose fork pull request is approved, can read
  the token through a changed pipeline. It must therefore never be able to do more than the
  bot in this repository: this repository only, `write:issue` and `read:repository`, event
  `pull_request` only.

## Setup by a person

The bot can write the pipeline, but cannot enable a repository, create secrets or change the
branch protection. In this order (the secret can only be created once the repository is
enabled, and the pull request that adds the pipeline already needs it):

1. **Enable the repository in Woodpecker:** visibility internal, pull requests allowed, not
   trusted, approval required for forks (the default). Pull requests from forks are released
   by any person with Woodpecker access (staff and authorised members of Netzbegrünung); check the diff for changes to `.woodpecker/` and
   `scripts/` first (see the known limit above).
2. **Secret, right after enabling and before the first pull-request run.** Create a token
   `woodpecker-ci-bericht-gutgesagt` for the bot account: this repository only, scopes
   `write:issue` and `read:repository`, nothing else. Store it in the team's password
   manager and add it in Woodpecker as secret `forgejo_ci_bericht_token`, event "Pull
   Request" only, no image filter. Woodpecker resolves secrets when it compiles a run: if
   the secret is missing or not released for pull requests, **every pull-request run fails
   with "secret not found"** before any step.
3. **Required status:** after the first pull-request run, add `ci/woodpecker/pr/ci` as a
   required status check in the branch protection of `main`, and switch on "pull request
   must be up to date", so combinations of two pull requests run before the merge. A branch
   is brought up to date by merge ("Update branch"), not by rebase. Whoever wants a linear
   `main` sets the merge style to squash.

Check without admin rights: `GET /api/v1/repos/<owner>/<repo>/branches/main` shows
`enable_status_check` and `status_check_contexts`.

## Running a step locally

`bash scripts/check.sh --schritt <name>` runs one step against the working tree (for
`integration` with Qdrant and PostgreSQL as described in the
[testing guide](../mvp/backend/semantic-search-service/app/tests/TESTING_GUIDE.md)).
`bash scripts/check.sh --integration` runs all of them.
