# Spec: Workspace Lifecycle

**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Overview

Each student project runs in an isolated container hosting an OpenVSCode Server instance. This spec defines how workspaces are created, accessed, paused, resumed, and destroyed — ensuring per-student per-project isolation with no context bleed between projects or students.

## 2. Goals

- Provide each student with a fully isolated coding environment per project
- Allow students to resume work across sessions without data loss
- Enable teachers and admins to manage workspace lifecycle (pause, destroy)
- Allow students to reset (re-provision) their own workspace without teacher/admin involvement
- Route each workspace to a unique URL via Traefik

## 3. Non-Goals

- Building a custom terminal or file editor (OpenVSCode Server handles this)
- Multi-student collaboration within a single workspace
- Real-time workspace resource auto-scaling (out of scope for v1)

## 4. Requirements

### Functional Requirements

| ID   | Requirement | Priority |
|------|-------------|----------|
| FR-1 | A workspace is created when a student opens a project for the first time | Must |
| FR-2 | Each workspace is scoped to a single `(student_id, project_id)` pair | Must |
| FR-3 | Workspaces persist across sessions — student files and git history are not lost on pause | Must |
| FR-4 | A workspace can be in one of four states: `pending`, `running`, `paused`, `destroyed` | Must |
| FR-5 | Each running workspace is accessible at a unique URL (e.g. `ws-{id}.domain.com`) routed via Traefik | Must |
| FR-6 | Workspaces auto-pause when the student's browser tab is closed or their session expires | Must |
| FR-7 | Admins and teachers can manually pause any workspace | Should |
| FR-8 | Admins and teachers can pause or destroy any workspace; students cannot destroy their workspace | Must |
| FR-11 | Students can reset (re-provision) their own workspace: volume is wiped and container is recreated fresh; Gitea remote is untouched | Must |
| FR-12 | Before a student confirms a reset, the platform warns them of any commits that exist locally but have not been pushed to Gitea | Must |
| FR-13 | On destroy, the workspace volume is automatically archived as a zip to object storage (Minio) before deletion | Must |
| FR-14 | Archives are retained for 30 days then permanently deleted | Must |
| FR-15 | Admin/teacher can opt to skip archiving when destroying a workspace | Must |
| FR-16 | Archived workspaces are accessible to admins only (not student-facing) in v1 | Must |
| FR-9 | Workspace creation provisions: OpenVSCode Server, Git, the AI agent VS Code extension, and Gitea remote config | Must |
| FR-10 | Resource limits (CPU, memory) are enforced per container | Must |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | Workspace startup time (pending → running) | < 30 seconds |
| NFR-2 | Workspace files persisted to a named Docker volume | Per workspace |
| NFR-3 | No network access between student containers | Enforced via Docker network policy |

## 5. User Stories

```
As a student, I want to open my project and get a running IDE immediately
so that I can start coding without manual setup.

As a student, I want my workspace to pause automatically when I close my browser tab
so that resources are freed without me having to do anything manually.

As a student, I want to reset my workspace to a clean state
so that I can start fresh without needing to ask a teacher or admin.

As a teacher, I want to pause or destroy a student's workspace
so that I can enforce project deadlines or free up resources.

As an admin, I want to set resource limits per workspace
so that no single student can starve shared infrastructure.
```

## 6. Lifecycle State Machine

```
[pending] → [running] → [paused] → [running]
               │                      │
               └──── student reset ───┘ (re-provision: wipe volume, recreate → pending → running)
               │
               └──────────────────────→ [destroyed]  (admin/teacher only)
```

| Transition | Trigger | Who |
|---|---|---|
| pending → running | Student opens project / workspace created | Student / system |
| running → paused | Browser tab closed / session expired / admin-teacher manual pause | System / admin / teacher |
| paused → running | Student resumes session | Student |
| running/paused → reset | Student confirms re-provision (with unpushed commit warning) | Student only |
| running/paused → destroyed | Manual action | Admin / teacher only |

**Destruction triggers (exhaustive list):**
- Admin manually destroys a workspace
- Teacher manually destroys a workspace (e.g. project deadline closed)
- Admin deletes a student's account
- Admin archives a course (bulk destroy of all workspaces in that course)

## 7. Container Provisioning Checklist

On first creation, each workspace container must include:

- [ ] OpenVSCode Server (latest stable, pinned version)
- [ ] Git (pre-configured with student identity)
- [ ] AI agent VS Code extension (pre-installed, see `specs/ai-proxy.md`)
- [ ] Gitea remote configured as `origin` pointing to the student's project repo on the self-hosted Gitea instance
- [ ] SSH key or token for Gitea auth pre-provisioned
- [ ] Working directory initialised at `/workspace/{project_slug}`

## 8. URL Routing

- Each running workspace gets a unique subdomain: `ws-{workspace_id}.platform.domain`
- Traefik handles routing based on a label set on the container at creation time
- Auth is enforced at the Traefik middleware layer (valid session token required before proxying to the container)

## 9. Persistent Storage

- Each workspace has a named Docker volume: `vol-{student_id}-{project_id}`
- Volume is retained when workspace is paused
- Volume is deleted only when workspace is `destroyed`
- Backups: not in scope for v1, but volume name must be stable for future backup tooling

## 10. Design Notes

- See `design/workspace-lifecycle-design.md` (to be written after spec approval)
- Container orchestration starts with Docker + Traefik; Kubernetes migration path should be non-breaking (volumes → PVCs, containers → Pods)
- Object storage for archives: Minio (self-hosted, S3-compatible); archive key format: `archives/{student_id}/{project_id}/{timestamp}.zip`
- 30-day archive expiry enforced via a Celery scheduled job (not Minio lifecycle policy, for auditability)

## 11. Acceptance Criteria

- [ ] A student who has never opened a project gets a running workspace within 30 seconds
- [ ] Two students opening the same project get separate, independent containers
- [ ] A student who resumes a paused workspace finds all files and git history intact
- [ ] A workspace pauses automatically when the student closes the browser tab or their session expires
- [ ] A workspace does not pause while the browser tab remains open, regardless of inactivity
- [ ] A destroyed workspace's volume is deleted and cannot be recovered via the UI
- [ ] No container can reach another container's filesystem or network
- [ ] A student who resets their workspace sees a warning listing unpushed commits before confirming
- [ ] After a reset, the workspace re-provisions to a clean state within 30 seconds and Gitea remote is intact
- [ ] A student cannot destroy their own workspace (destroy action is absent from student UI)
- [ ] Destroying a workspace (without skip) produces a zip archive in Minio within 60 seconds
- [ ] Archive is retrievable by admin for 30 days, then automatically deleted
- [ ] Destroying with "skip archiving" deletes the volume immediately with no archive created

## 12. Open Questions

- Resource limits have a global default set by admin, overridable per project. Schema: `projects.resource_overrides JSONB` (nullable; falls back to global config if null).
- On destroy, the workspace volume is automatically archived (zipped) to object storage (Minio) and retained for 30 days before permanent deletion. Admin/teacher can opt to skip archiving at the point of destruction. Archive is admin-accessible only (not student-facing in v1).
- Pause is triggered by browser tab close or session expiry (detected via WebSocket/heartbeat disconnect from the openvscode-server connection). A short grace period (e.g. 60 seconds) should be applied before pausing to handle brief network drops or accidental tab closes. Grace period duration is admin-configurable.

## 13. References

- `specs/ai-proxy.md` — AI agent extension provisioned in each workspace
- `specs/git-integration.md` — Gitea remote configuration
- `specs/auth-and-consent.md` — Session auth enforced at Traefik layer
