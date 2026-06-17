# FinAlly E2E Test Infrastructure

This directory holds the end-to-end (E2E) test infrastructure: the Playwright
suite plus the deterministic app harness it runs against.

## Playwright suite (authoritative E2E runner)

The suite is **self-contained** — it boots the backend itself via a managed
`webServer`, so you only need Node + `uv`:

```bash
cd test
npm install
npx playwright install chromium
npx playwright test            # boots backend (LLM_MOCK, simulator, throwaway DB) and runs chromium
npx playwright show-report     # open the HTML report
```

- `playwright.config.ts` — chromium project, `baseURL` http://127.0.0.1:8000,
  and a `webServer` that runs `scripts/start-backend.mjs`.
- `scripts/start-backend.mjs` — launches `uv run uvicorn app.main:app` from
  `../backend` with `LLM_MOCK=true`, `MASSIVE_API_KEY=""`,
  `STATIC_DIR=../frontend/out`, and a fresh `FINALLY_DB_PATH` in a temp dir
  (so the real DB is never touched and every run starts from the seeded
  $10,000 / 10-ticker state). Requires `frontend/out` to exist
  (`cd ../frontend && npm run build`).
- Specs in `e2e/` cover PLAN §12: fresh start, watchlist add/remove, buy/sell,
  portfolio visualization (heatmap + P&L chart), AI chat (mocked), and SSE
  resilience.

### Run against an already-running server (e.g. the Docker container)

```bash
# From repo root: docker run -d -p 8001:8000 -e LLM_MOCK=true finally:e2e
cd test
E2E_NO_SERVER=1 E2E_BASE_URL=http://127.0.0.1:8001 npx playwright test
```

`E2E_NO_SERVER=1` skips the managed backend; `E2E_BASE_URL` points the suite at
any host. On Windows PowerShell set them with `$env:E2E_NO_SERVER="1"` etc.

## Compose harness (Docker-based alternative)

The remainder of this document describes the **compose harness** that brings the
app up in a deterministic mode for tests.

## What `docker-compose.test.yml` does

- Builds the production image from the repo-root `Dockerfile`.
- Runs the app on **port 8000** with:
  - `LLM_MOCK=true` — deterministic, canned LLM responses (no OpenRouter calls).
  - `MASSIVE_API_KEY=""` — uses the built-in market **simulator** (no external API).
  - an **ephemeral SQLite DB** (tmpfs) so every run starts fresh and lazily seeds.
- Exposes a **healthcheck** hitting `GET /api/health`, so runners can wait until
  the app is actually ready before starting tests.

## Bring the app up for tests

```bash
# From the repo root:
docker compose -f test/docker-compose.test.yml up --build -d

# Wait until healthy (the healthcheck targets /api/health):
docker inspect --format '{{.State.Health.Status}}' finally-test
```

The app is then reachable at **http://localhost:8000** from the host.

## Run Playwright

### Option A — Playwright on the host (simplest)

```bash
# In your Playwright project, point the base URL at the running container:
BASE_URL=http://localhost:8000 npx playwright test
```

### Option B — Playwright in a container (no host browser deps)

A `playwright` service is defined under the `e2e` profile. It waits for the app
to be healthy, then targets `http://app:8000` on the compose network. Mount your
test project into it and override the `command` to run the suite:

```yaml
# Example override (e.g. test/docker-compose.e2e.override.yml):
services:
  playwright:
    volumes:
      - ./e2e:/e2e
    working_dir: /e2e
    command: ["sh", "-c", "npm ci && npx playwright test"]
```

```bash
docker compose -f test/docker-compose.test.yml --profile e2e up --build \
  --abort-on-container-exit
```

The runner reads `BASE_URL=http://app:8000` from the environment.

## Tear down

```bash
# Stop and remove containers + the ephemeral test volumes:
docker compose -f test/docker-compose.test.yml down -v
```

## Notes / contract

- The harness assumes the backend exposes `GET /api/health` returning HTTP 200
  once ready (PLAN §8) and serves on port 8000.
- The `8000:8000` host port mapping means the production container (started via
  `scripts/start_*`) must be stopped first to avoid a port clash.
