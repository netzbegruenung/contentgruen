
# 👨‍💻 Developer Guide – Gut gesagt

This guide provides advanced usage instructions for developing, testing, and debugging Gut gesagt.

It includes setup and test commands for all services, including how to run them isolated, with or without Docker.

---

## 🗂️ Project Structure (Overview)

- `mvp/frontend/` → Angular Web App
- `mvp/backend/BFF/` → Backend-for-Frontend (.NET + YARP)
- `mvp/backend/semantic-search-service/` → Semantic search backend (FastAPI + Qdrant + E5)
- `mvp/docker-compose.dev.yml` → Full containerized setup (local development)
- `mvp/docker-compose.local-dbs.yml` → Databases only (Qdrant + PostgreSQL), for component-based development

---

## 🔧 Development Setup

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality and run tests automatically before commits.

#### Installation

1. **Install pre-commit globally** (recommended):
```bash
# Using pip (Python 3.13+ recommended)
pip install --user pre-commit

# Or using pipx (if available)
pipx install pre-commit
```

2. **Install the Git hooks** (run once from project root):
```bash
cd /path/to/contentgruen
pre-commit install
```

#### What the hooks do

On every `git commit`, the following checks run automatically:
- **Unit tests** for the semantic search service (cross-platform compatible)
- **Python code formatting** with Black - automatically formats code (cross-platform compatible)
- **Trailing whitespace removal**
- **End-of-file fixes**
- **YAML validation**
- **Large file detection**

The hooks automatically detect your platform (Windows/Linux/Mac) and use the appropriate virtual environment path.

If any check fails, the commit is blocked until issues are fixed. Python files are automatically formatted by Black during the commit process.

#### Usage

- **Normal commits**: Just use `git commit` as usual - hooks run automatically
- **Skip hooks** (use sparingly): `git commit --no-verify`
- **Run manually**: `pre-commit run --all-files`
- **Run specific hook**: `pre-commit run <hook-id>`
- **Update hooks**: `pre-commit autoupdate`

#### Python Code Formatting

The project uses Black for consistent Python formatting. To format code manually:

```bash
cd mvp/backend/semantic-search-service
# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Format all Python files
black app/
```

---

## ⚙️ Frontend (Angular)

### 🧱 Install

Requires
- node v22.16
- npm 11.4

```bash
cd mvp/frontend/contentgruen-frontend
npm install
```

### ▶️ Run Locally

```bash
ng serve
```

### 🧪 Run Tests

```bash
ng test
```

### 🐳 Docker

```bash
cd mvp/frontend/contentgruen-frontend
docker build -t contentgruen-frontend:latest .
docker run -p 4200:80 -d contentgruen-frontend:latest
```

Open: [http://localhost:4200](http://localhost:4200)

---

## 🔁 Backend-for-Frontend (BFF – .NET)

### 🧱 Install

Requires:
- .NET Runtime 9.0
- .NET SDK 9.0

```bash
cd mvp/backend/BFF
dotnet restore
```

### ▶️ Run Locally

```bash
dotnet run
```

### 🐳 Docker

```bash
cd mvp/backend/BFF
docker build -t contentgruen-bff:latest .
docker run -p 5054:5054 -d contentgruen-bff:latest
```

Open: [http://localhost:5054](http://localhost:5054)

### 🧪 Manual API Tests

```bash
curl -X POST http://127.0.0.1:5054/api/v1/search/searchByText \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Windräder verschandeln die Landschaft", "limit": 3}'
```

---

## 🧠 Semantic Search Service (Python + FastAPI)

### 🧱 Install

Requirements:
- Python 3.13
- Pip
- **Windows only**: Visual Studio 2022 Build Tools (see [Build Tools Requirements](#-build-tools-requirements-windows-only) below)

```bash
cd mvp/backend/semantic-search-service
python -m venv venv
source venv/bin/activate  # or on Windows use .\venv\Scripts\activate.bat or Activate.ps1
pip install -r requirements.txt
```

#### 🔨 Build Tools Requirements (Windows only)

On Windows, some packages (annoy, hnswlib) may need to be compiled from source because pre-built wheels are not yet available. This requires:

1. Download [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Install these components (approximately 5GB):
   - **MSVC v143 - C++ Buildtools für x64/86 in VS 2022** (NOT the older versions marked "nicht mehr unterstützt")
   - **Windows 10 SDK** or **Windows 11 SDK** (latest version without "nicht mehr unterstützt" note)

**Note**: Linux/Mac users and Docker builds don't need these tools as pre-built wheels are available for those platforms.

### ▶️ Run Locally

```bash
cd mvp/backend/semantic-search-service/app
uvicorn main:app --reload
```

> First start may download models from Hugging Face

### 🧪 Run Tests

```bash
cd mvp/backend/semantic-search-service/app
pytest
```

### 🧪 API Test via curl

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search/searchByText \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Solarenergie macht unsere Umwelt kaputt", "limit": 3}'
```

### 🐳 Docker

```bash
cd mvp/backend/semantic-search-service
docker build -t contentgruen-semantic-search:latest .
docker run -p 8000:8000 -d contentgruen-semantic-search:latest
```

Open Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐋 Full Dockerized Setup

To run all services together:

```bash
cd mvp
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up
```

Then access:

* Frontend: [http://localhost](http://localhost)
* BFF (.NET): [http://localhost:5054](http://localhost:5054)
* Semantic Search: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛠 Known Issues & Fixes

### ❌ Semantic Search Service: Build Errors when installing packages from requirements.txt

**This is especially common on Windows**

If you see:

```
fatal error C1083: Datei (Include) kann nicht geöffnet werden: "stdio.h": No such file or directory
```

or similar errors when installing annoy or hnswlib, you are missing the C++ build tools.

➡️ Solution: Get the installer from here [https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

and install the following components:

> **MSVC v143 - C++ Buildtools für x64/86 in VS 2022** (choose the current version, NOT ones marked "nicht mehr unterstützt")
> **Windows 10 SDK** or **Windows 11 SDK** (latest version)

These components require approximately 5GB of disk space. After installation, packages like annoy and hnswlib will compile successfully.


### ❌ Semantic Search Service: PyTorch `fbgemm.dll` Error on Windows

If you see:

```
OSError: Error loading torch\lib\fbgemm.dll
```

you probably encounter an issue regarding specific version of the C++ build tools.

➡️ Solution: Install Visual Studio 2022 with the following component:

> `MSVC v143 - VS 2022 C++ x64/x86 Build Tools`

More info: [PyTorch issue #131662](https://github.com/pytorch/pytorch/issues/131662)

---

## 📄 Manual Test Payloads (Semantic Search Service)

The single search entry point is `POST /api/v1/search/searchByText`. It returns matching
commentaries, generic texts, posts and images for a free-text query.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search/searchByText \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Windräder verschandeln die Landschaft", "limit": 3}'
```

Anonymous requests should send a session header so usage and reporting can be tracked:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search/searchByText \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: 8cb492b4-d226-4cfc-904a-830946cefc36" \
  -d '{"query_text": "Solarenergie macht unsere Umwelt kaputt", "limit": 3}'
```

The full endpoint list is in the Swagger UI at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🙌 Contribute

For project onboarding, feature suggestions, and how to help, see:

👉 [`CONTRIBUTING.md`](../CONTRIBUTING.md)
