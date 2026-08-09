# Cursor Agent Prompt - Quorom, Day 1

Paste this into Cursor's agent/composer to kick off Day 1.

---

You are building **Quorom**, an autonomous AWS cost + reliability agent. Read `docs/PLANNING.md` in this repo first - it defines the full scope, safety design, and pipeline. Follow it exactly; do not expand scope beyond what it specifies (AWS only, EC2 + Lambda only, rightsizing + idle-kill only).

## Today's goal: Detect + Reason (read-only, no execution)

Build the following, in this order, committing after each working piece (target ~15-20 commits):

1. **Project scaffold**
   - FastAPI backend in `backend/app/` with the structure: `agents/`, `cloud/`, `api/`, `core/`, `models/`
   - React/Vite frontend in `frontend/`
   - Docker Compose for local dev (Postgres or SQLite, backend, frontend)
   - `.env.example` with placeholders for AWS credentials and Claude API key - never commit real credentials

2. **AWS sandbox connector (`backend/app/cloud/`)**
   - boto3 client wrapper that ONLY queries resources tagged `quorom:managed=true`
   - Function to list tagged EC2 instances + Lambda functions
   - Function to pull CloudWatch metrics for each (CPU utilization for EC2, invocation count + duration for Lambda) over a configurable lookback window
   - This layer is read-only in Day 1 - no write/execute calls at all

3. **Detection logic (`backend/app/core/`)**
   - Simple rule-based flagging first (idle = avg CPU < X% over N days; oversized = provisioned capacity significantly exceeds peak usage) - deterministic, not LLM-based. The LLM's job is reasoning about *what to do*, not detecting the raw signal.
   - Output a structured `Finding` model: resource_id, resource_type, metric_summary, flag_type, confidence

4. **Reasoning agent (`backend/app/agents/`)**
   - Takes a `Finding` + metrics + resource metadata, calls Claude API
   - Prompt the LLM to return **structured JSON only** (no prose) with: explanation, severity/risk level, proposed_action (enum: `resize_ec2`, `stop_idle_ec2`, `no_action`), proposed_params, confidence
   - Validate the LLM's JSON output against a Pydantic schema before storing it - reject and retry once if malformed
   - Store findings + reasoning output in the database

5. **Findings API + dashboard (read-only)**
   - `GET /findings` endpoint returning all findings with their reasoning
   - React dashboard listing findings as cards: resource, metric summary, the agent's explanation, proposed action, confidence - no approve/act buttons yet, that's Day 2

## Constraints
- No execution code today - this is detect + reason only, enforced literally (no boto3 write calls anywhere in the codebase yet)
- Use the sandbox tag filter (`quorom:managed=true`) everywhere resources are queried - hardcode this filter at the query layer, not just as a suggestion
- Keep the LLM's output schema strict and validated - this matters for Day 2 when it starts driving real actions
- Write a short README section per major piece as you go

## Definition of done for today
Running the app locally shows a dashboard of real (or seeded mock) AWS findings with LLM-generated explanations and proposed actions, entirely read-only.
