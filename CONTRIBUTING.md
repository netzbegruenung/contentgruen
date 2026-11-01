# Contributing to Gut gesagt

Welcome! We're glad you're interested in contributing to Gut gesagt – a semantic content platform for green political activism.

All contributions are welcome: code, design, testing, feedback, and content curation.

## License

By contributing, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](./LICENSE), the same license as the project.

## Repository

Development happens on Forgejo:
[git.verdigado.com/Netzbegruenung/gutgesagt](https://git.verdigado.com/Netzbegruenung/gutgesagt).
Issues and pull requests are managed there. Access is for people working on the project
(Netzbegrünung, verdigado).

[github.com/netzbegruenung/contentgruen](https://github.com/netzbegruenung/contentgruen) is a
read-only mirror: you can read and clone the code there, but issues and pull requests opened
there are not processed.

## Quickstart (Docker)

```bash
git clone https://github.com/netzbegruenung/contentgruen.git gutgesagt
cd gutgesagt/mvp
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up
```

- **Frontend**: [http://localhost:8080](http://localhost:8080) (host port 8080, because rootless
  Docker cannot bind ports below 1024)
- **BFF** (.NET): [http://localhost:5054](http://localhost:5054)
- **Semantic Search Service**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)
- **Sign in**: button "Anmelden" ("Direktanmeldung"), Beta-Zugang `test.user@example.com` /
  `Liebe>Hass!` from `mvp/config/managed-users.example.json`. With plain `docker compose`, copy
  that file to `mvp/config/managed-users.json` before starting, otherwise this sign-in is off
  (see [docs/DEV-SETUP.md](docs/DEV-SETUP.md)).

On Linux, `mvp/run-local.sh up` does the same in the background and creates
`managed-users.json` itself (`status`, `reset`, `logs`, `down`).

## Local Setup (component-based development)

### Prerequisites

Install pre-commit hooks before starting:

```bash
pip install --user pre-commit
pre-commit install
```

This runs formatting checks and tests before each commit. See [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) for details.

### Frontend (Angular)

```bash
cd mvp/frontend/gutgesagt-frontend
npm install
ng serve
```

### Backend-for-Frontend (BFF – .NET)

```bash
cd mvp/backend/BFF
dotnet run
```

### Semantic Search Service (Python + FastAPI)

```bash
cd mvp/backend/semantic-search-service
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cd app && uvicorn main:app --reload
```

> First start may download models from Hugging Face – requires internet access.

See [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) for full details.

## Testing

```bash
# Python (pytest.ini lives in app/)
cd mvp/backend/semantic-search-service/app && pytest

# Angular
cd mvp/frontend/gutgesagt-frontend && ng test

# .NET (test project is BFF.Tests, run from the solution directory)
cd mvp/backend && dotnet test
```

End-to-end tests (Playwright) run against the dev stack, not in CI: see
[mvp/frontend/gutgesagt-frontend/e2e/README.md](mvp/frontend/gutgesagt-frontend/e2e/README.md).

## Issues

Issues live on Forgejo. Before you open one, search whether it already exists. Describe what you
expected, what happened and how to reproduce it; for a new feature, what problem it solves.

Issues are labelled with a type and, while they are being worked out, a triage label:

| Label             | Meaning                                                      |
| ----------------- | ------------------------------------------------------------ |
| `bug`             | Something is broken                                          |
| `enhancement`     | New feature or improvement                                   |
| `needs-triage`    | A maintainer still has to evaluate the issue                 |
| `needs-info`      | Waiting for the reporter to add information                  |
| `ready-for-agent` | Fully specified; a coding agent can implement it unattended  |
| `ready-for-human` | Fully specified, but needs a person to implement it          |
| `wontfix`         | Will not be done                                             |

The triage labels follow [docs/agents/triage-labels.md](docs/agents/triage-labels.md); a maintainer
sets them. Planning happens on the
[Forgejo milestones](https://git.verdigado.com/Netzbegruenung/gutgesagt/milestones), not in a file.

## Branches

`main` is protected: nobody pushes to it directly, maintainers merge pull requests. Create a
branch in the Forgejo repository named after the kind of change, ideally with the issue number:

| Prefix    | For                                  | Example                       |
| --------- | ------------------------------------ | ----------------------------- |
| `feat/`   | New features                         | `feat/123-bildsuche`          |
| `fix/`    | Bug fixes                            | `fix/124-login-redirect`      |
| `docs/`   | Documentation only                   | `docs/125-dev-setup`          |
| `chore/`  | Tooling, dependencies, housekeeping  | `chore/126-renovate`          |

Coding agents use `sb/<issue>-<topic>`.

## Commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat: …`, `fix: …`, `docs: …`, `chore: …`), without emojis. The pre-commit hooks format Python
code and run the unit tests; if they reformat a file, commit again.

### Developer Certificate of Origin

Contributions to the code come under the
[Developer Certificate of Origin 1.1](https://developercertificate.org/) (DCO). Read it before your
first commit. Sign off every commit with your own name and address:

```bash
git commit -s -m "fix: …"
```

`-s` adds a trailer `Signed-off-by: Your Name <you@example.org>`, taken from `user.name` and
`user.email`; it must name the commit's author. To sign off commits you have already made on your
branch, run `git rebase --signoff origin/main` and push the rewritten branch again (with
`--force-with-lease`).

Woodpecker checks every pull request (step `sign-off`, [docs/CI.md](docs/CI.md)) and names the
commits without the author's sign-off. For now it does not check merge commits, nor commits a
coding agent wrote, recognised by a `Co-Authored-By` trailer with an agent's address (listed in
`scripts/sign_off.py`). Whether these exceptions stay is still open.

## Pull requests

1. Open an issue on Forgejo or comment on an existing one to coordinate
2. Create a branch as described above
3. Make your changes and run the checks: `scripts/check.sh --geaendert` while working, the full
   `scripts/check.sh --integration` before opening the pull request
4. Open a pull request against `main` on Forgejo with a clear description of what and why, and
   `Closes #<issue>`
5. Woodpecker runs the same checks on every pull request ([docs/CI.md](docs/CI.md)); a maintainer
   reviews and merges

Before starting significant work, please get in touch first to avoid duplication. Judgement rules
for reviews are in [CODING_STANDARDS.md](CODING_STANDARDS.md).

## Feedback and security

Questions and bug reports from people using Gut gesagt go through the "Feedback" button in the
app or to [gutgesagt@netzbegruenung.de](mailto:gutgesagt@netzbegruenung.de). Security
vulnerabilities: see [SECURITY.md](./SECURITY.md), never in a public issue.

## Project Structure

```
mvp/frontend/                      Angular web app
mvp/backend/BFF/                   .NET API gateway
mvp/backend/BFF.Tests/             .NET unit tests
mvp/backend/semantic-search-service/  Python search backend (FastAPI, Qdrant)
mvp/docker-compose.dev.yml         Full containerized setup (local development)
mvp/docker-compose.local-dbs.yml   Databases only, for component-based development
```

Planning: [Forgejo milestones](https://git.verdigado.com/Netzbegruenung/gutgesagt/milestones).
Current state of the project: [STATUS.md](./STATUS.md).
