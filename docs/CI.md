# CI on Woodpecker

Every pull request on Forgejo runs the pipeline `.woodpecker/ci.yaml` (workflow `ci`) on
verdigado's Woodpecker. It checks what `scripts/check.sh` checks locally; the integration
tests run only on `main`, on tags and manually (see
[Integration tests on main only](#integration-tests-on-main-only)). Its status
`ci/woodpecker/pr/ci` is required before a merge into `main` once a person has completed the
[setup](#setup-by-a-person).

After the merge, `.woodpecker/build.yaml` and, on `v*` tags, `release.yaml` build the images
(see [Images and releases](#images-and-releases)), and every night `.woodpecker/nacht.yaml`
measures search quality against the real model (see [Nightly run](#nightly-run)).
`.woodpecker/ci-image.yaml` builds the images the pipeline itself can run in, with the Python
packages, the models and `node_modules` already installed (see [CI images](#ci-images)). Until the switch the GitHub Actions on the
mirror (`.github/workflows/`) still build them too and publish the tags the environments use.

## What runs

| Step | Image | Runs |
|---|---|---|
| `retired-words` | `node:22` (frontend Dockerfile; has git and python3) | `check.sh --schritt retired-words`, lines added since the branch left the target branch; pull requests only (push, tag and manual runs have no target branch) |
| `python-installieren` | `python:3.13-slim` (semantic-search Dockerfile) | `scripts/ci-installieren.sh python`: venv at `mvp/backend/semantic-search-service/venv`, `requirements.txt` (only a link to the packages of the [CI image](#ci-images) when they match) |
| `frontend-installieren` | `node:22` | `scripts/ci-installieren.sh frontend`: `npm ci` in the frontend directory, once for the two frontend steps (or a link to the `node_modules` of the CI image) |
| `lint` | `python:3.13-slim` | `check.sh --schritt lint`: Ruff and Black with the versions pinned in `requirements.txt` |
| `bff` | `mcr.microsoft.com/dotnet/sdk:9.0` (BFF Dockerfile) | `check.sh --schritt bff` with `CHECK_OHNE_DOCKER=1` |
| `unit` | `python:3.13-slim` | `check.sh --schritt unit`: Python unit tests and `scripts/tests/`, each with two pytest-xdist workers (`CHECK_WORKER=2`; locally four) |
| `frontend-build` | `node:22` | after `unit`: `check.sh --schritt frontend-build` (`ng build --configuration production`, for the budgets of the image build) with `NG_BUILD_MAX_WORKERS=2` |
| `frontend` | same | after `frontend-build`: Chromium from Debian (`scripts/ci-chromium.sh`), `check.sh --schritt frontend` (Karma tests) with `CHECK_OHNE_SOURCEMAPS=1` (`ng test --source-map=false`) |
| `integration` | `python:3.13-slim` | push to `main`, tags and manual runs only, never in pull requests: after `frontend`, `check.sh --schritt integration` with `INTEGRATION_STACK_PFLICHT=1` against the services below, serially |
| `ci-bericht` | `python:3.13-slim` | red pull-request runs only, see below |

Services (started only when `integration` runs, same `when`): `qdrant` (same version as the
compose files and `.github/workflows/tests-backend.yml`,
`entrypoint: /qdrant/qdrant`; without the absolute path the service does not start) and `postgres` (base image of
`mvp/backend/postgres-app`). The integration step reaches them through `QDRANT_URL` and
`POSTGRES_TEST_DATABASE_URL`, after `scripts/ci_dienste_warten.py` has waited (up to two
minutes) until both accept connections; the throwaway container of the suite is not used, the runner
has no Docker socket. There is no BFF either: the tests in `tests/integration/api/`, which need
the dev-stack BFF, skip in CI (`CI` set) instead of failing, and show up in the `SKIPPED` lines.
A hanging integration test fails instead of stalling the step: every test session has
`lock_timeout` 60 s and `statement_timeout` 120 s (`tests/integration/postgres.py`), a test
running over 5 min dumps the stacks of all threads (`faulthandler_timeout`), and `check.sh` stops
the whole step after `INTEGRATION_ZEITLIMIT` (default 25 min). Before that, main pipeline 1257
sat silent for 46 min until it was cancelled.
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
  already has locally stays out of `check.sh`: the venv (`python-installieren`), `npm ci`
  (`frontend-installieren`), both through `scripts/ci-installieren.sh`, and Chromium for the
  frontend (`scripts/ci-chromium.sh`). `check.sh` installs nothing, so it needs no
  knowledge of the CI images. `CHECK_VOLL=1`
  makes `check.sh` print the full output instead of its summary lines.
- **No path filter on the workflow.** A skipped workflow reports no status, and the
  required status then blocks the pull request. Filters only per step, and only so that
  `ci` still reports (see [Path filters](#path-filters)).
- **Events:** `pull_request`, `push` on `main`, `tag` and `manual`. Without `manual`,
  "Run pipeline" in the Woodpecker UI filters the workflow out.
- The clone step fetches the full history and the target branch (`fetch-target-branch`),
  so `retired-words` can find where the branch started.

**Staggered steps.** The runner is shared with the other pipelines of the Woodpecker
instance. With the heavy steps side by side, on 13.11. its memory ran out and many pipelines
were cancelled together. So the four heavy steps (three in pull requests, without `integration`) run one after the other, never two at once, in one chain of `depends_on`;
the light ones (`retired-words`, `lint`, `bff` and the two installations) run alongside.
The chain goes shortest first, so a quick failure shows early: `unit` (about half a minute),
`frontend-build`, `frontend` (Chromium and Karma), `integration` (loads the embedding model,
the longest). Each of the four also runs when the run is already red
(`status: [success, failure]`): Woodpecker's default skips a step once any step has failed,
so an early red light step would skip `unit`, and a red `unit` would leave `ci-bericht`
without the results after it. A failed installation therefore makes the heavy steps that
need it red as well. A run takes longer than with the
steps in parallel; that is the price of not running the host out of memory.
`scripts/tests/test_woodpecker_ci.py` checks the chain and the settings below.

- `unit` runs pytest with two xdist workers in CI (`CHECK_WORKER=2`), four locally (`-n`;
  `CHECK_WORKER=0` runs serially). Every worker collects the tests itself, so parametrized
  test IDs must not contain random values such as `uuid4()`, otherwise xdist aborts with
  "Different tests were collected". The integration step stays serial: every worker would
  load the embedding model again and the suite sizes its torch threads for one process
  (`tests/integration/conftest.py`).
- `frontend-build` sets `NG_BUILD_MAX_WORKERS=2`: `@angular/build` otherwise starts
  min(4, cores - 1) worker threads for the JavaScript transformer and Sass
  (`src/utils/environment-options.js`). `frontend` runs `ng test --source-map=false`
  (`CHECK_OHNE_SOURCEMAPS=1`): the same specs, but stack traces of a failing spec point
  into the bundle instead of the `.ts` file; rerun it locally for the mapped trace.
- `frontend` and `frontend-build` share one `npm ci` (`frontend-installieren`). Steps share
  the workspace, so only one step may run `npm ci` there; a second one would delete
  `node_modules` under the other step (`scripts/tests/test_woodpecker_ci.py` checks it).
  Angular's build cache is off in CI (`CI` set).

**Path filters.** In pull requests a step drops out when every changed file of the pull
request lies in parts of the repository it does not read. Woodpecker asks Forgejo for the
files of the pull request (the whole diff against the target branch, not only the last
push) and checks them against `path.exclude`: the step is skipped only if all files match.
Anything not listed, `.woodpecker/`, `scripts/check.sh` and the other shell scripts, the
documentation and `mvp/config/` therefore run everything. If Forgejo returns no file list,
everything runs too (`on_empty`). A push to `main`, tags and manual runs always run every
step.

| Step | Skipped when only these change |
|---|---|
| `frontend-installieren`, `frontend-build`, `frontend` | `mvp/backend/**`, `mvp/scripts/**`, `scripts/**/*.py` |
| `lint` | `mvp/frontend/**`, the BFF (`mvp/backend/BFF/**`, `BFF.Tests/**`, `GutGesagt.sln`) |
| `bff` | `mvp/frontend/**`, `mvp/backend/semantic-search-service/**`, `mvp/backend/postgres-app/**`, `mvp/scripts/**`, `scripts/**/*.py` |
| `retired-words`, `python-installieren`, `unit` | never |
| `integration` | not applicable, it never runs in pull requests |

- `python-installieren` and `unit` always run: unit tests and `scripts/tests/` also read
  frontend and BFF files (CSS variables, unused endpoints, profile pictures, ...), so a
  frontend-only change can turn them red.
- A step that `when` filters out is not part of the pipeline at all. Woodpecker rejects
  a pipeline in which a step depends on a missing step, unless the dependency is marked
  `optional: true` (Woodpecker 3.15 and later). So `integration` depends on `frontend`
  optionally (without it, it waits for `unit`), and `ci-bericht` lists every filtered
  step as optional; `integration` is not in its list at all, since the report only runs in
  pull requests, where `integration` never runs. Skipped steps do not make the run red;
  `ci-bericht` lists them under
  "Nicht gelaufen".
- `scripts/tests/test_woodpecker_ci.py` replays Woodpecker's filtering for typical
  pull requests and checks that the heavy steps never overlap and no dependency is missing.

**No light runs for WIP pull requests.** A lighter pipeline while the title starts with
"WIP:" was considered and dropped. Editing the title or a label makes Woodpecker 3.20
start a run with the event `pull_request_metadata`, and its status context is
`ci/woodpecker/pull_request_metadata/ci`, not the required `ci/woodpecker/pr/ci`. The
required status would stay green from the light run, and the full run after removing
"WIP:" would not be required for the merge. An empty push after removing "WIP:" would
fix the status but depends on nobody forgetting it.

## Integration tests on main only

Decided on 14.11.: `integration` runs on a push to `main`, on tags (`release.yaml` waits for
`ci`, so no release skips them) and on "Run pipeline", never in pull-request runs. The
services `qdrant` and `postgres` have the same `when` and do not start in pull requests
either. Pull-request runs lose their longest step (several minutes on the shared runner,
loading the embedding model).

- **The price:** a pull request can be green and still break the integration tests on
  `main`. Then a red `main` takes precedence over new work: fix it first (or revert), and
  check `ci/woodpecker/push/ci` after every merge; nothing reports a red `main` by itself.
  As long as `main` is red, `build.yaml` (it waits for `ci`) builds no images, so nothing
  new reaches test or production.
- Whoever wants the integration tests before the merge runs them locally
  (`bash scripts/check.sh --schritt integration`, or `--geaendert`, which picks them when
  the changes reach them) or starts "Run pipeline" on the branch.
- Woodpecker 3.20.1 (`pipeline/frontend/yaml/compiler/dag.go`): a step that `when` filters out
  is dropped together with every optional dependency on it; a missing required one rejects
  the pipeline. Nothing depends on `integration`, so pull requests lose only that step.
  Services are filtered by the same `when` (`compiler.go`, services stage).

## CI images

`Dockerfile.ci` has two targets, built by `.woodpecker/ci-image.yaml` with the same plugin,
registry and secrets as `build.yaml`:

| Image | Base | Contains | For the steps |
|---|---|---|---|
| `gutgesagt-ci-python` | `python:3.13-slim` | the packages of `requirements.txt` system-wide; the models `intfloat/multilingual-e5-base` and `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` under `HF_HOME=/opt/ci/huggingface` | `python-installieren`, `lint`, `unit`, `integration` |
| `gutgesagt-ci-node` | `node:22` (same digest) | Chromium with the wrapper of `scripts/ci-chromium.sh`; `node_modules` from `package-lock.json` under `/opt/ci/node_modules`; the npm cache | `frontend-installieren`, `frontend-build`, `frontend` |

Tags: `latest` and the first 12 characters of the checksum of the files the packages come
from (`scripts/ci-installieren.sh --pruefsumme python|frontend`: `requirements.txt`, or
`package.json` and `package-lock.json`). Measured locally on 13.11.: about 1.9 GB (Python)
and 0.8 GB (Node) compressed in the registry; the Node image shares its base layers with
`node:22`.

- **Every run checks the image** (in the installation step). The image keeps the checksum under `/opt/ci/`.
  `scripts/ci-installieren.sh` compares it with the checkout. If it matches, the venv is
  created with `--system-site-packages` and pip does nothing (2 s instead of about 85 s
  locally, about 2 min in CI), and `node_modules` becomes a link to `/opt/ci/node_modules`.
  If it does not match (a pull request changes `requirements.txt` or `package-lock.json`, or
  the image is behind), the step installs as without an image: pip only installs what differs
  from the packages in the image (13 s locally for one changed pin), `npm ci --prefer-offline`
  takes what it can from the npm cache of the image. Known price: a package that the pull
  request removes from `requirements.txt` is still importable from the image until it is
  rebuilt; the service image would then fail on the import, the CI not. In the plain `python:3.13-slim` and
  `node:22` images there is no checksum and everything is installed. No pull request turns
  red because the image is old.
- **Models without offline mode.** Unlike the service image, the CI image does not set
  `HF_HUB_OFFLINE`: if a pull request switches to a model the image does not have, the
  run downloads it as before. The confirmer (`NLI_BESTAETIGER_MODELL`, 2.2 GB) is left out;
  it is off by default and no test loads it. Locally the integration suite passed with
  `HF_HUB_OFFLINE=1` in the image, so the two models are all it needs.
- **When it is built:** after a push to `main` that changes what an image contains (path
  filter per build step: `Dockerfile.ci`, `Dockerfile.ci.dockerignore`, the lockfiles,
  `scripts/ci-installieren.sh`, for Node also `scripts/ci-chromium.sh`, and the workflow),
  weekly by the cron job `ci-image` (new versions within the `>=` ranges of
  `requirements.txt`, new model revisions, security updates of `python:3.13-slim`), and
  with "Run pipeline" on `main`. The workflow waits for `ci` and `build` (both optional:
  a cron run has neither, and `build` drops out when no image step matches), so it never
  builds next to the heavy steps; if `ci` is red on `main`, it does not build and the next
  cron run catches up. The two images are built one after the other; `ci-node` does not
  build after a red step before it.
- The build context is the repository root, cut down by `Dockerfile.ci.dockerignore` to the
  files the Dockerfile copies (`scripts/tests/test_woodpecker_ci.py` keeps both lists and
  the path filters equal).
- The images contain nothing secret and are public like the other images of
  `netzbegruenung-images`, so the pipeline pulls them without a login.
- **Switching `ci.yaml` to the images** is a separate pull request after the first build:
  until `:latest` exists in the registry, a step with that image cannot start, and a
  missing image is the one case the checksum cannot catch. The steps then name
  `gutgesagt-ci-python:latest` or `gutgesagt-ci-node:latest` with `pull: true`;
  `retired-words` and `ci-bericht` stay on the plain images.

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

## Nightly run

`.woodpecker/nacht.yaml` (workflow `nacht`, #391) measures the Messset and the
Suchtestset against the real embedding model, every night and on request. Both decide
whether a change to the model, a threshold, the stemmer or the normalisation shifts
results; they are too slow for every pull request (several minutes, over 1 GB RAM for the
model), so the run is not a required status.

| Step | Runs | Red when |
|---|---|---|
| `messset` | `pytest tests/regression/test_aehnlichkeit_messset.py -m langsam`, then the table per Paar-Label | a score differs from `aehnlichkeit_gemessen.py` by more than 0.005, or a decision of the Dublettenprüfung changes (`MESSSET.md`) |
| `suchtest` | waits for the services (`scripts/ci_dienste_warten.py`), `tests.regression.seed_laden` loads the seed into an empty collection of the service `qdrant`, `tests.regression.nachtlauf` measures the Suchtestset at today's threshold and prints the tables and the checks | a number differs from the Soll by more than one case (in either direction), or the gate for Roadmap-Stufe 3 or the lower bound for ähnliche Aussagen is not met (`SUCHTESTSET.md`, „Nächtlicher Lauf“) |

- **Model cache:** both steps run in the image of the semantic search service
  (`gutgesagt-semantic-search:main`, pulled anew each run, `pull: true`; the package is
  public, no registry login), which downloads the model at build time. The code
  measured is the checkout; pip only installs what `requirements.txt` changed.
  `HF_HUB_OFFLINE=1` keeps the run on the model revision baked into the image instead of
  whatever the hub serves that night. The image itself sets it too, after the preload
  steps of its Dockerfile, so production and the dev stack never ask the hub either (#578);
  the step's `environment` overrides the image. A pull request that switches to another
  model adds a preload step for it to the Dockerfile and sets `HF_HUB_OFFLINE` to `"0"` in
  `nacht.yaml` on its branch for the manual run, so the run downloads the new model (the
  `:main` image does not have it yet), and back to `"1"` before the merge:
  `scripts/tests/test_woodpecker_ci.py` keeps `ci` red until then, so `"0"` never lands on
  `main`.
- **Services:** `qdrant` and `postgres`, the same as in `ci.yaml` (`scripts/tests/test_woodpecker_ci.py`
  keeps them equal). `suchtest` needs the database: starting the services
  (`dependencies.initialize_services`) creates the `VotingService`, which opens the app
  database and creates its tables. The step points `SEMANTIC_SEARCH_APP_DATABASE_URL` at
  `postgres:5432`; without it the run fails with „Connection refused“ on `localhost:5433` (#576).
- `suchtest` also runs after a red `messset`, one after the other: each step loads the
  model.
- The log line „Folder not found: …/index_data/content_index“ while loading the seed is
  harmless: the aggregated `ContentRepository` looks for initial data in
  `index_data/content_index`, which the seed does not have (it keeps everything under
  `statements_with_*`), finds nothing and loads the seed the regular way. Seeding logs it in
  the dev stack too.
- Always against the seed in the service `qdrant` of the run, never against test or
  production. No secret and no report step (there is no pull request to comment on): a red
  run is visible in Woodpecker.
- **When a pull request must trigger the run:** if it changes the embedding model,
  a threshold (`MINIMUM_SCORE_THRESHOLD` in `services/search/search_orchestrator.py`,
  `aussage_vorschlag_schwelle` in `core/config.py`),
  the stemmer, the normalisation (`utils/text_normalisierung.py`), the search pipeline, the
  seed, the Messset or the Suchtestset. Run it with "Run pipeline" on the pull-request
  branch (not on `main`: there a manual run also builds every image, `build.yaml`) and name
  the result in the pull request. `ci` runs alongside (it reacts to `manual` too), so the
  agent carries both at once for a few minutes. The other way round as well: every manual
  run, also one meant for `ci` or the images, starts the nightly run. If a number changes
  on purpose, update the Soll in the same pull request (`aehnlichkeit_gemessen.py` or
  `SOLL` in `nachtlauf.py`).
- Locally: the commands in `MESSSET.md` and `SUCHTESTSET.md`.

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
  `package.json` once the GitHub workflows are gone (`docs/DEPLOYMENT.md`, "Releases").
  Builds of `main` pass `APP_VERSION=main`: the footer shows „main · <commit>“ instead of a
  version that would go stale.
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
   `.github/workflows/`; update this section and `docs/DEPLOYMENT.md` (the `package.json`
   step in "Releases" goes, the GitHub CI paragraph in "Updating Production" too).
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
   with the scope `write:package` only. The account is the Forgejo user `WoodpeckerCI` in the
   team "Pipelines" of the organisation `netzbegruenung-images` (unit "Packages": write); the
   release bot of the organisation has no package rights. When creating the token, choose the
   repository access "All (public, private, and limited)" and only "package: Read and Write":
   with "Specific repositories" Forgejo offers no package scope. Store it in the team's password
   manager and add it in Woodpecker as secrets `registry_user` (the account name) and
   `registry_token`, events "Push", "Tag" and "Manual" (for "Run pipeline" on `main`), image filter
   `woodpeckerci/plugin-docker-buildx` (so only the build steps see them). The plugin needs
   Docker inside its container: it must be on the list of privileged plugins of the
   Woodpecker server as `woodpeckerci/plugin-docker-buildx`, without a tag. The workflows pin
   the plugin by tag and digest, and an entry with a tag only matches that exact reference.
   In the repository settings, switch on "Cancel previous pipelines" for "Push": otherwise
   two quick merges can build in parallel, and the older one, finishing last, leaves `:main`
   on the older commit (the GitHub CI cancelled superseded runs too). Without the secrets
   the workflows fail before any step; `ci` is not affected. Known limit: Woodpecker has no
   branch filter for secrets. Whoever can push a branch or a tag (write access, the bot
   included) can run a changed `build.yaml` or `release.yaml` with the secret, limited to
   the plugin, which can push any image under any tag to the registry, `:main` included.
   The same holds for `forgejo_wiki_token`. Tags are set by the maintainer only.
5. **Required status:** after the first pull-request run, add `ci/woodpecker/pr/ci` as a
   required status check in the branch protection of `main`, and switch on "pull request
   must be up to date", so combinations of two pull requests run before the merge. A branch
   is brought up to date by merge ("Update branch"), not by rebase. Whoever wants a linear
   `main` sets the merge style to squash.

6. **CI images, before merging the pull request that adds `ci-image.yaml`:** release the
   secrets `registry_user` and `registry_token` (step 4) also for the event "Cron", so the
   weekly build can push; nothing else changes (same plugin, same image filter, already
   privileged). After the merge, add a cron job named `ci-image` (the workflow only reacts
   to this name), branch `main`, schedule e.g. `0 4 * * 0` (Sundays at 04:00, after the
   nightly run). The merge itself builds both images, since it changes the workflow; if
   that run is red, start the cron job once with "Run now", so `:latest` exists before
   `ci.yaml` switches to the images.

7. **Cron job for the nightly run,** after the pull request that adds `nacht.yaml` is
   merged: in the repository settings of Woodpecker, "Cron", add a job named `nachtlauf`
   (the workflow only reacts to this name), branch `main`, schedule e.g. `0 3 * * *`
   (every night at 03:00). No secret needed.

Check without admin rights: `GET /api/v1/repos/<owner>/<repo>/branches/main` shows
`enable_status_check` and `status_check_contexts`.

## Running a step locally

`bash scripts/check.sh --schritt <name>` runs one step against the working tree (for
`integration` with Qdrant and PostgreSQL as described in the
[testing guide](../mvp/backend/semantic-search-service/app/tests/TESTING_GUIDE.md)).
`bash scripts/check.sh --integration` runs all of them.

**Before a push, `bash scripts/check.sh --geaendert` is enough.** The full run, with
all specs and the BFF, is the pipeline's job (the integration tests on `main`); run it
locally only when the pipeline is red and you need the full output.

`bash scripts/check.sh --geaendert` runs only the steps the files changed
since the branch left `origin/main` (`CHECK_BASE`) reach, the working tree included; for the
frontend only the specs of the changed components and services and the specs that import them.
The production build (`frontend-build`) runs for every frontend change except one touching only
specs or `tsconfig.spec.json`, which the build does not read; `e2e/` (Playwright against the dev
stack) runs neither Karma nor the build.
`integration` runs when migrations, repositories or Python modules the integration tests import
directly or indirectly changed, without `--integration`, and then needs Qdrant and PostgreSQL like
`--schritt integration`. It prints the chosen steps and why (`scripts/geaendert.py`, tests in
`scripts/tests/test_geaendert.py`). When in doubt it runs more: changes under `scripts/` or
`.woodpecker/` and paths it does not know run everything, documentation runs only
`retired-words`. The pipeline does not use `--geaendert`; on `main` it runs every step, pull
requests see [Path filters](#path-filters) and [Integration tests on main only](#integration-tests-on-main-only).
