# Design: Git Integration

**Spec:** [specs/git-integration.md](../specs/git-integration.md)
**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Summary

Each student workspace has a local Git repo. A self-hosted Gitea instance acts as the `origin` remote. Gitea webhooks deliver push, branch, and PR events to the platform backend, which persists them as structured grading signals. Teachers browse Gitea read-only for code inspection; the teacher dashboard consumes the structured events for timeline and rubric grading.

---

## 2. Component Overview

```
Student workspace container
  └─► git push origin ──► Gitea (self-hosted)
                               │
                    ┌──────────┴──────────┐
                    │  Gitea webhook       │
                    ▼                     ▼
          Platform Backend          Teacher browser
          (consume webhook,          (Gitea read-only
           write git_events)          UI, deep links)
                    │
                    ▼
              PostgreSQL
              (git_events)
                    │
                    ▼
          Teacher Dashboard
          (timeline cards,
           grading signals)
```

---

## 3. Gitea Setup

| Concern | Decision |
|---|---|
| Deployment | Single Docker container, persistent volume for repos + DB |
| Organisation structure | One Gitea organisation per course: `course-{course_id}` |
| Student repo naming | `{student_username}-{project_slug}` under the course org |
| Platform bot user | `platform-bot` Gitea account; makes initial commits |
| Teacher access | `Reporter` role on the course org (read-only) |
| Student access | `Owner` of their own repo only |
| Webhook target | `POST https://platform.domain/webhooks/gitea` — all events |

---

## 4. Workspace Git Provisioning Sequence

```
WorkspaceService.create(student_id, project_id)
  │
  ├─► GiteaClient.create_repo(org=course_org, name=repo_name)
  │         → returns clone URL
  │
  ├─► GiteaClient.create_webhook(repo, url=platform_webhook_url, events=["push","create","pull_request"])
  │
  ├─► GiteaClient.generate_token(student_user, repo)
  │         → scoped access token, stored encrypted in workspaces table
  │
  ├─► Build base skeleton (AGENT.md, specs/TEMPLATE.md, .gitignore, .mcp.json if enabled)
  │         → teacher-defined content fetched from projects table
  │
  ├─► GiteaClient.init_repo_with_files(repo, files, committer="platform-bot",
  │         message="chore: initial project scaffold")
  │
  └─► Container started with env vars:
            GITEA_TOKEN=<encrypted token>
            GITEA_REMOTE=https://<token>@gitea.domain/course-org/repo.git
            GIT_AUTHOR_NAME=<student name>
            GIT_AUTHOR_EMAIL=<student email>

  Inside container (entrypoint script):
    git clone $GITEA_REMOTE /workspace
    git config user.name  "$GIT_AUTHOR_NAME"
    git config user.email "$GIT_AUTHOR_EMAIL"
```

---

## 5. Webhook Ingestion

### Endpoint

```
POST /webhooks/gitea
  → verify Gitea HMAC signature (X-Gitea-Signature header)
  → parse event type from X-Gitea-Event header
  → dispatch to handler
```

### Event Handlers

| Gitea Event | Handler | git_events row |
|---|---|---|
| `push` (non-forced) | `handle_push` | event_type=`push`, one row per commit |
| `push` (forced=true) | `handle_push` | event_type=`force_push` |
| `create` (ref_type=branch) | `handle_branch_create` | event_type=`branch_create` |
| `delete` (ref_type=branch) | `handle_branch_delete` | event_type=`branch_delete` |
| `pull_request` (action=opened) | `handle_pr_open` | event_type=`pr_open` |
| `pull_request` (action=closed, merged=true) | `handle_pr_merge` | event_type=`pr_merge` |

### Student resolution

`student_id` is resolved from the Gitea repo name: `{student_username}-{project_slug}` → look up `users` by `gitea_username`.

---

## 6. git_events Schema

```sql
CREATE TABLE git_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    event_type      TEXT NOT NULL,
    payload         JSONB NOT NULL,   -- raw Gitea webhook payload
    commit_sha      TEXT,
    commit_message  TEXT,
    branch_name     TEXT,
    pr_number       INTEGER,
    pr_title        TEXT,
    pr_description  TEXT,
    forced          BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_git_events_student_project ON git_events (student_id, project_id);
CREATE INDEX idx_git_events_type            ON git_events (event_type);
CREATE INDEX idx_git_events_created         ON git_events (created_at);
```

---

## 7. Grading Signal Queries

These are the key queries the AI grading service and teacher dashboard use:

```sql
-- Commit frequency (commits per day)
SELECT DATE(created_at) as day, COUNT(*) as commits
FROM git_events
WHERE student_id=? AND project_id=? AND event_type='push'
GROUP BY day ORDER BY day;

-- Commit messages (for quality evaluation)
SELECT commit_message, created_at FROM git_events
WHERE student_id=? AND project_id=? AND event_type='push'
ORDER BY created_at;

-- Branch activity
SELECT branch_name, created_at FROM git_events
WHERE student_id=? AND project_id=? AND event_type='branch_create'
ORDER BY created_at;

-- PR history
SELECT pr_title, pr_description, event_type, created_at FROM git_events
WHERE student_id=? AND project_id=? AND event_type IN ('pr_open','pr_merge')
ORDER BY created_at;

-- Force-push count
SELECT COUNT(*) FROM git_events
WHERE student_id=? AND project_id=? AND forced=true;
```

---

## 8. Teacher Deep Links into Gitea

The teacher dashboard generates Gitea URLs for drill-down:

| View | URL pattern |
|---|---|
| Commit detail | `https://gitea.domain/{org}/{repo}/commit/{sha}` |
| Branch view | `https://gitea.domain/{org}/{repo}/src/branch/{name}` |
| PR detail | `https://gitea.domain/{org}/{repo}/pulls/{number}` |
| Full history | `https://gitea.domain/{org}/{repo}/commits/branch/main` |

---

## 9. Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| Gitea (self-hosted) | GitHub / GitLab | No external dependency; full webhook control; lightweight |
| HTTPS token auth | SSH keys | Simpler to provision per-container; SSH can be added v2 |
| Webhook per repo | Gitea system webhook | Per-repo allows finer control and easier debugging |
| Raw payload stored in JSONB | Normalised columns only | Future-proofing; can extract new fields without schema migration |

---

## 10. Open Questions

None — all spec questions resolved.
