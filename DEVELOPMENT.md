# Regulus — Development Guide

## Prerequisites

- Python 3.12+
- Node.js 20+
- Git

Google Cloud credentials are **not required** for local development. The backend runs entirely in mock mode.

---

## Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env if needed — defaults work for local dev

# Start the server
uvicorn app.main:app --reload --port 8000
```

The server starts at `http://localhost:8000`.

API docs available at `http://localhost:8000/docs` (development only).

### Default local dev behavior

With the default `.env.example` settings:

| Feature | Local behavior |
|---|---|
| Firestore | In-memory (no GCP needed) |
| Pub/Sub | asyncio.Queue (in-process, no GCP needed) |
| Gemini | Mock responses (no API key needed) |
| Research data | Synthetic Maji Valley dataset |

To use real Gemini, set `GOOGLE_APPLICATION_CREDENTIALS` and a valid `GEMINI_MODEL`.

---

## Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Start dev server
npm run dev
```

The app runs at `http://localhost:3000`.

---

## Running tests

### Backend

```bash
cd backend
source .venv/bin/activate

# All tests
PYTHONPATH=. python -m pytest tests/ -v

# PGM engine only
PYTHONPATH=. python -m pytest tests/test_pgm.py -v

# Integration test only
PYTHONPATH=. python -m pytest tests/test_integration.py -v

# With coverage
PYTHONPATH=. python -m pytest tests/ --cov=app --cov-report=term-missing
```

Expected: **33 tests, all passing** in ~1.5 seconds.

### Frontend

```bash
cd frontend
npm run build   # TypeScript check + production build
```

---

## Project structure

```
regulus/
├── backend/
│   ├── app/
│   │   ├── main.py               FastAPI app, lifespan, CORS
│   │   ├── config.py             Settings from environment
│   │   ├── api/routes/           Thin route handlers
│   │   ├── agents/               Four agent classes + prompts
│   │   ├── domain/               Pydantic models, state machine
│   │   ├── pgm/                  Graph, simulation, sensitivity
│   │   ├── infrastructure/       Firestore, Pub/Sub, Gemini, logging
│   │   └── workers/              Background job processor
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── app/                      Next.js App Router pages
│   ├── components/               Reusable UI components
│   ├── hooks/                    TanStack Query hooks
│   ├── lib/                      API client, types, utils
│   └── .env.local.example
│
├── demo_water_scenario.json       Demo scenario parameters
├── README.md
├── ARCHITECTURE.md
├── AGENTS.md
├── PGM.md
├── DEVELOPMENT.md
├── DEMO.md
├── VERCEL_DEPLOYMENT.md
└── CLOUD_RUN_DEPLOYMENT.md
```

---

## Environment variables reference

### Backend

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development`, `staging`, `production` |
| `GEMINI_MODEL` | `gemini-2.0-flash-exp` | Gemini model identifier |
| `GOOGLE_CLOUD_PROJECT` | `regulus-demo` | GCP project ID |
| `FIRESTORE_DATABASE` | `(default)` | Firestore database name |
| `PUBSUB_TOPIC` | `regulus-runs` | Pub/Sub topic name |
| `PUBSUB_SUBSCRIPTION` | `regulus-runs-sub` | Pub/Sub subscription name |
| `ALLOWED_ORIGIN` | `http://localhost:3000` | CORS allowed origin |
| `SIMULATION_COUNT` | `500` | Monte Carlo sample count |
| `MAX_RESEARCH_LOOPS` | `3` | Max autonomous research loops |
| `USE_MOCK_RESEARCH` | `true` | Use synthetic demo data |
| `USE_MOCK_FIRESTORE` | `false` | Use in-memory Firestore |
| `USE_MOCK_PUBSUB` | `false` | Use in-process queue |
| `LOG_LEVEL` | `INFO` | Logging level |

### Frontend

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL (e.g. `https://your-service.run.app`) |

---

## Making changes

### Adding a new intervention

1. Add the new type to `InterventionType` enum in `backend/app/domain/models.py`
2. Add node overrides in `backend/app/pgm/water_model.py` for affected nodes
3. Add the intervention config in `SimulationAgent.build_scenarios()` in `backend/app/agents/simulation/agent.py`
4. Add the UI option in `frontend/app/app/new/page.tsx` INTERVENTIONS array

### Changing the PGM structure

1. Edit `backend/app/pgm/water_model.py` — add/remove nodes and edges
2. Update `NODE_POSITIONS` in `frontend/components/model/PGMGraph.tsx` for layout
3. Update the node count assertion in `tests/test_pgm.py`

### Adjusting materiality threshold

In `backend/app/agents/orchestrator/agent.py`:
```python
MATERIALITY_THRESHOLD = 0.35  # Change this value
```

Or pass `materiality_threshold` to `run_sensitivity_analysis()` directly.
