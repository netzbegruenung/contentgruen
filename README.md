# ContentGrün

**ContentGrün** is a semantic content platform for green political activism – helping users find and share relevant political content through AI-powered search.

Licensed under the [GNU Affero General Public License v3.0](./LICENSE).

## Live Systems

- **Test System**: [https://test.contentgruen.de](https://test.contentgruen.de)
  Login: `testuser` / Password: `Liebe>Hass!`

- **Production**: [https://contentgruen.netzbegruenung.de](https://contentgruen.netzbegruenung.de)
  Uses Netzbegruenung Keycloak for authentication

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
docker compose build
docker compose up
```

Access the app at [http://localhost](http://localhost). See [CONTRIBUTING.md](./CONTRIBUTING.md) for local development setup.

## Documentation

| File | Description |
|------|-------------|
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Setup and contribution guide |
| [`STATUS.md`](./STATUS.md) | Current roadmap and priorities |
| [`docs/DEV_GUIDE.md`](./docs/DEV_GUIDE.md) | Development and testing guide |
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Deployment instructions |

## Community

Questions, ideas, and bug reports go in the [issue tracker](https://git.verdigado.com/Netzbegruenung/contentgruen/issues).
