# Design

This directory contains architecture and design documents for Progress Grader. Each design document is derived from an approved spec in `specs/`.

## Index

| Design Doc | Spec | Status | Description |
|---|---|---|---|
| [workspace-lifecycle-design.md](workspace-lifecycle-design.md) | [workspace-lifecycle.md](../specs/workspace-lifecycle.md) | Draft | Container lifecycle, Traefik routing, Minio archiving, heartbeat pause detection |
| [ai-proxy-design.md](ai-proxy-design.md) | [ai-proxy.md](../specs/ai-proxy.md) | Draft | Thin FastAPI proxy, provider adapters, context tracking, dual student/platform use |
| [conversation-logging-design.md](conversation-logging-design.md) | [conversation-logging.md](../specs/conversation-logging.md) | Draft | Full schema, async write path, consent enforcement query, read APIs |
| [git-integration-design.md](git-integration-design.md) | [git-integration.md](../specs/git-integration.md) | Draft | Gitea setup, provisioning sequence, webhook ingestion, grading signal queries |
| [teacher-dashboard-design.md](teacher-dashboard-design.md) | [teacher-dashboard.md](../specs/teacher-dashboard.md) | Draft | Next.js architecture, timeline data assembly, AI grading flow, CSV export |
| [auth-and-consent-design.md](auth-and-consent-design.md) | [auth-and-consent.md](../specs/auth-and-consent.md) | Draft | Keycloak/Better Auth flow, JWT structure, consent modal, role + consent middleware |

## How to Write a Design Doc

1. Copy `TEMPLATE.md` to a new file (e.g. `my-feature-design.md`).
2. Link back to the originating spec.
3. Fill in all sections before implementation begins.
4. Move status from `Draft` → `Review` → `Approved`.
5. Update the index table above.
