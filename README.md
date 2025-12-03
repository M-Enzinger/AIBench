# AIBench Experiment Platform

A monorepo that bundles a FastAPI backend, React dashboard, and PostgreSQL database for running LLM-driven experiments alongside human baselines. The stack is fully Dockerized so you can launch everything with a single command and access the UI at `http://<server-ip>:2222`.

## Quick start

1. Copy the environment template and update values as needed:

   ```bash
   cp .env.example .env
   ```

2. Start the stack:

   ```bash
   docker compose up -d
   ```

3. Open `http://<server-ip>:2222` in your browser. The default API docs are at `http://<server-ip>:8000/docs`.

No authentication is required; the dashboard is immediately usable after the stack is running.

## Architecture

- **backend/** – FastAPI service implementing scenario management, experiment orchestration, and storage of stubbed run records to illustrate bulk execution.
- **frontend/** – Vite + React dashboard for configuring scenarios/experiments and browsing run outputs.
- **PostgreSQL** – Provided via Docker Compose with a persistent volume.

The frontend talks to the backend through `VITE_API_URL` (defaults to the internal compose hostname). Both services are exposed via Docker so the full app is reachable at port 2222.

## Environment variables

See `.env.example` for all required variables:

- App: `APP_ENV`, `APP_PORT`
- Database: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- LLM providers: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROK_API_KEY`

## Development notes

- Backend auto-creates database tables on startup; no manual migrations are required.
- The example experiment endpoint seeds placeholder runs to demonstrate how AI and human sources are tracked. Extend the run creation logic to call real model APIs and compute scenario-defined metrics.
- CORS is permissive by default to simplify local testing.
