# Contributing to ContentGrün

Welcome! We're glad you're interested in contributing to ContentGrün – a semantic content platform for green political activism.

All contributions are welcome: code, design, testing, feedback, and content curation.

## License

By contributing, you agree that your contributions will be licensed under the [GNU Affero General Public License v3.0](./LICENSE), the same license as the project.

## Repository

[https://github.com/netzbegruenung/contentgruen](https://github.com/netzbegruenung/contentgruen)

Issues and pull requests are managed there.

## Quickstart (Docker)

```bash
git clone https://github.com/netzbegruenung/contentgruen.git
cd contentgruen/mvp
docker compose build
docker compose up
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
cd mvp/frontend/contentgruen-frontend
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
uvicorn app.main:app --reload
```

> First start may download models from Hugging Face – requires internet access.

See [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) for full details.

## Testing

```bash
# Python
cd mvp/backend/semantic-search-service && pytest

# Angular
cd mvp/frontend/contentgruen-frontend && ng test

# .NET
cd mvp/backend/BFF && dotnet test
```

## Contribution Flow

1. Open an issue or comment on an existing one to coordinate
2. Fork the repository on [GitHub](https://github.com/netzbegruenung/contentgruen)
3. Create a feature branch: `feature/<your-feature>`
4. Make your changes and run the tests
5. Open a pull request with a clear description of what and why

Before starting significant work, please get in touch first to avoid duplication.

## Community

Questions and discussion go in the [issue tracker](https://github.com/netzbegruenung/contentgruen/issues).

## Project Structure

```
mvp/frontend/                      Angular web app
mvp/backend/BFF/                   .NET API gateway
mvp/backend/semantic-search-service/  Python search backend (FastAPI, Qdrant)
mvp/docker-compose.yml             Full containerized setup
```

See [STATUS.md](./STATUS.md) for the current roadmap.
