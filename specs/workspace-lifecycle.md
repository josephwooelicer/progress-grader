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
| FR-6 | Workspaces auto-pause after a configurable idle timeout (default: 30 minutes) | Should |
| FR-7 | Students can manually pause and resume their own workspace | Should |
| FR-8 | Admins and teachers can pause or destroy any workspace | Must |
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

As a student, I want my workspace to pause when I'm idle and resume where I left off
so that I don't lose work between sessions.

As a teacher, I want to pause or destroy a student's workspace
so that I can enforce project deadlines or free up resources.

As an admin, I want to set resource limits per workspace
so that no single student can starve shared infrastructure.
```

## 6. Lifecycle State Machine

```
[pending] → [running] → [paused] → [running]
                    └──────────────→ [destroyed]
```

| Transition | Trigger |
|---|---|
| pending → running | Student opens project / workspace created |
| running → paused | Idle timeout OR manual pause |
| paused → running | Student resumes session |
| running → destroyed | Admin/teacher action OR project deadline passed |
| paused → destroyed | Admin/teacher action |

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

## 11. Acceptance Criteria

- [ ] A student who has never opened a project gets a running workspace within 30 seconds
- [ ] Two students opening the same project get separate, independent containers
- [ ] A student who resumes a paused workspace finds all files and git history intact
- [ ] A workspace idle for 30 minutes is automatically paused
- [ ] A destroyed workspace's volume is deleted and cannot be recovered via the UI
- [ ] No container can reach another container's filesystem or network

## 12. Open Questions

- [ ] Should workspace CPU/memory limits be configurable per-project or globally by admin?
- [ ] Do we need a "archiving" state between paused and destroyed (e.g. export to zip before deletion)?
- [ ] How do we handle students who lose network mid-session — grace period before auto-pause?

## 13. References

- `specs/ai-proxy.md` — AI agent extension provisioned in each workspace
- `specs/git-integration.md` — Gitea remote configuration
- `specs/auth-and-consent.md` — Session auth enforced at Traefik layer
