# ContentGrün Scripts Guide

All scripts are located in the `mvp/scripts/` directory and organized by category.

## Quick Reference

| Task | Windows | Unix/Linux/Mac |
|------|---------|----------------|
| **Start local development** | `scripts\dev\run-local.bat` | `scripts/dev/run-local.sh` |
| **Start Docker environment** | `scripts\dev\run-docker.bat` | `scripts/dev/run-docker.sh` |
| **Run all tests** | `scripts\test\run-all-tests.bat` | `scripts/test/run-all-tests.sh` |
| **Check environment** | `scripts\setup\check-environment.bat` | `scripts/setup/check-environment.sh` |
| **Install dependencies** | `scripts\setup\install-dependencies.bat` | `scripts/setup/install-dependencies.sh` |
| **Clean everything** | `scripts\utils\clean-all.bat` | `scripts/utils/clean-all.sh` |
| **Create backup** | N/A (Linux/Unix only) | `scripts/backup/backup.sh` |
| **Restore backup** | N/A (Linux/Unix only) | `scripts/backup/restore.sh` |
| **Test backup/restore** | N/A (Linux/Unix only) | `scripts/backup/test-backup-restore.sh` |

## Directory Structure

```
mvp/scripts/
├── dev/                    # Development environment launchers
│   ├── run-local.*        # Start all services locally
│   ├── run-docker.*       # Start all services in Docker
│   └── run-docker-postgres.*  # Start only PostgreSQL in Docker
├── test/                   # Test runners
│   ├── run-all-tests.*   # Run all tests (backend, frontend, BFF)
│   ├── run-backend-tests.*   # Run Python backend tests only
│   ├── run-frontend-tests.*  # Run Angular frontend tests only
│   └── run-bff-tests.*   # Run .NET BFF tests only
├── setup/                  # Setup and installation
│   ├── check-environment.*   # Verify development environment
│   └── install-dependencies.*  # Install all project dependencies
├── backup/                 # Backup and restore (Linux/Unix only)
│   ├── backup.sh          # Create backup of Qdrant + PostgreSQL
│   ├── restore.sh         # Restore from backup
│   ├── test-backup-restore.sh  # Test backup/restore workflow
│   └── README.md          # Detailed backup documentation
└── utils/                  # Utility scripts
    ├── clean-all.*        # Clean all build artifacts and dependencies
    ├── switch-to-docker.* # Configure for Docker mode
    └── switch-to-local.*  # Configure for local mode
```

## Development Scripts (`scripts/dev/`)

### run-local
Starts all services in local development mode:
- PostgreSQL in Docker container
- Python Semantic Search API (port 8000)
- .NET BFF (port 5054)
- Angular Frontend (port 4200)

**Features:**
- Automatic virtual environment setup
- Dependency installation
- Environment configuration
- Live reload for all services

### run-docker
Starts all services in Docker containers:
- Uses `docker-compose.dev.yml`
- Frontend accessible on port 80
- All services networked together

### run-docker-postgres
Starts only PostgreSQL with pgvector extension:
- Useful for local development with database only
- Port 5432
- Persistent volume for data

## Test Scripts (`scripts/test/`)

### run-all-tests
Orchestrates all test suites:
1. Python backend unit tests
2. Angular frontend tests (headless Chrome)
3. .NET BFF tests

Returns appropriate exit codes for CI/CD integration.

### run-backend-tests
Runs Python pytest suite:
- Unit tests only (excludes integration tests)
- Skips seeding implementation tests (requires special setup)
- Uses virtual environment

### run-frontend-tests
Runs Angular tests:
- Uses `npm run test:ci` (headless, no-watch mode)
- ChromeHeadless browser
- Suitable for CI/CD

### run-bff-tests
Runs .NET tests:
- Uses `dotnet test`
- Includes all BFF unit and integration tests

## Setup Scripts (`scripts/setup/`)

### check-environment
Comprehensive environment verification:
- Checks for required tools (Docker, .NET, Node.js, Python)
- Verifies Docker is running
- Checks for port conflicts
- Cross-platform compatible

### install-dependencies
Installs all project dependencies:
1. Python: Creates venv, installs from requirements.txt
2. .NET: Runs `dotnet restore`
3. Node.js: Runs `npm install`

Run this after cloning the repository or after running `clean-all`.

## Backup Scripts (`scripts/backup/`) - Linux/Unix Only

### backup
Creates a complete backup of Qdrant and PostgreSQL:
- Qdrant vector database (content + embeddings)
- PostgreSQL metadata (usage tracking)
- Backup metadata with checksums
- Stored in `/opt/contentgruen-backups/daily/backup_YYYYMMDD_HHMMSS/`
- On Sundays, additionally copied to `/opt/contentgruen-backups/weekly/`
- Creates the backup directories on first run
- Automatic rotation keeps the last 7 daily and 4 weekly backups
  (`KEEP_DAILY` / `KEEP_WEEKLY` at the top of the script)

**Usage:**
```bash
scripts/backup/backup.sh
```

### restore
Restores data from a backup:
- Prompts for confirmation (destructive operation)
- Stops application container
- Restores Qdrant snapshot
- Restores PostgreSQL database
- Restarts application container
- Verifies restoration

**Usage:**
```bash
# Paths are resolved relative to /opt/contentgruen-backups/
scripts/backup/restore.sh daily/latest                    # Restore latest daily backup
scripts/backup/restore.sh weekly/latest                   # Restore latest weekly backup
scripts/backup/restore.sh daily/backup_20250916_103000    # Restore a specific backup
```

### test-backup-restore
End-to-end test of backup/restore functionality:
- Counts current data state
- Creates backup
- Adds test marker to Qdrant
- Restores from backup
- Verifies data integrity
- Checks API health

**Usage:**
```bash
scripts/backup/test-backup-restore.sh
```

**Note:** Backup scripts are Linux/Unix only and require:
- Docker running with ContentGrün containers
- `/opt/contentgruen-backups/` directory (created by setup script)
- GNU coreutils (stat, md5sum, readlink)

See `scripts/backup/README.md` for detailed documentation.

## Utility Scripts (`scripts/utils/`)

### clean-all
Complete environment cleanup:
- Stops and removes all Docker containers and volumes
- Removes Python virtual environment and cache
- Removes .NET build artifacts
- Removes node_modules and Angular cache
- **WARNING:** Destructive operation, requires reinstallation

### switch-to-docker / switch-to-local
Environment configuration helpers:
- Updates `environment.ts` for the appropriate mode
- Docker mode: Empty baseUrl (uses nginx proxy)
- Local mode: baseUrl points to localhost:5054

## Platform Notes

### Windows
- All scripts have `.bat` versions
- Use backslashes in paths: `scripts\dev\run-local.bat`
- PowerShell wrapper available for run-local

### Unix/Linux/Mac
- All scripts have `.sh` versions
- Make scripts executable: `chmod +x scripts/**/*.sh`
- Use forward slashes: `scripts/dev/run-local.sh`

### Cross-Platform Features
- Consistent behavior across platforms
- Color-coded output on Unix systems
- Proper error handling and exit codes
- Environment detection for Python venv

## Common Workflows

### First-Time Setup
```bash
# 1. Check your environment
scripts/setup/check-environment.bat

# 2. Install all dependencies
scripts/setup/install-dependencies.bat

# 3. Start development
scripts/dev/run-local.bat
```

### Daily Development
```bash
# Start local environment
scripts/dev/run-local.bat

# Or start Docker environment
scripts/dev/run-docker.bat
```

### Before Committing
```bash
# Run all tests
scripts/test/run-all-tests.bat
```

### Clean Restart
```bash
# 1. Clean everything
scripts/utils/clean-all.bat

# 2. Reinstall dependencies
scripts/setup/install-dependencies.bat

# 3. Start fresh
scripts/dev/run-local.bat
```

### Switching Environments
```bash
# Switch from local to Docker
scripts/utils/switch-to-docker.bat
scripts/dev/run-docker.bat

# Switch from Docker to local
scripts/utils/switch-to-local.bat
scripts/dev/run-local.bat
```

## Troubleshooting

### Port Conflicts
Run `scripts/setup/check-environment.bat` to identify conflicting services.

### Missing Dependencies
Run `scripts/setup/install-dependencies.bat` to install all requirements.

### Tests Failing
- Check individual test scripts for specific service tests
- Ensure all dependencies are installed
- Verify services are not running (for unit tests)

### Clean Start
If experiencing issues, run `scripts/utils/clean-all.bat` followed by `scripts/setup/install-dependencies.bat`.

## Script Conventions

- **Naming**: Hyphen-separated lowercase (e.g., `run-local.bat`)
- **Exit Codes**: 0 for success, non-zero for failure
- **Output**: Colored on Unix, clear status messages
- **Error Handling**: All scripts check for errors and provide helpful messages
- **Cross-Platform**: Every `.bat` has a corresponding `.sh`
