# Quorom - Planning Doc (v1)

## One-line pitch
An autonomous cloud reliability + cost agent that detects waste and risk on real AWS infrastructure, reasons about the right fix with an LLM, and (only after human approval) executes the remediation via Terraform, with full audit trail and rollback.

## Why this scope (v1 lock)
Multi-cloud, five resource types, and five action categories sounds impressive on paper but guarantees an unfinished demo. v1 is deliberately narrow so the pipeline is airtight end-to-end:

- **Cloud:** AWS only
- **Resource types:** EC2 instances + Lambda functions only
- **Action categories:** rightsizing (downsize an oversized/idle EC2 instance) + idle-kill (stop/terminate confirmed-idle resources)
- **Account:** a dedicated sandbox AWS account/resource group, hard-tagged, with a hard dollar cap and IAM permissions scoped ONLY to that tag

Everything else (RDS, S3, multi-cloud, security-posture fixes) is a clearly labeled "v2 roadmap" item - good to mention in an interview, bad to half-build for a demo.

## Pipeline (the actual product)
```
Detect → Reason → Propose → Approve → Act → Verify → Report
```

1. **Detect** - a scheduled scanner pulls CloudWatch metrics (CPU, memory proxy, invocation count) for tagged EC2/Lambda resources and flags candidates: idle >N days, oversized relative to utilization, etc.
2. **Reason** - flagged resource + metrics + cost data get sent to the LLM agent, which produces a structured finding: what's wrong, why, confidence, exploitability-equivalent ("blast radius" if fixed wrongly), and a proposed action.
3. **Propose** - finding renders in the dashboard as a card: current state, proposed state, estimated savings, risk level. Nothing executes yet.
4. **Approve** - human clicks approve/reject. Reject requires a reason (fed back as context so the agent doesn't re-propose the same bad idea).
5. **Act** - approved action executes through a thin Terraform/boto3 execution layer, never directly from LLM output. The LLM proposes a structured action (enum + params), a deterministic executor turns that into the actual API/Terraform call. LLM never gets raw AWS credentials or arbitrary code execution.
6. **Verify** - post-action check confirms the resource is in the expected state and nothing else broke (e.g. Lambda still returns 200 on a smoke invoke).
7. **Report** - every action, approval, rejection, and verification result is logged immutably (append-only table) and exportable as a Markdown/PDF report - this is your "audit trail" story for interviews.

## Safety design (this is the part that makes it a strong project, not a liability)
- Hard-coded resource tag filter (`quorom:managed=true`) - the agent can only ever see/act on tagged resources, enforced at the IAM policy level, not just application logic
- Dollar-cap circuit breaker: if projected cumulative action cost/impact in a session exceeds a threshold, agent auto-pauses and requires explicit override
- Dry-run mode is the default; live-execute is an explicit toggle
- LLM never has direct AWS credentials or shell access - it emits a structured JSON action, a separate deterministic layer validates it against an allowlist of action types before executing
- Every execution is a Terraform plan/apply (or boto3 call) wrapped in a rollback-capable transaction where possible (e.g. snapshot before resize)

## Stack
- **Backend:** FastAPI, boto3, Terraform (subprocess or python-terraform), Claude API for the reasoning agent
- **Frontend:** React/Vite, Recharts for cost/util visualization
- **Infra:** local Terraform against a sandboxed AWS account/IAM role; Docker Compose for local dev
- **Data:** Postgres (or SQLite for v1 simplicity) for findings, approvals, audit log

## Milestones (suggested 3-day sprint)
- **Day 1:** Detect + Reason - CloudWatch ingestion, LLM finding generation, findings dashboard (read-only, no execution yet)
- **Day 2:** Propose + Approve + Act - approval UI, structured action schema, Terraform/boto3 executor, dry-run mode working end-to-end
- **Day 3:** Verify + Report + safety hardening - post-action verification, audit log, PDF/Markdown export, dollar-cap circuit breaker, live-execute toggle, demo polish

## Demo script (what you actually show in an interview)
1. Show a resource flagged as idle/oversized with the agent's reasoning
2. Approve one action → watch it execute live in dry-run, then toggle to a real sandbox execution
3. **Reject one action on purpose** and show the agent respecting that and not re-proposing it - this is the moment that proves it's not a YOLO script
4. Pull up the audit report showing every decision made in the session

## v2 roadmap (mention, don't build)
- Multi-cloud (GCP/Azure)
- RDS + S3 cost/security findings
- Auto-rollback on failed verification
- Slack/PagerDuty integration for approval requests
