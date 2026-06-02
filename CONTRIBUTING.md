## 💻 Local Environment Prerequisites

To run this platform inside its optimized multi-container development environment, your local host machine must satisfy the following system requirements:

1. **Docker Engine**: Docker must be installed and running on your host machine.
2. **VS Code**: Install the from Microsoft. 
3. **VS Code Extensions**: Ensure you have the official **Dev Containers** extension installed on your host machine.

### Launching the Workspace

Once your host machine matches the steps above:
1. Clone this repository
2. Open the directory in your IDE
3. Press `F1` or `Ctrl+Shift+P` and choose **Dev Containers: Reopen in Container**.
4. The extension will automatically parse your local configurations, spin up the active background services (MinIO and Azurite), and install all required depencencies. Within the dev container you can run pytest etc.



# Contributing Guidelines

Thank you for contributing to the Environmental Public Health Platform! To maintain structural integrity and a linear git history, all developers must adhere to the following code quality and commit standards.

## 📋 Conventional Commit Standards

We enforce the **Conventional Commits** specification. Every commit message must match this metadata layout to pass our automation gates:

```text
<type>(<scope>): <short summary in present tense>
```

### Allowed Commit Types
* `feat`: A brand new platform feature or data pipeline module.
* `fix`: A bug fix or corrected layout logic.
* `ci`: Changes to our automation configurations (e.g., GitHub Actions YAML).
* `build`: Changes affecting compilation, Dockerfiles, or Docker Compose structures.
* `docs`: Documentation-only adjustments (e.g., updating this guide or a README).
* `test`: Adding missing tests or correcting existing test suites.
* `chore`: Maintenance, updating dependency locks, or general file housekeeping.

### Allowed Scopes
* `infra`: Core container environments, dev-containers, or networks.
* `backend`: Data ingestion scripts, Prefect flows, or storage adapters.
* `api`: FastAPI route handlers, gateways, or access controllers.
* `frontend`: Marimo dashboards or geospatial analytics viewports.

---

## 🛠️ Local Quality Validation (Pre-Commit Hooks)

Our platform utilizes an automated, zero-duplication linting framework powered by `pre-commit` and bound directly to your local `uv` lockfile environment. 

The hooks run automatically on `git commit`, but you should execute a global pass manually across all code vectors before pushing to the server:

```bash
uv run pre-commit run --all-files
```

### What our validation suite scans for:
1. **Commit Linter**: Re-verifies your message conforms strictly to Conventional Commits.
2. **Ruff Check & Format**: Auto-fixes Python syntax formatting and indentation on the fly.
3. **Mypy Static Typing**: Runs a strict mathematical type-check evaluation over all function definitions.
4. **Hygiene Guards**: Validates configuration integrity for all YAML, TOML, and secret key boundaries.

---

## 🧪 Local Test Suite Configuration

All unit and integration tests are co-located right inside their respective service directories. Before pushing your branch, execute the localized test runner inside your active development container:

```bash
uv run pytest backend/
```
