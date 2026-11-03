# CI on Woodpecker

Every pull request on Forgejo runs the pipeline `.woodpecker/ci.yaml` (workflow `ci`) on
verdigado's Woodpecker. It checks what `scripts/check.sh --integration` checks locally, and
its status `ci/woodpecker/pr/ci` is required before a merge into `main` once a person has
completed the [setup](#setup-by-a-person).

After the merge, `.woodpecker/build.yaml` and, on `v*` tags, `release.yaml` build the images
(see [Images and releases](#images-and-releases)). Until the switch the GitHub Actions on the
mirror (`.github/workflows/`) still build them too and publish the tags the environments use.

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

Services: `qdrant` (same version as the compose files and `.github/workflows/tests-backend.yml`,
`entrypoint: /qdrant/qdrant`; without the absolute path the service does not start) and `postgres` (base image of
`mvp/backend/postgres-app`). The integration step reaches them through `QDRANT_URL` and
`POSTGRES_TEST_DATABASE_URL`, after `scripts/ci_dienste_warten.py` has waited (up to two
minutes) until both accept connections; the throwaway container of the suite is not used, the runner
has no Docker socket. There is no BFF either: the tests in `tests/integration/api/`, which need
the dev-stack BFF, skip in CI (`CI` set) instead of failing, and show up in the `SKIPPED` lines.
The same holds for `test_webserver_protokoll.py`, which starts nginx in a container. The
app database the code under test would open (`localhost:5433`, the dev stack) does not exist
in CI either: tests replace the repositories that need it (`tests/conftest.py`), and in unit
tests a fixture blocks `get_app_database()` (`tests/fixtures/ohne_app_datenbank.py`).
The `python:3.13-slim` image of the unit step has no git: tests that call a program ask for it
with `programme.noetig` (`scripts/tests/programme.py`) and skip in CI when it is missing; locally
a missing program is an error.

Rules the pipeline keeps, checked by `scripts/tests/test_woodpecker_ci.py` (part of
`check.sh`):

- **One source for versions.** Woodpecker cannot read a Dockerfile, so the images appear a
  second time in `ci.yaml`. The test fails if they differ from the Dockerfiles, the
  compose files, the Qdrant service of the GitHub CI or the SDK image `check.sh` uses for
  the BFF. When raising a version, change all of them.
- **One source for commands.** Each step calls `check.sh --schritt <name>`, one pipeline step
  per step of `check.sh` (the test compares the names). Only the preparation a working tree
  already has locally stays in `ci.yaml`: the venv (`python-installieren`), `npm ci` and
  Chromium for the frontend. `CHECK_VOLL=1`
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
red, the last step `ci-bericht` writes one comment into the pull request: per red step the
exit code and its error lines (the `FAILED`/`ERROR` lines of the pytest short summary, not
the `ERROR` lines of captured logs; or else the last non-empty line, the summary of Karma,
dotnet or Ruff), the last 80 lines of its output folded in
`<details>` ("Log <step>"), and the steps that did not run.

- **Same error, one line.** Each report ends with an invisible HTML comment
  `<!-- ci-bericht fingerabdruck=… -->`: a hash of the red steps, their exit codes and their
  `FAILED`/`ERROR` lines (for a step without such lines its last 20 non-empty lines, since a
  summary like "Found 1 error." alone looks the same for different errors), without
  timestamps, clock times, durations and memory addresses. Before posting, the step reads
  the comments of the pull request. If the most recent earlier report has the same
  fingerprint, it posts only one line ("Unverändert rot", commit, pipeline, link to the last
  full report) carrying the marker again. If the comments cannot be read (refused,
  connection broken, unexpected answer), the full report is posted.
- **Which comments count as a report.** Only comments of the account that owns the token
  (`CI_BERICHT_KONTO` in `ci.yaml`) that start with the report header. A marker in a new
  comment of another account, or in an agent comment of the same account that quotes a
  report, is ignored. Whoever can write to the repository can still edit a report's marker,
  at worst turning the next report into the one line; they could change `ci.yaml` anyway.
  Without `CI_BERICHT_KONTO` the full report is posted without comparing. If the token moves
  to another account and the variable stays, every run posts the full report and the log
  says that markers exist only in comments of other accounts.
- A green run writes nothing: the step only runs on red runs, the last report stays.
- Each step runs its commands through `scripts/ci-protokoll.sh`: output to the Woodpecker
  log and appended to `.ci/<step>.log`, exit code to `.ci/<step>.status`. A log without a
  status counts as aborted.
- `scripts/ci_bericht.py` builds the comment (standard library only, so it also reports a
  failed installation). The output is stripped of ANSI codes and control characters, the
  token value is replaced if it shows up, the comment stays below 60 000 characters.
- One attempt per request (reading the comments, posting), at most 30 seconds each. If
  Forgejo refuses the post, the step turns red and logs only the HTTP status, never the
  response body (Forgejo echoes an invalid token in it). Without a token value the step
  logs a line and ends green.
- **Known limit:** the step runs `ci.yaml` and `scripts/` from the pull-request branch with
  the token. Anyone who can push a branch, or whose fork pull request is approved, can read
  the token through a changed pipeline. It must therefore never be able to do more than the
  bot in this repository: this repository only, `write:issue` and `read:repository`, event
  `pull_request` only.

## Wiki page of the legal-text files

The gap list and the Stände der Nutzungsbedingungen are stored as one file per entry (#500); a
checked-in overview would again be the file every pull request appends to. So the workflow
`.woodpecker/rechtstexte-wiki.yaml` renders both tables after every push to `main` and
overwrites the wiki page „Rechtstexte Übersicht“ (#503). Readers without Python find the
overview there; the head of the page names the commit and says to change the entry files,
not the page.

- `scripts/rechtstexte_wiki.py` (standard library only, Forgejo helpers shared with
  `ci-bericht` in `scripts/forgejo_api.py`) writes only if its commit is still the head of
  `main` and the tables changed: of two merges running in parallel only the newer one
  writes, and most runs write nothing. Then it updates the page (`PATCH`) or, on 404,
  creates it (`POST /wiki/new`). Errors log the HTTP status only. Without a token the step
  is red: its only job is the page.
- No path filter: whether the Ablage changed is the script's decision, not Woodpecker's
  list of changed files, which is unverified for merge commits.
- The title has no hyphen: Forgejo stores a title with "-" under a path ending in `.-`, and
  reading the page by its title would then never find it again (`seitenpfad`).
- After a red run, restart the last push pipeline on `main` in Woodpecker; there is no
  manual or cron trigger, so the secret stays out of branch runs.
- Own workflow, not a step in `ci`: a red run here leaves the status of `ci` alone.
- `push` on `main` only, and the secret is released for `push` only: pull-request and manual
  runs of a branch never see it. Whoever can push a branch to this repository could still
  read it through a changed workflow; they have write access already. The scope
  `write:repository` is wider than the wiki: the token could also push to unprotected
  branches and create tags. Forgejo has no narrower scope for the wiki, so a leaked token
  is revoked and replaced at once.

## Images and releases

Two workflows build the four images (frontend, BFF, semantic search, postgres-app) with the
plugin `woodpeckerci/plugin-docker-buildx` and push them to
`git.verdigado.com/netzbegruenung-images/gutgesagt-*`, the names the GitHub CI used, so
deployment and Renovate keep working (#327). Both start only after a green `ci` run
(`depends_on: [ci]`): a tag cannot ship what `main` would have rejected.

| Workflow | Runs on | Builds | Tags |
|---|---|---|---|
| `build.yaml` | push to `main`; "Run pipeline" on `main` | images whose files changed; a manual run builds all | `main`, `sha-<7 characters>` |
| `release.yaml` | tag `v*` | all four | `X.Y.Z`, `X.Y`, `latest`; a prerelease only `X.Y.Z` |

- **Tags from one script.** The step `image-tags` runs `scripts/image_tags.py`, which writes
  the tags to `.image-tags`; the build steps read them (`tags_file`). A tag that is not a
  SemVer version `vX.Y.Z` turns the step red and nothing is built.
- **Version in the footer from the tag.** The release build passes the tag as build
  argument `APP_VERSION` to the frontend image; a release needs no version change in
  `package.json` (`docs/DEPLOYMENT.md`, "Releases"). Builds of `main` show the version from
  `package.json`.
- **Path filters** per build step, because a filter on the workflow would hide it. They cover
  everything the Dockerfile copies (the semantic search image also takes the migrations,
  `mvp/scripts/backup`, `mvp/data` and `mvp/.dockerignore`), plus `build.yaml` and
  `scripts/image_tags.py`, so a change to the build rebuilds every image. Woodpecker takes
  the changed files of a push from the webhook; if the list is empty, every step runs.
- `scripts/tests/test_woodpecker_images.py` keeps the two workflows identical except for the
  path filters and `APP_VERSION`, checks the image names, the filters against the
  Dockerfiles and that only the plugin steps see the registry secret.
- No build cache: each run builds from scratch, as the earlier Woodpecker builds did.

**Parallel run.** As long as the GitHub workflows build, every Woodpecker tag carries the
prefix `woodpecker-` (`IMAGE_TAG_PRAEFIX` in both workflows): `:woodpecker-main`,
`:woodpecker-0.9.0` and so on. The two CIs never overwrite each other's tags, and nothing
deployed follows a prefixed tag.

**Switch** (one pull request, with the maintainer's consent, because `.github/workflows/`
changes act on the mirror at once), after at least one push to `main` and one test tag
have built on both sides:

1. Compare the images: same base layers, the same files in the image
   (`docker run --rm --entrypoint ls <image> -R /app` or similar per image), the frontend
   footer with the expected version and commit.
2. Remove `IMAGE_TAG_PRAEFIX` from `build.yaml` and `release.yaml` and delete
   `.github/workflows/`; update this section and `docs/DEPLOYMENT.md`.
3. After the merge: delete the GitHub Actions secrets on the mirror and the prefixed tags in
   the registry.

## Setup by a person

The bot can write the pipeline, but cannot enable a repository, create secrets or change the
branch protection. In this order (the secret can only be created once the repository is
enabled, and the pull request that adds the pipeline already needs it):

1. **Enable the repository in Woodpecker:** visibility internal, pull requests allowed, not
   trusted, approval required for forks (the default). Pull requests from forks are released
   by any person with Woodpecker access (staff and authorised members of Netzbegrünung); check the diff for changes to `.woodpecker/` and
   `scripts/` first (see the known limit above).
2. **Secret, right after enabling and before the first pull-request run.** Create a token
   `woodpecker-ci-bericht-gutgesagt` for the bot account (its login is `CI_BERICHT_KONTO` in
   `ci.yaml`): this repository only, scopes
   `write:issue` and `read:repository`, nothing else. Store it in the team's password
   manager and add it in Woodpecker as secret `forgejo_ci_bericht_token`, event "Pull
   Request" only, no image filter. Woodpecker resolves secrets when it compiles a run: if
   the secret is missing or not released for pull requests, **every pull-request run fails
   with "secret not found"** before any step.
3. **Wiki secret, before merging the pull request that adds `rechtstexte-wiki.yaml`.** Create
   a token `woodpecker-rechtstexte-wiki-gutgesagt` for the bot account: this repository only,
   scope `write:repository` (the wiki needs it; what else it allows is above), no other
   scope. Store it in the team's password manager and add it in Woodpecker as secret
   `forgejo_wiki_token`, event "Push" only, no image filter. The wiki of the repository must
   stay enabled.
4. **Registry secrets, before merging the pull request that adds `build.yaml`.** A registry
   account with write access to the packages of `netzbegruenung-images`, and a token for it
   with the scope `write:package` only. Store it in the team's password manager and add it in
   Woodpecker as secrets `registry_user` (the account name) and `registry_token`, events
   "Push" and "Tag" only, image filter `woodpeckerci/plugin-docker-buildx` (so only the
   build steps see them). The plugin needs Docker inside its container: it must be on the
   list of privileged plugins of the Woodpecker server. Without the secrets the workflows
   fail before any step; `ci` is not affected. Known limit: whoever can push a tag (write
   access, the bot included) can run a changed `release.yaml` with the secret, limited to
   the plugin, which can push any image to the registry. Tags are set by the maintainer only.
5. **Required status:** after the first pull-request run, add `ci/woodpecker/pr/ci` as a
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

For checks in between, `bash scripts/check.sh --geaendert` runs only the steps the files changed
since the branch left `origin/main` (`CHECK_BASE`) reach, the working tree included; for the
frontend only the specs of the changed components and services and the specs that import them.
`integration` runs when migrations, repositories or Python modules the integration tests import
directly or indirectly changed, without `--integration`, and then needs Qdrant and PostgreSQL like
`--schritt integration`. It prints the chosen steps and why (`scripts/geaendert.py`, tests in
`scripts/tests/test_geaendert.py`). When in doubt it runs more: changes under `scripts/` or
`.woodpecker/` and paths it does not know run everything, documentation runs only
`retired-words`. The pipeline does not use `--geaendert`; it always runs every step, and so does
the full check before the merge.
