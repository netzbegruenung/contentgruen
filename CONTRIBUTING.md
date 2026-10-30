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
git clone https://github.com/netzbegruenung/contentgruen.git
cd contentgruen/mvp
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up
```

- **Frontend**: [http://localhost](http://localhost)
- **BFF** (.NET): [http://localhost:5054](http://localhost:5054)
- **Semantic Search Service**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

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

## Contribution Flow

1. Open an issue on Forgejo or comment on an existing one to coordinate
2. Create a branch in the Forgejo repository: `feature/<your-feature>`
3. Make your changes and run the tests (`scripts/check.sh`)
4. Open a pull request on Forgejo with a clear description of what and why

Before starting significant work, please get in touch first to avoid duplication.

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

See [STATUS.md](./STATUS.md) for the current roadmap.
