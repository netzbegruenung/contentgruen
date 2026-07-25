# ContentGrün

**ContentGrün** is a semantic content platform for green political activism – helping users find and share relevant political content through AI-powered search.

Licensed under the [GNU Affero General Public License v3.0](./LICENSE).

## Live Systems

- **Test System**: https://contentgruen-test.netzbegruenung.de
  Login: `testuser` / Password: `Liebe>Hass!`
  (The older [test.contentgruen.de](https://test.contentgruen.de) is being discontinued.)

- **Production**: [https://contentgruen.netzbegruenung.de](https://contentgruen.netzbegruenung.de)
  Uses Netzbegruenung Keycloak for authentication.
  `contentgruen.de` currently redirects here.

## Project Overview

ContentGrün is a containerized web application with three main components:

- **Frontend** (Angular) – served via Nginx
- **BFF** (Backend-for-Frontend, .NET + YARP) – authentication & API gateway
- **Semantic Search Service** (Python + FastAPI) – semantic search using Qdrant and E5 multilingual embeddings

See `architecture.png` for a system overview.

## Getting Started

```bash
git clone https://github.com/netzbegruenung/contentgruen.git
cd contentgruen/mvp
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up
```

Access the app at [http://localhost](http://localhost). See [CONTRIBUTING.md](./CONTRIBUTING.md) for local development setup.

## Documentation

| File | Description |
|------|-------------|
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Setup and contribution guide |
| [`STATUS.md`](./STATUS.md) | Current status and priorities |
| [`docs/DEV_GUIDE.md`](./docs/DEV_GUIDE.md) | Development and testing guide |
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Deployment instructions |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System architecture |
| [`docs/CONTENT_MODEL.md`](./docs/CONTENT_MODEL.md) | Content-type architecture |
| [`docs/ROADMAP.md`](./docs/ROADMAP.md) | Long-term direction |

## Community

Questions, ideas, and bug reports go in the [issue tracker](https://github.com/netzbegruenung/contentgruen/issues).
