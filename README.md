<div align="center">

# PrepSense

**A multi-tenant AI preparation platform — one architecture, two products.**

Grounded question generation, free-text grading, and per-topic progress reports for
both **exam prep** (schools) and **interview prep** (companies, institutes, and solo
candidates).

![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.15-A30000)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white)
![Tests](https://img.shields.io/badge/tests-90%20passing-2E7D32)
![Status](https://img.shields.io/badge/status-complete%20%26%20running-2E7D32)

</div>

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Accounts & demo data](#accounts--demo-data)
- [API](#api)
- [Multi-tenancy](#multi-tenancy)
- [Project layout](#project-layout)
- [Testing](#testing)
- [Operational notes](#operational-notes)
- [Roadmap](#roadmap)

---

## Overview

PrepSense runs two products on a single, uniform architecture:

| Product           | Tenant is a…                          | Flow                                                                 |
| ----------------- | ------------------------------------- | ------------------------------------------------------------------- |
| **Exam prep**     | school                                | Teachers/parents upload chapters or PDFs → the system generates grounded questions, grades free-text answers, and reports a per-topic confidence picture to parents and teachers. |
| **Interview prep**| company, institute, or solo candidate | A candidate practises for a role → the system generates behavioural/technical questions from a job description or role + skills, grades answers, tracks improvement, and lets a mentor review history. |

Both are the **same loop** over different source material:

```
SOURCE MATERIAL → GENERATE GROUNDED QUESTIONS → LEARNER ANSWERS
    → GRADE AGAINST RUBRIC → TRACK PROGRESS PER TOPIC
    → OBSERVER (parent/teacher | mentor) VIEWS REPORT
```

> **Status — complete and running.** Tenant isolation, JWT auth with per-tenant RBAC,
> ingestion, grounded generation (Gemini / Anthropic / offline fake), grading, marks
> & progress reports, and a React frontend are all built and covered by 90 passing
> tests.
>
> The Django project module, database user, and frontend package are named
> `prepcheck` internally — the product's original codename.

---

## Features

- **Multi-tenant by construction** — every tenant-owned row is isolated automatically;
  a developer writing an ordinary view gets correct scoping for free.
- **Grounded generation** — questions are derived **only** from the selected
  material's own chunks; a Python paper never yields a Java question.
- **Free-text grading** — answers scored 0–100 against a source-derived rubric that
  stays hidden from the learner.
- **Per-topic progress** — strong / weak / untested breakdown with trend, surfaced to
  the right observer (parent, teacher, or mentor).
- **Provider-agnostic AI** — Google Gemini, Anthropic Claude, or a deterministic
  offline fake, selected by env var; **no API key required to run**.
- **Role-aware React SPA** — superadmin onboarding, org-admin user management, upload
  → generate → practice → dashboard.
- **Per-tenant cost controls** — daily/monthly LLM call caps enforced by throttle.
- **Production-ready ops** — Docker Compose stack, structured logging, health probe,
  OpenAPI docs, and clean deploy checks.

---

## Architecture

```
┌────────────┐   JWT (tenant_id claim)   ┌──────────────────────────────────────┐
│  React SPA │ ────────────────────────▶ │  Django REST Framework  (web)         │
│  (Vite)    │ ◀──────────────────────── │  ├─ tenant middleware → ContextVar     │
└────────────┘   {status,message,data}   │  ├─ TenantScoped ORM (auto-filter)     │
                                          │  └─ envelope responses                 │
                                          └───────┬───────────────────┬──────────┘
                                                  │                   │
                                       ┌──────────▼─────┐    ┌────────▼─────────┐
                                       │ PostgreSQL      │    │ Celery worker    │
                                       │ + pgvector      │    │ (ingest, embed,  │
                                       │ (tenant rows,   │    │  generate, grade)│
                                       │  embeddings)    │    │  ── Redis broker │
                                       └─────────────────┘    └────────┬─────────┘
                                                                       │
                                                          ┌────────────▼───────────┐
                                                          │ LLM / embedding provider│
                                                          │ Gemini │ Claude │ fake  │
                                                          └────────────────────────┘
```

---

## Tech stack

| Concern          | Choice                                                                     |
| ---------------- | -------------------------------------------------------------------------- |
| Backend          | Django 5.1 + Django REST Framework                                         |
| Auth             | `djangorestframework-simplejwt` (JWT with a `tenant_id` claim)            |
| Database         | PostgreSQL + `pgvector` in Docker; SQLite by default for local dev        |
| LLM              | Google Gemini / Anthropic Claude / offline fake — provider & model via env|
| Embeddings       | Voyage / offline deterministic fake (dedup & grounding work offline)      |
| Background tasks | Celery + Redis (ingestion, embedding, grading off the request cycle)      |
| API docs         | drf-spectacular (OpenAPI) + Swagger UI at `/api/docs/`                    |
| Frontend         | React 18 + Vite + Tailwind                                                 |
| Tests            | pytest-django (90 tests, offline fakes — no external services needed)     |
| Containerisation | Docker Compose (web, worker, postgres, redis, frontend)                   |

---

## Getting started

### Prerequisites

- **Docker** (for the full stack), **or** Python 3.12+ and Node 18+ for local dev.


### Option — Local backend (SQLite, no Redis/Postgres)

```bash
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo                # schools + company + institute, ready to explore
python manage.py runserver                # http://localhost:8000
```

```bash
# frontend — separate terminal
cd frontend
npm install
npm run dev                               # http://localhost:5173 (proxies /api to :8000)
```

Everything works **offline out of the box** — the fake LLM/embedding providers need
no API key. For a demo without Redis, set `CELERY_TASK_ALWAYS_EAGER=True` and
`CELERY_RESULT_BACKEND=cache+memory://` so ingestion/generation/grading run inline.

> A `Makefile` wraps the common commands — run `make help` to list targets
> (`make run`, `make migrate`, `make seed`, `make test`, `make up`, …).

---

## Configuration

All settings are read from `backend/.env` via `django-environ` — see
[`backend/.env.example`](backend/.env.example). To generate **real, grounded**
questions instead of the offline fake, set one provider:

```bash
# Google Gemini (free tier: https://aistudio.google.com)
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...your-key
GEMINI_MODEL=gemini-2.5-flash

# ...or Anthropic Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
```

Set `EMBEDDING_PROVIDER=voyage` + `VOYAGE_API_KEY` for real embeddings (the
deterministic fake keeps dedup and retrieval working offline).

---

## Accounts & demo data

### Platform superadmin (creates organizations)

```bash
cd backend
python manage.py create_superadmin --email superadmin@platform.local --password 'Str0ng@Pass1'
```

Log in as the superadmin to onboard a new organization **and its first admin** in one
step; that admin then manages their own users.

### Demo logins (all password `Prep@1234`)

| Email                    | Role      | Mode                        |
| ------------------------ | --------- | --------------------------- |
| teacher@springfield.demo | TEACHER   | exam (sees all students)    |
| homer@springfield.demo   | STUDENT   | exam                        |
| parent@springfield.demo  | PARENT    | exam (linked to Homer)      |
| mentor@acme.demo         | MENTOR    | interview (sees candidates) |
| dana@acme.demo           | CANDIDATE | interview                   |

Log in as `teacher@springfield.demo` and note you cannot see any Riverdale / Acme /
CodeCoach data — tenant isolation, live.

---

## API

| Endpoint          | Purpose                                  |
| ----------------- | ---------------------------------------- |
| `GET /api/schema/`| OpenAPI schema                           |
| `GET /api/docs/`  | Swagger UI (browsable)                   |
| `GET /healthz/`   | Liveness/readiness probe                 |
| `/api/…`          | All resources — consistent JSON envelope |

Every `/api/` response uses the same envelope: `{"status", "message", "data"}`.
A ready-to-import Postman collection and environment live in
[`postman/`](postman/) (mirrored in [`docs/`](docs/)).

---

## Multi-tenancy

**Goal:** a developer writing an ordinary view (`Model.objects.all()`,
`get_object_or_404`) gets correct tenant isolation **for free** — never having to
remember `.filter(tenant=...)`. Four parts:

1. **`Organization` is the single tenant model**, discriminated by `type`
   (`SCHOOL | COMPANY | INSTITUTE | INDIVIDUAL`). Solo users get an auto-created
   `INDIVIDUAL` org, so there is never a tenant-less row.
2. **A request-scoped current tenant** held in a `contextvars.ContextVar` — correct
   under async and not leaked between Celery tasks that reuse a worker.
3. **Middleware binds the tenant from the JWT**, validating the token with simplejwt,
   reading the `tenant_id` claim, and verifying the token's user actually belongs to
   that organization before binding. The binding is always cleared in a `finally`.
4. **`TenantScoped` base model + `TenantScopedManager`** — the default manager
   auto-filters every query by the bound tenant, and `save()` stamps the tenant from
   context. It **fails closed** (returns `.none()` when no tenant is bound), keeps an
   *unscoped* base manager so Django's FK/cascade machinery isn't filtered, and
   exposes `objects.unscoped()` / `objects.for_tenant(org)` escape hatches for admin,
   migrations, Celery tasks, and the seed script.

Because a Tenant B request can only ever see a queryset scoped to B, fetching Tenant
A's row by primary key returns a clean **404** — never a data leak. This is proven in
`backend/tenants/tests/test_isolation.py`.

**Shared core vs mode-specific models.** Exam and interview prep are the same loop, so
questions/attempts live in **single concrete tables with a `mode` discriminator**
(`PrepContext = EXAM | INTERVIEW`) rather than an abstract base with subclasses. The
differences are small and additive — a couple of nullable columns guarded by
`clean()` — so there's one manager, one query path, and one set of isolation tests per
concept.

---

## Project layout

```
backend/
  prepcheck/            # project: settings (env-driven), urls, celery, wsgi/asgi, exception handler
  core/                 # shared helpers: pagination, permissions, filters, health, constants
  tenants/              # >>> isolation core <<< context, managers, middleware, Organization, onboarding
  accounts/             # custom User (email login, org FK, role), JWT auth + per-tenant RBAC
  materials/            # SourceMaterial / MaterialChunk — upload, parse, chunk, embed (Celery)
  questions/            # grounded question generation + view/edit/delete
  attempts/             # learner answers + async grading against a source-derived rubric
  reports/              # per-topic progress + observer dashboard endpoints
  tests_support/        # test-only concrete TenantScoped model
frontend/               # Vite + React + Tailwind SPA
postman/                # API collection + environment
docker-compose.yml      # web, worker, postgres(pgvector), redis, frontend
Makefile                # dev & ops task runner
```

---

## Testing

```bash
cd backend
pytest                     # full suite — prepcheck.settings_test (in-memory sqlite)
pytest tenants/tests/      # just the tenant isolation suite
make ci                    # tests + Django production deploy checks
```

No Postgres, Redis, or API keys are required — the suite runs entirely on offline
fakes.

---

## Operational notes

- **Errors** — a structured DRF exception handler plus the per-action envelope give
  consistent bodies and never leak stack traces.
- **Logging** — structured `logging` with tenant/user context injected on every
  record; uploads, generation, grading, and auth failures are attributable to a
  tenant/user.
- **Cost control** — each `Organization` carries `llm_daily_call_cap` /
  `llm_monthly_call_cap`, enforced per-tenant by a throttle.
- **Config & migrations** — everything is read via `django-environ`; migrations are
  checked in and `makemigrations --check` is clean.

---

## Roadmap

- Spaced-repetition scheduling for weak topics.
- Mock live-interview mode with voice input.
- Cross-tenant benchmarking for institute admins (opt-in, anonymised).
- Postgres Row-Level Security as defence-in-depth beneath the ORM scoping.
- UUID primary keys to remove even the theoretical value of id enumeration.
