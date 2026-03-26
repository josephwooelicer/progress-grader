# Design: Workspace Lifecycle

**Spec:** [specs/workspace-lifecycle.md](../specs/workspace-lifecycle.md)
**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Summary

Each student project runs in a dedicated Docker container hosting OpenVSCode Server. This document describes how containers are created, routed, paused, resumed, reset, and destroyed — and how the supporting services (Traefik, Minio, Celery) are wired together.

---

## 2. Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Platform Backend (FastAPI)            │
│  WorkspaceService: create / pause / resume / destroy     │
│  ArchiveService: zip volume → Minio on destroy           │
└────────┬──────────────────────┬───────────────────────┘
         │ Docker API            │ Celery tasks
         ▼                      ▼
┌──────────────────┐    ┌─────────────────────┐
│  Docker Engine   │    │  Celery + Redis      │
│  (containers +   │    │  - archive_workspace │
│   volumes)       │    │  - purge_old_archives│
└────────┬─────────┘    └─────────────────────┘
         │ container labels
         ▼
┌──────────────────┐    ┌─────────────────────┐
│  Traefik         │    │  Minio              │
│  (reverse proxy) │    │  (archive storage)  │
│  ws-{id}.domain  │    │  archives/{s}/{p}/  │
└──────────────────┘    └─────────────────────┘
```

---

## 3. Container Naming and Volumes

| Resource | Name Pattern | Example |
|---|---|---|
| Container | `ws-{workspace_id}` | `ws-a1b2c3d4` |
| Volume | `vol-{student_id}-{project_id}` | `vol-s123-p456` |
| URL | `ws-{workspace_id}.platform.domain` | `ws-a1b2c3d4.app.school.edu` |
| Minio archive key | `archives/{student_id}/{project_id}/{timestamp}.zip` | `archives/s123/p456/20260326T120000.zip` |

Volume name is stable across resets and re-provisions so it can be referenced for future backup tooling.

---

## 4. Workspace States and Transitions

```
pending ──► running ──► paused ──► running
              │            │
              │            └──► reset (wipe vol, re-provision)
              │
              └──► destroyed (archive → delete vol → remove container record)
```

### State storage

Workspace state is stored in the `workspaces` table:

```sql
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    state           TEXT NOT NULL CHECK (state IN ('pending','running','paused','destroyed')),
    container_id    TEXT,           -- Docker container ID, NULL when paused/destroyed
    url             TEXT,           -- assigned subdomain URL
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (student_id, project_id)
);
```

---

## 5. Container Lifecycle Operations

### 5.1 Create (pending → running)

1. Insert `workspaces` row with `state=pending`
2. Pull/verify workspace Docker image (pre-built, pinned version)
3. `docker volume create vol-{student_id}-{project_id}` (idempotent)
4. `docker run` with:
   - Volume mounted at `/workspace`
   - Traefik labels for subdomain routing + auth middleware
   - Env vars: `STUDENT_ID`, `PROJECT_ID`, `JWT_SECRET`, `PLATFORM_API_URL`, `GITEA_TOKEN`
   - Network: isolated student network (no container-to-container access)
   - Resource limits from project config or global default
5. Update `workspaces` row: `state=running`, `container_id`, `url`

### 5.2 Pause (running → paused)

Triggered by: WebSocket heartbeat disconnect (60s grace) or admin/teacher manual action.

1. `docker stop ws-{workspace_id}` (SIGTERM → SIGKILL after 10s)
2. Update `workspaces`: `state=paused`, `container_id=NULL`
3. Volume is retained

### 5.3 Resume (paused → running)

1. `docker start` with same config as create, same volume
2. Update `workspaces`: `state=running`, `container_id`

### 5.4 Reset (student-initiated re-provision)

1. Check for unpushed commits via Git API on Gitea (compare local volume HEAD vs remote HEAD)
2. Return unpushed commit list to client for warning UI
3. On student confirmation:
   - `docker stop` + `docker rm ws-{workspace_id}`
   - `docker volume rm vol-{student_id}-{project_id}`
   - `docker volume create vol-{student_id}-{project_id}` (fresh)
   - Re-run create flow (step 5.1) — Gitea remote is unchanged

### 5.5 Destroy (admin/teacher only)

Default (archive enabled):
1. `docker stop` + `docker rm ws-{workspace_id}`
2. Dispatch Celery task `archive_workspace(student_id, project_id)`
   - Mounts volume, zips `/workspace`, uploads to Minio
   - Records archive metadata in `workspace_archives` table
3. `docker volume rm vol-{student_id}-{project_id}`
4. Update `workspaces`: `state=destroyed`

Skip archive:
- Same as above but skip step 2

---

## 6. Pause Detection (Tab Close / Session Expiry)

OpenVSCode Server maintains a WebSocket connection to the browser. The platform backend monitors this via a sidecar or by polling the container's active connections:

- Each running container emits a heartbeat ping to the platform backend every 30 seconds
- If the platform backend receives no heartbeat for 60 seconds (grace period), it triggers pause
- This is implemented as a lightweight Celery beat task that checks heartbeat timestamps per workspace

```sql
CREATE TABLE workspace_heartbeats (
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    last_seen_at    TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (workspace_id)
);
```

---

## 7. Resource Limits

Global defaults stored in platform config (env vars or admin settings table). Per-project overrides stored in `projects.resource_overrides JSONB`.

Applied to container at creation:

```python
limits = project.resource_overrides or global_defaults
docker.run(
    ...
    cpu_quota=limits["cpu_quota"],   # e.g. 100000 = 1 CPU
    mem_limit=limits["mem_limit"],   # e.g. "512m"
    memswap_limit=limits["mem_limit"],  # disable swap
)
```

---

## 8. Archive Storage

```
workspace_archives table:
    id              UUID
    student_id      UUID
    project_id      UUID
    minio_key       TEXT    -- full object key
    size_bytes      BIGINT
    archived_at     TIMESTAMPTZ
    purge_after     TIMESTAMPTZ  -- archived_at + 30 days
    purged_at       TIMESTAMPTZ  -- NULL until Celery purge job runs
```

Celery beat job `purge_old_archives` runs daily:
- Queries `workspace_archives WHERE purge_after < now() AND purged_at IS NULL`
- Deletes object from Minio
- Sets `purged_at = now()`

---

## 9. Traefik Routing

Each container is started with Docker labels:

```
traefik.enable=true
traefik.http.routers.ws-{id}.rule=Host(`ws-{id}.platform.domain`)
traefik.http.routers.ws-{id}.middlewares=platform-auth
traefik.http.services.ws-{id}.loadbalancer.server.port=3000
```

`platform-auth` middleware validates the session JWT before proxying to the container. Implemented as a Traefik ForwardAuth middleware pointing to the platform backend's `/auth/verify` endpoint.

---

## 10. Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| Docker stop/start for pause | Checkpoint/restore (CRIU) | Simpler, sufficient for this use case; CRIU adds complexity |
| Volume-per-workspace | Shared NFS / bind mounts | Strong isolation; no cross-student filesystem risk |
| Celery for archive | Synchronous in request | Destroy returns immediately; archive runs in background |
| Heartbeat via container ping | Docker events API | More reliable; Docker events miss tab-close scenarios |

---

## 11. Open Questions

None — all spec questions resolved.
