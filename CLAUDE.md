# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project Overview

**Progress Grader** is a school-focused agentic coding platform that evaluates students not just on their final code, but on *how* they used AI to get there — their prompts, problem decomposition, branching strategy, commit granularity, spec-driven design adherence, and context management.

Teachers get a dashboard to review full student–AI conversation histories (with student consent), alongside Git activity (commits, branches, PRs) captured from each student's isolated workspace.

### Key Concepts
- Each student gets one sandboxed container per project (no context bleed between projects or students)
- All AI calls are routed through a platform-owned proxy — never directly to the AI provider
- Every prompt and response is logged server-side, consent-gated, and surfaced to teachers for grading
- Git activity (commits, branches, PRs) is a grading signal alongside conversation quality

## Finalized Architecture

| Layer | Technology |
|---|---|
| Workspace IDE | OpenVSCode Server (one container per student per project) |
| AI agent UI | Custom VS Code Extension (routes all calls through backend) |
| AI proxy | Thin custom FastAPI proxy (pluggable providers) |
| AI models | OpenAI, Anthropic, Azure, Ollama — configurable |
| Git (local) | Git inside each container |
| Git (hosted) | Gitea (self-hosted, teacher-facing) |
| Database | PostgreSQL |
| Auth | Keycloak (SSO-ready) or Better Auth |
| Orchestration | Docker + Traefik → Kubernetes (when needed) |
| Background jobs | Celery + Redis |
| Teacher dashboard | Next.js + shadcn/ui |
| Languages | Python (backend), TypeScript (extension + dashboard) |

## Spec-Driven Design Workflow

This project follows a **spec-driven design** approach. All features must be fully specified before implementation begins.

### Workflow Steps

1. **Spec** — Write a detailed spec in `specs/` before touching any code.
2. **Design** — Document architecture decisions in `design/`.
3. **Implement** — Write code only after spec and design are approved.
4. **Test** — Verify against the spec, not just the implementation.

### Directory Structure

```
specs/          # Feature specs (.md files)
design/         # Architecture and design documents
src/            # Source code (do not create without a spec)
tests/          # Tests (mirror spec acceptance criteria)
```

## Development Guidelines

- Do not write implementation code without a corresponding spec in `specs/`.
- Each spec file should follow the template in `specs/TEMPLATE.md`.
- Design documents should reference the spec they are derived from.
- Keep specs updated when requirements change — the spec is the source of truth.
- All AI calls must go through the platform proxy — never call AI providers directly from the extension or frontend.
- Student conversation data is consent-gated — enforce at the API layer, not just the UI.

## Commands

### Start the platform (all services)

```bash
cd infra
cp ../.env.example .env   # edit .env and fill in all required secrets
docker compose up -d
```

### Run database migrations

```bash
docker compose exec backend alembic upgrade head
```

### Build the workspace image

The workspace image bundles the VS Code extension. Build from the `services/` directory so the extension source is available to the Dockerfile:

```bash
docker build \
  -t progress-grader/workspace:latest \
  -f services/workspace-image/Dockerfile \
  services/
```

### Build the VS Code extension (.vsix)

```bash
cd services/extension
npm install
npm run package          # produces progress-grader-*.vsix
```

### Build the dashboard (standalone)

```bash
cd services/dashboard
npm install
npm run build
```

### View logs

```bash
cd infra
docker compose logs -f backend
docker compose logs -f proxy
docker compose logs -f dashboard
docker compose logs -f celery-worker
```

### Create a teacher account

```bash
curl -X POST http://localhost/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"teacher@school.edu","password":"secret","role":"teacher"}'
```

### Register a student workspace (after teacher creates project)

```bash
curl -X POST http://localhost/api/workspace/create \
  -H "Authorization: Bearer <student_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<project_uuid>"}'
```
