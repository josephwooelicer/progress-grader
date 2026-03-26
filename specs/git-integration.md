# Spec: Git Integration

**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Overview

Each student workspace has a local Git repository. A self-hosted Gitea instance acts as the remote (`origin`), giving teachers browser-based visibility into commit history, branches, and pull requests without accessing student containers directly. Git activity events (commits, branches, PRs) are also captured as grading signals via Gitea webhooks.

## 2. Goals

- Give students a normal Git workflow (commit, push, branch, PR) inside their workspace
- Give teachers read access to all student repositories from one Gitea instance
- Capture Git activity as structured grading signals (commit granularity, branching strategy, PR usage)
- Ensure Git history persists as long as the workspace volume exists

## 3. Non-Goals

- Replacing Gitea with a custom Git server
- Real-time code review features (teachers can view code on Gitea; inline annotation is a v2 feature)
- Enforcing specific branching models (Git workflow is a grading signal, not a constraint)
- Supporting multiple remotes per workspace in v1

## 4. Requirements

### Functional Requirements

| ID   | Requirement | Priority |
|------|-------------|----------|
| FR-1 | Each workspace is provisioned with a local Git repo at `/workspace/{project_slug}` | Must |
| FR-2 | A corresponding Gitea repository is created for each `(student_id, project_id)` at workspace creation | Must |
| FR-3 | The local Git remote `origin` points to the student's Gitea repository | Must |
| FR-4 | Student Git identity (`user.name`, `user.email`) is pre-configured from their platform profile | Must |
| FR-5 | Students can push, pull, branch, and open PRs using standard Git commands and the VS Code Git panel | Must |
| FR-6 | Teachers have read-only access to all student repositories on Gitea | Must |
| FR-7 | Gitea webhooks fire on: push, branch create/delete, PR open, PR merge | Must |
| FR-8 | The platform backend consumes webhook events and writes structured grading signal records to PostgreSQL | Must |
| FR-9 | Gitea repositories are organised under a per-course organisation (e.g. `gitea.domain/course-cs101/`) | Should |
| FR-10 | Students cannot access other students' Gitea repositories | Must |
| FR-11 | Each project has a teacher-defined base skeleton (files/folders uploaded or defined at project creation time) | Must |
| FR-12 | At workspace creation, the platform commits the base skeleton as the first commit using a platform bot user identity | Must |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | Gitea runs as a single Docker container with a persistent volume | Must |
| NFR-2 | Webhook delivery to platform backend must be retried on failure (Gitea built-in retry) | Must |
| NFR-3 | Git operations inside the workspace must not require the student to enter credentials | Must (token pre-configured) |

## 5. User Stories

```
As a student, I want to commit and push code using standard Git commands
so that my workflow is not different from any other development environment.

As a student, I want to create branches and open PRs
so that I can practice a professional Git workflow as part of my grade.

As a teacher, I want to browse a student's commit history on Gitea
so that I can evaluate commit granularity and message quality without accessing containers.

As a teacher, I want to see a student's branching and PR activity
so that I can evaluate their version control strategy.
```

## 6. Grading Signals Captured from Git

| Signal | Source | What it Reveals |
|---|---|---|
| Commit frequency | Push webhook → commit list | Whether student commits in small, logical chunks |
| Commit message quality | Push webhook → commit messages | Descriptiveness, clarity of intent |
| Branch naming | Branch create webhook | Problem decomposition, feature isolation |
| PR creation | PR open webhook | Whether student uses PRs for review/integration |
| PR description | PR open webhook | Ability to communicate changes clearly |
| Time between commits | Commit timestamps | Pacing, not coding in one session |
| Commits-per-session | Correlate with workspace activity | Incremental progress vs. big-bang submissions |
| Force-push | Push webhook (forced flag) | Did student rewrite or hide history before submission |

All signals are stored in a `git_events` table (see schema below).

## 7. Data Schema

### `git_events` table

```sql
CREATE TABLE git_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    event_type      TEXT NOT NULL,  -- 'push', 'branch_create', 'branch_delete', 'pr_open', 'pr_merge'
    payload         JSONB NOT NULL, -- raw webhook payload (Gitea format)
    commit_sha      TEXT,
    commit_message  TEXT,
    branch_name     TEXT,
    pr_number       INTEGER,
    pr_title        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_git_events_student_project ON git_events (student_id, project_id);
CREATE INDEX idx_git_events_type            ON git_events (event_type);
```

## 8. Workspace Git Provisioning

On workspace creation:

1. Platform backend calls Gitea API to create a new repository under the course organisation
2. A per-workspace Git credential token is generated and stored (scoped to that repo only)
3. Container is started with environment variables containing the token
4. Git is configured inside the container:
   ```bash
   git init /workspace/{project_slug}
   git config user.name  "{student display name}"
   git config user.email "{student email}"
   git remote add origin https://{token}@gitea.domain/{org}/{repo}.git
   ```
5. Gitea webhook is registered on the repo pointing to `https://platform.domain/webhooks/gitea`

## 9. Teacher Access

- Teachers are added to the Gitea course organisation with `Reporter` role (read-only)
- Teachers access Gitea via their own Gitea account, not as the student
- The teacher dashboard deep-links into Gitea for commit/branch/PR views
- No teacher can push to a student's repository

## 10. Design Notes

- See `design/git-integration-design.md` (to be written after spec approval)
- Gitea is chosen for its low resource footprint and full API/webhook support
- Git credentials inside the container use HTTPS + token (not SSH) for simplicity; SSH can be added in v2

## 11. Acceptance Criteria

- [ ] A newly created workspace has a local Git repo with `origin` pointing to Gitea
- [ ] `git push` from the workspace succeeds without prompting for credentials
- [ ] A push event triggers a webhook that writes a `git_events` row within 10 seconds
- [ ] Teacher can browse the student's commit history and branches on Gitea
- [ ] Student cannot access another student's Gitea repository
- [ ] PR creation on Gitea triggers a `pr_open` event row in `git_events`

## 12. Open Questions

- Platform makes the initial commit at workspace creation. Each project has a base skeleton (files defined by the teacher per project) committed as `chore: initial project scaffold` by a platform bot user. Student commits start from this baseline.
- All Git actions are permitted including force-push, history rewrite, and branch deletion. No Gitea branch protection rules enforced. Force-push events are captured via webhook as a grading signal.
- Read-only Gitea access for teachers in v1. No inline code comments on Gitea. Teacher feedback is left on the unified activity timeline in the teacher dashboard (see `specs/teacher-dashboard.md`), which interleaves conversation messages and git events chronologically.
- [ ] Should spec files (`specs/*.md`) be committed to the student's project repo as part of the workflow?

## 13. References

- `specs/workspace-lifecycle.md` — Git provisioning happens at workspace creation
- `specs/teacher-dashboard.md` — reads `git_events` and links to Gitea
- `specs/auth-and-consent.md` — teacher Gitea access controlled by platform roles
