# Specs

This directory contains feature specifications for Progress Grader.

## Status Legend

| Status      | Meaning                                      |
|-------------|----------------------------------------------|
| Draft       | Work in progress, not ready for review       |
| Review      | Ready for team review and feedback           |
| Approved    | Approved, ready to be designed/implemented   |
| Implemented | Feature is live and spec is archived         |

## Index

| Spec | Status | Description |
|------|--------|-------------|
| [workspace-lifecycle.md](workspace-lifecycle.md) | Draft | Per-student per-project container lifecycle (create, pause, resume, destroy) |
| [ai-proxy.md](ai-proxy.md) | Draft | Thin FastAPI proxy that intercepts and logs all student–AI exchanges |
| [conversation-logging.md](conversation-logging.md) | Draft | Schema and rules for storing prompts, responses, consent records |
| [git-integration.md](git-integration.md) | Draft | Local Git + Gitea remote, webhook-based grading signal capture |
| [teacher-dashboard.md](teacher-dashboard.md) | Draft | Teacher-facing web app for reviewing conversations, Git activity, and rubric scoring |
| [auth-and-consent.md](auth-and-consent.md) | Draft | Authentication (Keycloak/SSO), roles, and student consent flow |

## How to Write a Spec

1. Copy `TEMPLATE.md` to a new file named after your feature (e.g., `user-auth.md`).
2. Fill in all sections. Leave none blank — use "N/A" if truly not applicable.
3. Set status to `Draft` and submit for review.
4. Do not begin design or implementation until status is `Approved`.
5. Update the index table above when adding a new spec.
