# Quorom

Autonomous AWS cost + reliability agent. Detects idle/oversized EC2 and Lambda resources,
reasons about the right fix via an LLM, and executes remediations only after human approval,
with a full audit trail and rollback path.

See [`docs/PLANNING.md`](docs/PLANNING.md) for full scope, architecture, and safety design.

## Pipeline

```
Detect → Reason → Propose → Approve → Act → Verify → Report
```

**Day 1 (this branch):** Detect + Reason - read-only findings dashboard. No AWS writes.

## Stack

FastAPI · boto3 · Claude API · React/Vite · SQLite (Postgres-ready) · Docker Compose

## Quick start (mock mode - no AWS/Claude keys needed)

```bash
# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 - seeded findings with agent reasoning appear automatically.

### Live mode

Set in `.env`:

```
QUOROM_MODE=live
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
ANTHROPIC_API_KEY=...
```

Only resources tagged `quorom:managed=true` are ever queried (enforced in the cloud layer).

### Docker Compose

```bash
docker compose up --build
```

## Safety (v1)

- Hard tag filter: `quorom:managed=true` at the query layer
- LLM never gets AWS credentials - structured JSON actions only
- Dry-run default; live execute is Day 2+
- Day 1 is **read-only** - no boto3 write calls in the codebase

## Project layout

```
backend/app/
  agents/   # Claude reasoning → validated structured actions
  cloud/    # boto3 read-only connector + metrics
  core/     # rule-based detection + scan pipeline
  api/      # FastAPI routes
  models/   # SQLAlchemy + Pydantic schemas
frontend/   # React dashboard (findings cards)
docs/       # Planning + agent prompts
infra/      # Sandbox IAM policies + Terraform (Day 2+)
```

## v2 roadmap (not built yet)

Multi-cloud · RDS/S3 · auto-rollback · Slack/PagerDuty approvals
