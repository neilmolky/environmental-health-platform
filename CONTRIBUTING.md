## 💻 Local Development Environment

The easiest way to begin development is to make use of the optimized multi-container development environment defined in `.devcontainer/devcontainer.json`, This environment can be set up to provide developer tools consistent with the ci checks including:
* pre-commit-hooks that run linting, type checking and reject commit messages so your commits don't fail in ci.
* vscode settings for syntax highlighting and linting that will be consistent with ci.
* cloud storage emulation for local, end to end integration checks for your cloud provider of choice

To set up the dev environment, your local host machine must satisfy the following system requirements:

1. **Docker Engine**: Docker must be installed and running on your host machine.
2. **VS Code**: Install the from Microsoft. 
3. **VS Code Extensions**: Ensure you have the official **Dev Containers** extension installed on your host machine.

### Launching the Workspace

Once your host machine matches the steps above:
1. Clone this repository
2. Open the directory in your IDE
3. Press `F1` or `Ctrl+Shift+P` and choose **Dev Containers: Reopen in Container**.
4. You should be able to begin development immediately. All the infrastructure, dependencies, tool integrations will be available. 
5. To view the services: Look at the "Ports" tab at the bottom of VS Code to see all running services and click the globe icon to open them in your browser. The dev container reloads your code changes through the uvicorn server. 

---

# Tools

This project was built with an oppinion on tools. The choices reflect the following preferences. 
- **Learning experimental tools**: Tools like ty and marimo are novel and perhaps unconventional choices that users might be less familiar with. A project like this is meant to be somewhere you can experiment and play with tools that interest you.
- **Cloud agnostic and accessible**: Modern data engineering is in the cloud, and sadly fear arround the costs can feel like a barrier to learning and developing important skills. However, cloud is just infrastructure, a platform, or a service that, by design, we connect to exclusively via a network. In theory, we can emulate this in containers and in doing so, learn the essential concepts that transcend individual providers.
- **Limited developer friction**: All the times I've got angry because a mistake I could have avoided got picked up 30 minutes into a build. All the times I've had to fix a problem after deployment. All the times I've been reactive rather than proactive. This project is for you. From the earliest stages of design I've aimed to make the development experience frictionless. I want to set and maintain quality standards without having to remember what they are. I want to enable these standards to grow and evolve with the project. 

---

# Contributing Guidelines

Thank you for contributing to the Environmental Public Health Platform! The following code quality and commit standards are enforced at CI. pre-commit checks ensure no commit can be made if it doesn't pass code linting standards. Pull requests to `main` will check container's successfully build, tests successfully run, test coverage is beyond the set threshold, and security vulnerabilities are patched.

## Commands run in CI
The following commands which run in CI can be run locally to validate your build before each commit.

uv sync                            # ensure dependencies are up to date
uv run pre-commit run --all-files  # runs ruff, ty and other linting tools
uv run pytest -m 'not integration' # 
uv run pytest                      # run the full suite of tests, mocks are not run in ci
```

## 📋 Conventional Commit Standards

We enforce the **Conventional Commits** specification. Every commit message must match this metadata layout:

```text
<type>(<optional scope>): <message>
```
eg:
```
build: add gcp emulation to docker-compose
```
```
feat(backend): add pipeline for air quality
```

### Allowed Commit Types
* `build`: Changes affecting compilation, Dockerfiles, or Docker Compose structures.
* `chore`: Maintenance, updating dependency locks, or general file housekeeping.
* `ci`: Changes to our automation configurations (e.g., GitHub Actions YAML).
* `docs`: Documentation-only adjustments (e.g., updating this guide or a README).
* `feat`: A brand new platform feature or data pipeline module.
* `fix`: A bug fix or corrected layout logic.
* `perf`: A code change that improves performance.
* `refactor`: A code change that neither fixes a bug nor adds a feature.
* `revert`: Remove a change in order to unblock future development
* `style`: Changes that do not affect the meaning of the code (white-space, formatting, etc).
* `test`: Adding missing tests or correcting existing test suites.

### Allowed Scopes
* `backend`: Data ingestion scripts, Prefect flows, or storage adapters.
* `api`: FastAPI route handlers, gateways, or access controllers.
* `frontend`: Marimo dashboards or geospatial analytics viewports.

---

## 🛠️ Local Quality Validation (Pre-Commit Hooks)

Our platform uses the pre-commit package to provide linting that is applied prior to every commit. Commits that fail linting will be rejected and often fixed automatically. If a commit fails the linter may make changes to the code. Stage these changes and try again.  

The hooks run automatically on `git commit`, but can be manually anytime.

```bash
uv run pre-commit run --all-files
```

### What our validation suite scans for:
1. **Commit Linter**: verifies your message conforms to Conventional Commits.
2. **Ruff Check & Format**: Auto-fixes Python syntax formatting and indentation on the fly.
3. **Ty Static Typing**: Runs a type-check evaluation over all function definitions.
4. **Hygiene Guards**: Validates configuration integrity for all YAML, TOML, and secret key boundaries.

---

## 🧪 Local Test Suite Configuration

All unit and integration tests are co-located right inside their respective service directories. Before pushing your branch, execute the localized test runner inside your active development container:

```bash
uv run pytest backend/
```
