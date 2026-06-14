# 📡 UK Met Office API Ingestion Core

This module manages the automated ingestion of hourly weather metrics from ground-based sensor instruments across the UK, feeding raw data directly into the platform's Medallion storage layers.

## 🔄 The DataOps Lifecycle

To protect our API limits, minimize network overhead, and maintain zero runtime cost for spatial distance tracking, our workflow decouples spatial station mapping from production execution:

```text
  [ Developer Workspace ]                       [ Production Runner Cluster ]
  Register City (Lat/Long)                                 │
             │                                             ▼
             ▼                                  Load spatial_registry.json
  Query /nearest endpoint                        (Zero-cost Local File Scan)
             │                                             │
             ▼                                             ▼
  Capture Unique Geohash                         Batch-Query /{geohash} Loop
             │                                      (Concurrent aiohttp)
             ▼                                             │
   Commit to Git as Config-as-Code                         ▼
             │                                   Stream to Bronze Lake House
             └─────────────────────────────────────────────┘
```

1. **Credential Provisioning**: A developer registers to access the API on the [Met Office Weather DataHub](https://datahub.metoffice.gov.uk/docs/o/category/observations/type/land-observations/api-documentation#overview) and exports the application keys as environment variables.
    ```text
    MET_OFFICE_CLIENT_SECRET=...  # Required: Your API key/secret
    MET_OFFICE_URL=...            # Optional: Override base URL (e.g., for mock server)
    ```
2. **Spatial Location Registration**: When adding target tracking coordinates for a new urban center, the developer inserts the coordinates into the local orchestration engine.
3. **Static Resolution**: The developer utility script makes a single-shot request to the `/observation-land/1/nearest` API endpoint to find the closest active weather station and its unique `geohash`.
4. **Configuration as Code**: The resolved station meta and timestamp are saved back to disk in `geohash_registry.json`. This acts as a version-controlled, immutable snapshot registry that tracks location mapping historically.
5. **Concurrent Production Ingestion**: Our production pipeline reads the local JSON registry. It loops through only the unique geohashes, executing high-concurrency requests against `/observation-land/1/{geohash}`. This cuts API usage in half and completely avoids unnecessary runtime coordinate lookups.
6. **Medallion Delivery**: The incoming time-series payloads are structured, timestamped in UTC, and written directly into the **Bronze Storage Layer**.

---

## 🔐 Environment Configuration

To connect this platform to the live UK Met Office network, export your application keys as local environment variables, configure these in GitHub as secrets, or save to a .env file locally. For instance:

```bash
export MET_OFFICE_CLIENT_SECRET="your_client_secret_here"
# Optional: Override the base URL (defaults to live Met Office API, usually not required)
export MET_OFFICE_URL="https://data.hub.api.metoffice.gov.uk"
```

---

## 🧪 Testing and Automation Matrix

We separate local developer safety from live network contract verification using a test isolation model:

### 1. Offline Developer Loops (Default)
Standard unit tests validate our data contracts, Pydantic schemas, and processing logic locally without requiring external network connections.
```bash
uv run pytest
```
*   **Result**: `100% Green / Passed` (Safe to run completely offline).
*   **Mock Infrastructures**: Our local environment includes a containerized **FastAPI Mock Server** that mimics the Met Office endpoints. It uses **Polyfactory** to automatically stream contractually valid, randomized JSON data over a local self-signed TLS/SSL connection. This allows you to test end-to-end processing and edge cases (like network timeouts and connection drops) entirely on your local machine.

### 2. Live Contract Drift Integration Tests
A dedicated smoke test suite hits the real Met Office network to verify that our internal code models still match live industry data structures. This proactively alerts us to any upstream API changes.
```bash
uv run pytest -m integration
```
*   **Behavior**: If real credentials are missing locally, this suite will display a clear error message instructing you how to pass variables or bypass them.
*   **CI/CD Guard**: Our GitHub Actions pipelines override the default options during midnight cron checks by injecting repository secrets and forcing `-m integration`. This isolates contract testing away from local developer machines while guaranteeing production safety.
