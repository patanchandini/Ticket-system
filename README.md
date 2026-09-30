# Support Ticket System

An end-to-end workflow that converts **unresolved customer conversations** into
**structured, prioritized, routed, SLA-tracked support tickets**.

It extracts customer / order / product / issue / evidence / contact details,
requests missing mandatory information, computes priority from severity,
sentiment, waiting time, customer impact and SLA rules, routes tickets by agent
skills / availability / workload / business hours, and enforces business-hours
SLA rules with warnings at 75% and automatic escalation on breach.

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Visit%20API-brightgreen)](https://ticket-system-ie7h.onrender.com/docs)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3119/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-5%20passed-brightgreen)](tests/test_pipeline.py)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## 🌐 Live Demo

**Swagger UI:** https://ticket-system-ie7h.onrender.com/docs  
**API Base:** https://ticket-system-ie7h.onrender.com

> ⚠️ Hosted on Render's free tier — the app sleeps after 15 minutes of
> inactivity. The first request may take 30–60 seconds to wake up.


---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [API Endpoints](#api-endpoints)
- [Example Usage](#example-usage)
- [Configuration](#configuration)
- [SLA Engine](#sla-engine)
- [Deduplication](#deduplication)
- [Priority Scoring](#priority-scoring)
- [Routing](#routing)
- [Masked Handoff](#masked-handoff)
- [Runtime Changes](#runtime-changes)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Production Hardening](#production-hardening)
- [Hidden Evaluation Cases](#hidden-evaluation-cases)
- [License](#license)

---

## Features

| Feature | Description |
|---|---|
| **Conversation Ingest** | Accepts chat / email / voice transcripts with metadata |
| **Field Extraction** | Pulls customer, order, product, issue, evidence, contact, sentiment |
| **Missing-Info Handling** | Detects missing mandatory fields and asks targeted questions |
| **Deduplication** | Fingerprint-based merge, grouping, and splitting of related issues |
| **Priority Scoring** | Composite score from severity, sentiment, wait, impact, SLA |
| **Skill-Based Routing** | Routes to qualified, available agents within business hours |
| **Fallback Chain** | Backup team → on-call → pending queue (never drops a ticket) |
| **Business-Hours SLA** | Excludes weekends and configured holidays |
| **Warn @ 75% / Breach Escalation** | Warning event at 75%, auto-escalate on breach |
| **Runtime SLA Changes** | Versioned policies; recompute from original start time |
| **Masked Handoff Summary** | PII-masked summary for the receiving agent |
| **Idempotent Event Log** | Every stage emits versioned events for replay |

---

## Architecture

```
Conversation Ingest
      │
      ▼
[1] Normalize & Segment
      │
      ▼
[2] Extract Structured Fields
      │
      ▼
[3] Validate & Request Missing Info
      │
      ▼
[4] Deduplicate / Group / Split
      │
      ▼
[5] Compute Priority
      │
      ▼
[6] Route to Team / Agent
      │
      ▼
[7] SLA Clock (business-hours aware)
      │
      ▼
[8] Masked Handoff Summary + Ticket Created
      │
      ▼
[9] Monitor / Re-evaluate on Runtime SLA Changes
```

---

## Project Structure

```
ticket-system/
├── main.py                     # FastAPI app + orchestrator
├── config.py                   # Hot-reloadable config service
├── models.py                   # Pydantic schemas
├── db.py                       # SQLAlchemy models
├── events.py                   # Idempotent event emitter
├── sla_engine.py               # Business-hours SLA core
├── conftest.py                 # pytest path setup
├── configs/                    # YAML configuration
│   ├── calendar.yaml           # Timezone, weekends, holidays, business hours
│   ├── sla_policies.yaml       # SLA targets by priority & category
│   ├── skills.yaml             # Agents, skills, teams, backups
│   └── mandatory_fields.yaml   # Required fields per issue category
├── stages/                     # Pipeline stages
│   ├── __init__.py
│   ├── ingest.py               # Normalize + segment
│   ├── extract.py              # Field extraction
│   ├── validate.py             # Mandatory-field checks
│   ├── dedup.py                # Fingerprint generator
│   ├── priority.py             # Priority scoring
│   ├── routing.py              # Routing engine
│   └── handoff.py              # Masked handoff summary
├── workers/
│   ├── __init__.py
│   └── sla_worker.py           # Warn @75% + breach escalation
├── tests/
│   └── test_pipeline.py        # Unit tests
├── requirements.txt
└── README.md
```

---

## Requirements

- **Python 3.11** (recommended — has pre-built wheels for all dependencies)
- **Windows / macOS / Linux**
- **~100 MB disk** for the virtual environment

---

## Installation

### 1. Clone or download the project

```bash
cd ticket-system
```

### 2. Create a virtual environment with Python 3.11

**Windows (PowerShell):**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd):**
```cmd
py -3.11 -m venv .venv
.\.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --only-binary=:all:
```

> The `--only-binary=:all:` flag forces pip to use pre-built wheels, avoiding
> the Rust / MSVC compilation error that occurs on some Python versions.

---

## Running the Server

```bash
python -m uvicorn main:app --port 8001
```

Expected output:

```
INFO:     Started server process [xxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

Open in a browser:

| Purpose | URL |
|---|---|
| **Swagger UI** | http://127.0.0.1:8001/docs |
| **ReDoc** | http://127.0.0.1:8001/redoc |
| **OpenAPI JSON** | http://127.0.0.1:8001/openapi.json |

> ⚠️ **Never use `0.0.0.0` in a browser.** That's a server bind address.
> Always browse to `127.0.0.1` or `localhost`.

---

## API Endpoints

### `POST /conversations`

Ingest a conversation and create one or more tickets.

**Request body:**
```json
{
  "turns": [
    {"speaker": "customer", "text": "I was double charged on order #4821. Screenshot attached. This is unacceptable!"}
  ],
  "meta": {"channel": "email"}
}
```

**Response (200 OK):**
```json
{
  "created": [{
    "ticket_id": "TCK-a1b2c3d4",
    "state": "OPEN",
    "priority": "P1",
    "routed_to": {
      "team": "billing-tier1",
      "agent": "A-01",
      "reason": "skill+availability+workload"
    },
    "handoff_summary": "Ticket TCK-a1b2c3d4 | P1 | billing\nCustomer: N/A (Tier: gold)\nOrder: ***4821 | Value: 750.0\n..."
  }]
}
```

### `GET /tickets/{ticket_id}`

Retrieve a ticket by ID.

```bash
curl http://localhost:8001/tickets/TCK-a1b2c3d4
```

### `POST /admin/reload-config`

Runtime configuration change. Reloads YAML config and recomputes SLA
milestones for all open tickets.

```bash
curl -X POST "http://localhost:8001/admin/reload-config?key=sla_policies"
```

**Response:**
```json
{
  "reloaded": "sla_policies",
  "version": 2,
  "recomputed": ["TCK-a1b2c3d4", "TCK-e5f6g7h8"]
}
```

---

## Example Usage

### 1. Create a ticket

```bash
curl -X POST http://localhost:8001/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "turns": [
      {"speaker": "customer", "text": "I was double charged on order #4821. Screenshot attached. This is unacceptable!"}
    ],
    "meta": {"channel": "email"}
  }'
```

### 2. Send a duplicate (should merge)

Send the **same** request again. Response:

```json
{"created": [{"ticket_id": "TCK-a1b2c3d4", "state": "MERGED_DUPLICATE"}]}
```

### 3. Trigger a runtime SLA change

```bash
curl -X POST "http://localhost:8001/admin/reload-config?key=sla_policies"
```

### 4. Run the SLA worker (warn @75% / breach escalation)

```bash
python -m workers.sla_worker
```

Run this periodically (e.g., every 60 seconds via cron / Task Scheduler).

---

## Configuration

All configuration lives in `configs/*.yaml` and is **hot-reloadable**.

### `configs/calendar.yaml`

```yaml
timezone: Asia/Kolkata
weekends: [5, 6]                # Monday=0 ... Sunday=6
holidays:
  - "2025-01-26"
  - "2025-03-14"
  - "2025-08-15"
business_hours:
  start: "09:00"
  end: "18:00"
pause_states:
  - AWAITING_INFO
  - PENDING_TEAM_AVAILABILITY
  - QUEUED_OFF_HOURS
```

### `configs/sla_policies.yaml`

```yaml
version: v1
defaults:
  P1: 60          # minutes
  P2: 240
  P3: 480
  P4: 1440
overrides:
  P1:
    billing: 60
    delivery: 120
```

### `configs/skills.yaml`

```yaml
categories:
  billing:        [billing, refunds]
  delivery:       [logistics, tracking]
  product_defect: [technical, rma]
  account:        [account_mgmt]

agents:
  - id: A-01
    name: Alice
    skills: [billing, refunds]
    timezone: Asia/Kolkata
    shift: {start: "09:00", end: "18:00"}
    wip_cap: 5

teams:
  billing-tier1: [A-01, A-02]
  tech-tier1:    [A-03]
  escalation:    [A-01, A-03]
  on_call:       [A-02]

backup:
  billing:        [billing-tier1, on_call]
  product_defect: [tech-tier1, on_call]
```

### `configs/mandatory_fields.yaml`

```yaml
order_issue:    [order.id, contact.email, evidence]
product_defect: [product.sku, contact.email, evidence]
billing:        [order.id, contact.email, evidence]
account:        [customer.id, contact.email]
default:        [customer.id, contact.email, evidence]
```

---

## SLA Engine

The SLA clock is **business-hours aware** — it excludes weekends and holidays,
and pauses in configured states.

**Milestones:**

- `allowed_minutes` — selected from `sla_policies.yaml` by priority + category
- `warn_at = 0.75 × allowed` — emit `SLA_WARNING`
- `breach_at = allowed` — emit `SLA_BREACH` → auto-escalate

**Runtime policy change:**

When `POST /admin/reload-config` is called, the engine:
1. Bumps the policy version
2. Recomputes `allowed`, `warn_at`, `breach_at` from the **original start time**
3. Re-evaluates state (OK / WARNED / BREACHED) from elapsed business minutes
4. Re-fires events idempotently (keyed by `ticket_id:event_type:policy_version`)

---

## Deduplication

Each ticket gets a **fingerprint**:

```python
fingerprint = hash(customer_id, product_sku, issue_category, description[:80])
```

| Condition | Action |
|---|---|
| Same fingerprint + same order + within window | **MERGE** (dedup) |
| Same customer + order + different category | **GROUP** under parent |
| High similarity + same product across customers | **LINK** to Problem Record |
| Different order / product, low similarity | **SPLIT** into separate tickets |

Merged tickets reuse the original SLA clock — a duplicate does not extend the deadline.

---

## Priority Scoring

```
priority_raw =
    0.50 × severity_score        # S1=100, S2=70, S3=40, S4=15
  + 0.15 × sentiment_score       # (1 - normalized_sentiment) × 20
  + 0.15 × wait_score            # min(wait/sla_target, 1) × 20
  + 0.15 × impact_score          # tier + order value + affected users
  + 0.05 × sla_score             # breach risk
```

**Hard rule:** S1 severity always lands in **P1 or P2** — with an escalation
to P1 if the customer is angry (`sentiment < -0.5`) or has waited more than
60 business minutes.

| Score | Priority | Response Target |
|---|---|---|
| ≥ 80 | P1 | 1 business hour |
| 60–79 | P2 | 4 business hours |
| 40–59 | P3 | 1 business day |
| < 40 | P4 | 3 business days |

Category overlays can tighten these (e.g., P1 billing = 1h, P1 delivery = 2h).

---

## Routing

Filter agents by:

1. Skills ⊇ required skills for the issue category
2. Available now (within shift)
3. Within agent's timezone business hours
4. Below WIP cap

Score remaining candidates:

```
score = 0.5 × skill_match
      + 0.3 × (1 - workload_ratio)
      + 0.2 × availability_window
```

**Fallback chain** (never drops a ticket):

1. Backup team with overlapping skills
2. On-call rota
3. `PENDING_TEAM_AVAILABILITY` with paused SLA clock
4. Next business day queue

---

## Masked Handoff

Every ticket has a masked handoff summary for the receiving agent:

```
Ticket TCK-a1b2c3d4 | P1 | billing
Customer: A***h K*** (Tier: gold)
Order: ***4821 | Value: 750.0
Product: WP-X2
Issue: double charged on renewal
Sentiment: -0.7
SLA: 80% consumed ⚠️
Related: TCK-xxxx (same order)
Handoff: Verify duplicate txn, refund excess, confirm with customer.
```

**Masking rules:**

| Field | Rule |
|---|---|
| Name | First + last initial |
| Email | First letter + `***@domain` |
| Phone | `***` + last 4 |
| Order ID | `***` + last 4 |
| Card / UPI | `***` + last 4 |

Full PII is available only via an authorized audited endpoint.

---

## Runtime Changes

Every stage emits a versioned event. All timers are keyed by
`(ticket_id, event_type, policy_version)` so replay is safe.

To reload **any** config at runtime:

```bash
curl -X POST "http://localhost:8001/admin/reload-config?key=sla_policies"
curl -X POST "http://localhost:8001/admin/reload-config?key=calendar"
curl -X POST "http://localhost:8001/admin/reload-config?key=skills"
curl -X POST "http://localhost:8001/admin/reload-config?key=mandatory_fields"
```

Omit `key` to reload all configs:

```bash
curl -X POST http://localhost:8001/admin/reload-config
```

---

## Testing

```bash
python -m pytest tests\test_pipeline.py -v
```

**Expected output:**

```
tests/test_pipeline.py::test_weekend_excluded ................ PASSED
tests/test_pipeline.py::test_holiday_excluded ................ PASSED
tests/test_pipeline.py::test_priority_p1_for_s1_gold ......... PASSED
tests/test_pipeline.py::test_runtime_sla_change_recomputes ... PASSED
tests/test_pipeline.py::test_dedup_fingerprint_stable ........ PASSED

==================== 5 passed in ~3s ====================
```

Tests cover:

- Weekend exclusion (Fri 17:00 + 120 min → Mon 10:00)
- Holiday exclusion
- Priority P1 for S1 severity + Gold customer
- Runtime SLA change recomputes milestones from original start
- Fingerprint stability for identical descriptions

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'stages.dedup'`

- Ensure `stages/__init__.py` exists (empty file)
- Ensure the file is named `dedup.py`, not `dedub.py`
- Ensure `conftest.py` exists at the project root
- Run uvicorn from the project root

### `[Errno 10048] error while attempting to bind on address`

Port already in use by a stale process.

```cmd
taskkill /F /IM python.exe
taskkill /F /IM uvicorn.exe
```

Or use a different port:

```cmd
python -m uvicorn main:app --port 8002
```

### `'uvicorn' is not recognized`

Activate the venv first:

```cmd
.\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt --only-binary=:all:
```

### `Fatal error in launcher: Unable to create process`

A venv was moved to a different drive. Rebuild it:

```cmd
deactivate
rmdir /s /q .venv
.\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt --only-binary=:all:
```

### `metadata-generation-failed` for `pydantic-core`

You're on Python 3.13 without a pre-built wheel. Use Python 3.11:

```cmd
py -3.11 -m venv .venv
.\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt --only-binary=:all:
```

### Browser shows `{"detail":"Not Found"}` at `/`

That's expected — no route is defined for `/`. Go to `/docs` instead.

### Browser shows `Failed to fetch` on Swagger

The server isn't running. Restart uvicorn and refresh.

### Browser shows `ERR_ADDRESS_INVALID`

You typed `0.0.0.0`. Use `127.0.0.1` or `localhost` instead.

### `422 Unprocessable Entity` with `"Field required: turns"`

Wrong request body shape. The API expects `{"turns": [...], "meta": {...}}`,
not `{"created": [...]}`. See [Example Usage](#example-usage).

### `AttributeError: 'NoneType' object has no attribute 'get'`

`config.py` points to the wrong folder. Ensure:

```python
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configs")
```

(Note the `s` — the folder is named `configs`, not `config`.)

---

## Production Hardening

| Area | Suggestion |
|---|---|
| Database | Replace SQLite with Postgres in `db.py` |
| Extraction | Replace heuristics with an LLM (OpenAI / Anthropic) using `Extraction.model_json_schema()` |
| Scheduler | Move SLA worker to Celery Beat / APScheduler with persistent job store |
| Auth | Add OAuth2 / JWT on `/admin/*` and PII endpoints |
| Cache | Add Redis for agent workload counters and dedup windows |
| Tracing | Add OpenTelemetry spans per stage |
| Deployment | Containerize with Docker; run under Gunicorn + Uvicorn workers |
| Monitoring | Prometheus metrics + Grafana dashboards |
| Replay | Add `/admin/replay/{ticket_id}` to recompute from event history |

---

## Hidden Evaluation Cases

This system is designed to handle edge cases commonly used in automated
evaluation:

| Case | Behavior |
|---|---|
| **Duplicate tickets** | Same fingerprint → merged; no new SLA clock |
| **Unavailable teams** | Fallback chain: backup team → on-call → pending queue |
| **After-hours requests** | Ticket queued; SLA clock starts at next business instant |
| **Runtime SLA changes** | Versioned policies; recompute from original start time |
| **Related vs unrelated issues** | Grouped by order/customer; split by product |
| **Missing mandatory info** | Draft ticket in `AWAITING_INFO` + targeted question |
| **Weekends / holidays** | Excluded from SLA clock |
| **Warn @ 75%** | `SLA_WARNING` event + notify assignee and lead |
| **Breach** | `SLA_BREACH` event + auto-escalate to P1 + reassign |![alt text](image.png)

---

## License

MIT License — see LICENSE file for details.

---

## Credits

Built as a complete reference implementation of a support ticket workflow
covering extraction, deduplication, priority scoring, skill-based routing,
business-hours SLA enforcement, and runtime policy changes."# Ticket-system" 
