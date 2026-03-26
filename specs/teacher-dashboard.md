# Spec: Teacher Dashboard

**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Overview

The Teacher Dashboard is a web application (Next.js) where teachers review student–AI conversation histories, Git activity, and apply grading rubrics to evaluate how students used agentic coding tools. It is the primary grading interface for this platform — teachers do not need to access containers, Gitea directly, or raw database records.

## 2. Goals

- Give teachers a clear, structured view of each student's AI interactions and Git activity per project
- Surface grading signals derived from conversation and Git data in an easy-to-scan format
- Allow teachers to annotate and score students against a rubric
- Link directly to Gitea for deep inspection of commits, branches, and PRs

## 3. Non-Goals

- Running or modifying student code (read-only view only)
- Real-time monitoring of students while they work (review is asynchronous, post-session)
- Auto-grading or AI-assisted scoring in v1
- Student-facing views (students do not use this dashboard)

## 4. Requirements

### Functional Requirements

| ID   | Requirement | Priority |
|------|-------------|----------|
| FR-1 | Teacher can view a list of all students and their projects in their assigned courses | Must |
| FR-2 | Teacher can open a student project and see all conversation sessions, ordered by date | Must |
| FR-3 | Each conversation session shows the full prompt/response thread with timestamps | Must |
| FR-4 | Teacher can see conversation boundaries (where a new `conversation_id` begins) as a visible separator | Must |
| FR-5 | Teacher can view Git activity summary per student project: commit count, branch count, PR count | Must |
| FR-6 | Teacher can click through to Gitea for full commit/branch/PR detail | Must |
| FR-7 | Teacher can apply a rubric score per grading dimension for each student project | Must |
| FR-8 | Rubric scores and annotations are saved and retrievable | Must |
| FR-9 | Teacher cannot view conversations for students who have not consented | Must (enforced by API) |
| FR-10 | Dashboard shows a consent status indicator per student | Must |
| FR-11 | Teacher can filter/search students by name, project, consent status | Should |
| FR-12 | Dashboard is read-only — no teacher can modify student conversation data | Must |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | Built with Next.js + shadcn/ui | Must |
| NFR-2 | Conversation thread must load within 2 seconds for up to 500 messages | Must |
| NFR-3 | Dashboard is accessible only to authenticated users with `teacher` or `admin` role | Must |

## 5. User Stories

```
As a teacher, I want to see all my students' projects in one place
so that I can efficiently navigate to any student's work.

As a teacher, I want to read a student's AI conversation in full, with clear conversation breaks,
so that I can evaluate their context management and prompt quality.

As a teacher, I want to see how many commits a student made and how often they branched
so that I can evaluate their Git workflow without leaving the dashboard.

As a teacher, I want to score each student on a rubric and leave notes
so that I have structured, defensible grades.

As a teacher, I want to be blocked from viewing a student's conversations if they haven't consented
so that I never inadvertently access unconsented data.
```

## 6. Grading Rubric Dimensions

The rubric is applied per `(teacher, student, project)`. Each dimension is scored on a configurable scale (default: 1–5).

| Dimension | What is Evaluated | Data Source |
|---|---|---|
| **Prompt quality** | Clarity, specificity, context given in prompts | Conversation logs |
| **Problem decomposition** | Whether student breaks problems into small asks | Conversation logs + commit patterns |
| **Context management** | Appropriate use of new conversations to prevent bloat | Conversation boundaries (`conversation_id` resets) |
| **Spec-driven approach** | Evidence of writing specs before asking for code | Conversation logs + Git file history |
| **Commit granularity** | Small, logical commits with clear messages | Git events |
| **Branching strategy** | Feature branches, meaningful names, PR usage | Git events |
| **PR quality** | PR descriptions, review engagement | Git events |

### `rubric_scores` table

```sql
CREATE TABLE rubric_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES users(id),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    dimension       TEXT NOT NULL,
    score           SMALLINT NOT NULL CHECK (score BETWEEN 1 AND 5),
    annotation      TEXT,
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_rubric_unique ON rubric_scores (teacher_id, student_id, project_id, dimension);
```

## 7. Dashboard Page Structure

```
/dashboard                          → Course/student list
/dashboard/courses/{course_id}      → Students in course
/dashboard/students/{student_id}/projects/{project_id}
  ├── /conversations                → Full conversation thread view
  ├── /git                          → Git activity summary + Gitea links
  └── /rubric                       → Rubric scoring form
```

## 8. Conversation View Details

- Messages displayed in chronological order
- `user` messages: visually distinct from `assistant` messages
- Conversation boundaries shown as a labelled divider: `— New conversation started at {timestamp} —`
- Each message shows: timestamp, role, content, model name, token count
- Token counts help teachers see if student is managing context (high token counts = not starting new conversations)

## 9. Git Activity View Details

- Summary cards: total commits, branches created, PRs opened, PRs merged
- Commit timeline: list of commits with SHA (truncated), message, timestamp, branch
- Each commit SHA links to Gitea commit detail page
- Branch list with creation date, links to Gitea branch view
- PR list with title, state, description preview, links to Gitea PR page

## 10. Design Notes

- See `design/teacher-dashboard-design.md` (to be written after spec approval)
- All data is fetched from the platform backend API — the dashboard never queries PostgreSQL or Gitea directly
- Gitea links are deep links into the self-hosted Gitea instance; teachers must have a Gitea account (provisioned by admin)

## 11. Acceptance Criteria

- [ ] Teacher can navigate to a student project and see all conversations grouped by session
- [ ] Conversation boundaries (new `conversation_id`) are visually distinct
- [ ] Teacher sees "No consent on file" and no conversation data for unconsented students
- [ ] Git summary shows correct commit/branch/PR counts matching Gitea
- [ ] Teacher can submit rubric scores for all 7 dimensions and they persist across page reloads
- [ ] Dashboard page load is under 2 seconds for a student with 500 conversation messages
- [ ] A user with `student` role cannot access any dashboard route

## 12. Open Questions

- [ ] Should rubric dimensions be configurable per course, or fixed platform-wide?
- [ ] Should teachers be able to export rubric scores to CSV for upload to an LMS (e.g. Canvas, Moodle)?
- [ ] Should there be a "flag for review" feature so teachers can mark interesting prompts?
- [ ] Do admins need a separate view to see all teachers' rubric scores across a course?

## 13. References

- `specs/conversation-logging.md` — source of conversation data displayed here
- `specs/git-integration.md` — source of Git activity data displayed here
- `specs/auth-and-consent.md` — consent status check enforced before data is shown
