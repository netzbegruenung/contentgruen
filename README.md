# Gut gesagt

**Gut gesagt** is a semantic content platform for green political activism – helping users find and share relevant political content through AI-powered search.

Licensed under the [GNU Affero General Public License v3.0](./LICENSE).

The hand in the logo, favicon, Siegel and vote buttons is the "Thumbs up" emoji from [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) (MIT, Copyright Microsoft Corporation), see [FLUENT-EMOJI-LIZENZ.txt](./mvp/frontend/gutgesagt-frontend/public/marke/FLUENT-EMOJI-LIZENZ.txt). The profile pictures are Fluent Emoji 3D as well, see [public/avatars/FLUENT-EMOJI-LIZENZ.txt](./mvp/frontend/gutgesagt-frontend/public/avatars/FLUENT-EMOJI-LIZENZ.txt).

## Live Systems

- **Test System**: https://gutgesagt-test.netzbegruenung.de
  Login: `testuser` / Password: `Liebe>Hass!`

- **Production**: [https://gutgesagt.netzbegruenung.de](https://gutgesagt.netzbegruenung.de)
  Uses Netzbegruenung Keycloak for authentication.
  `contentgruen.de` currently redirects here.

## Project Overview

Gut gesagt is a containerized web application with three main components:

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
| [`docs/DEV-SETUP.md`](./docs/DEV-SETUP.md) | `ng serve` against the Docker dev stack (proxy, no frontend container) |
| [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) | Deployment instructions |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | System architecture |
| [`docs/CONTENT_MODEL.md`](./docs/CONTENT_MODEL.md) | Content-type architecture |
| [`docs/VISION.md`](./docs/VISION.md) | Purpose, audience and limits of the product (German) |
| [`docs/ROADMAP.md`](./docs/ROADMAP.md) | Long-term direction |

## Feedback, questions and bug reports

- **Using Gut gesagt:** use the "Feedback" button in the app, or write to
  [gutgesagt@netzbegruenung.de](mailto:gutgesagt@netzbegruenung.de).
- **Security vulnerabilities:** do not report them publicly, see [SECURITY.md](./SECURITY.md).
- **Development:** issues and pull requests live on Forgejo
  ([git.verdigado.com/Netzbegruenung/gutgesagt](https://git.verdigado.com/Netzbegruenung/gutgesagt)),
  see [CONTRIBUTING.md](./CONTRIBUTING.md).

The GitHub repository [netzbegruenung/contentgruen](https://github.com/netzbegruenung/contentgruen)
is a read-only mirror. Issues and pull requests opened there are not processed.
