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
| FR-3 | The primary view is a unified activity timeline merging conversation messages and git events in chronological order | Must |
| FR-4 | Conversation boundaries (new `conversation_id`) appear as labelled dividers in the timeline | Must |
| FR-5 | Git events (commits, branches, PRs, force-pushes) appear as cards in the timeline at the correct timestamp | Must |
| FR-6 | Teachers can leave comments on any individual timeline entry; comments are stored and persist | Must |
| FR-7 | Teacher can click through to Gitea for full commit/branch/PR detail (read-only) | Must |
| FR-7 | Teacher can click through to Gitea for full commit/branch/PR detail (read-only) | Must |
| FR-8 | Teacher defines rubric dimensions per project at project creation; mandatory platform dimensions are prefilled and cannot be removed | Must |
| FR-9 | Teacher can add custom rubric dimensions with a name, description, and scoring criteria | Must |
| FR-10 | Teacher can trigger AI grading for a student (or bulk for all students in a project) | Must |
| FR-11 | AI returns a suggested score + justification per dimension; saved to `rubric_scores.ai_suggested_score` | Must |
| FR-12 | Teacher reviews AI scores and confirms, adjusts, or overrides each; `final_score` is only set by teacher action | Must |
| FR-13 | Teacher cannot view conversations for students who have not consented | Must (enforced by API) |
| FR-14 | Dashboard shows a consent status indicator per student | Must |
| FR-15 | Teacher can filter/search students by name, project, consent status | Should |
| FR-16 | Dashboard is read-only — no teacher can modify student conversation or git data | Must |
| FR-17 | Teacher can export final rubric scores for a project to CSV (student name, email, per-dimension scores, total, annotations) | Must |
| FR-18 | Teacher can toggle a personal flag on any timeline entry; flags are per-teacher, not visible to others | Should |

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

As a teacher, I want AI to pre-score students against my rubric criteria
so that I can review and adjust rather than grade from scratch.

As a teacher, I want to be blocked from viewing a student's conversations if they haven't consented
so that I never inadvertently access unconsented data.
```

## 6. Grading Rubric

### Structure

Rubrics are **per-project**. When a teacher creates a project, they define the rubric dimensions. The platform provides **prefilled mandatory dimensions** that cannot be removed, plus teachers can add custom dimensions.

**Mandatory dimensions (prefilled, always present):**

| Dimension | What is Evaluated | Data Source |
|---|---|---|
| **Prompt quality** | Clarity, specificity, context given in prompts | Conversation logs |
| **Problem decomposition** | Whether student breaks problems into small asks | Conversation logs + commit patterns |
| **Context management** | Appropriate use of new conversations to prevent bloat | Conversation boundaries |
| **Spec-driven approach** | Evidence of writing specs before asking for code | Conversation logs + Git file history |
| **Commit granularity** | Small, logical commits with clear messages | Git events |
| **Branching strategy** | Feature branches, meaningful names, PR usage | Git events |
| **PR quality** | PR descriptions, review engagement | Git events |

**Custom dimensions:** Teacher can add project-specific dimensions (e.g. "understanding of REST APIs", "correct use of error handling"). Each custom dimension includes a name, description, and scoring criteria written by the teacher — this criteria is what the AI uses to score.

Each dimension has:
- A **name** and **description**
- A **scoring criteria** (free text written by teacher — fed to AI for auto-scoring)
- A **max score** (configurable per dimension, default 5)
- An **is_mandatory** flag (true for platform defaults)

### AI-Assisted Scoring

The platform uses AI to pre-score each student against the rubric after the project deadline. The teacher reviews and may override any AI-generated score.

**Scoring flow:**
```
Teacher triggers "AI Grade" for a student project (or bulk for whole class)
  → Platform assembles grading context:
      - Full conversation logs (all messages, conversation boundaries)
      - Git events (commits, branches, PRs, force-pushes, timestamps)
      - Each rubric dimension's name + scoring criteria
  → Sends to AI (via the same thin proxy, using a platform-level API key)
  → AI returns a score + justification per dimension
  → Scores saved as ai_suggested_score in rubric_scores table
  → Teacher sees AI scores with justifications on the rubric page
  → Teacher can accept, adjust, or override each score
  → Final score is teacher-confirmed
```

**Important:** AI scores are suggestions only. The teacher's confirmed score is the grade of record.

### Data Schema

#### `rubric_dimensions` table

```sql
CREATE TABLE rubric_dimensions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id),
    name            TEXT NOT NULL,
    description     TEXT NOT NULL,
    scoring_criteria TEXT NOT NULL,  -- teacher-written criteria fed to AI for scoring
    max_score       SMALLINT NOT NULL DEFAULT 5,
    is_mandatory    BOOLEAN NOT NULL DEFAULT false,
    display_order   SMALLINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### `rubric_scores` table

```sql
CREATE TABLE rubric_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dimension_id        UUID NOT NULL REFERENCES rubric_dimensions(id),
    teacher_id          UUID NOT NULL REFERENCES users(id),
    student_id          UUID NOT NULL REFERENCES users(id),
    project_id          UUID NOT NULL REFERENCES projects(id),
    ai_suggested_score  SMALLINT,           -- NULL until AI grading runs
    ai_justification    TEXT,               -- AI's reasoning for the suggested score
    final_score         SMALLINT,           -- NULL until teacher confirms
    teacher_annotation  TEXT,
    ai_graded_at        TIMESTAMPTZ,
    teacher_confirmed_at TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (dimension_id, student_id, project_id)
);
```

## 7. Dashboard Page Structure

```
/dashboard                          → Course/student list
/dashboard/courses/{course_id}      → Students in course
/dashboard/students/{student_id}/projects/{project_id}
  ├── /timeline                     → Unified activity timeline (primary view)
  ├── /rubric                       → Rubric scoring form
  └── /git                          → Git summary + Gitea deep links
```

## 8. Unified Activity Timeline (Primary View)

The timeline is the main grading surface. It merges conversation messages and git events into a single chronological feed, so teachers can see exactly what the student did and said in the order it happened.

### Timeline Entry Types

| Type | Source | Display |
|---|---|---|
| `conversation_start` | New `conversation_id` | Divider: `— New conversation · {timestamp} · {model} —` |
| `user_message` | `conversation_messages` (role=user) | Student prompt bubble with timestamp and token count |
| `assistant_message` | `conversation_messages` (role=assistant) | AI response bubble with token count and context usage % at time of message |
| `git_commit` | `git_events` (push) | Commit card: SHA (links to Gitea), message, branch, timestamp |
| `git_branch` | `git_events` (branch_create) | Branch card: branch name, timestamp |
| `git_pr_open` | `git_events` (pr_open) | PR card: title, description preview, link to Gitea PR |
| `git_pr_merge` | `git_events` (pr_merge) | PR merge card: title, timestamp |
| `git_force_push` | `git_events` (push, forced=true) | Force-push warning card: branch, timestamp |

### Teacher Comments on Timeline

- Teachers can leave a comment on **any timeline entry** (a message, a commit, a conversation boundary)
- Comments are stored in a `timeline_comments` table (see schema below)
- Comments are visible only to teachers and admins — not to students in v1
- Comments are not part of the rubric; they are free-form annotations for reference during grading

### `timeline_comments` table

```sql
CREATE TABLE timeline_comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL REFERENCES users(id),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    entry_type      TEXT NOT NULL,   -- 'conversation_message', 'git_commit', 'conversation_start', etc.
    entry_id        TEXT NOT NULL,   -- UUID of the referenced row (message id, git_event id, conversation id)
    comment         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_timeline_comments_project ON timeline_comments (student_id, project_id);
```

#### `timeline_flags` table

```sql
CREATE TABLE timeline_flags (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id  UUID NOT NULL REFERENCES users(id),
    student_id  UUID NOT NULL REFERENCES users(id),
    project_id  UUID NOT NULL REFERENCES projects(id),
    entry_type  TEXT NOT NULL,
    entry_id    TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (teacher_id, entry_type, entry_id)  -- one flag per teacher per entry
);

CREATE INDEX idx_timeline_flags_teacher_project ON timeline_flags (teacher_id, student_id, project_id);
```

## 9. Git Summary View

A secondary view with aggregate stats and direct Gitea links:

- Summary cards: total commits, branches created, PRs opened, PRs merged, force-push count
- Commit list: SHA (truncated, links to Gitea), message, branch, timestamp
- Branch list: name, created at, links to Gitea branch view
- PR list: title, state, description preview, links to Gitea PR page
- All Gitea links open in a new tab; Gitea is read-only for teachers

## 10. Design Notes

- See `design/teacher-dashboard-design.md` (to be written after spec approval)
- All data is fetched from the platform backend API — the dashboard never queries PostgreSQL or Gitea directly
- Gitea links are deep links into the self-hosted Gitea instance; teachers must have a Gitea account (provisioned by admin)

## 11. Acceptance Criteria

- [ ] Teacher sees a single unified timeline with conversation messages and git events interleaved by timestamp
- [ ] Conversation boundaries (new `conversation_id`) are visually distinct dividers in the timeline
- [ ] Git commits, branch creates, PRs, and force-pushes appear as distinct cards in the timeline
- [ ] Teacher can click any timeline entry and leave a comment; comment persists on page reload
- [ ] Teacher sees "No consent on file" and no timeline data for unconsented students
- [ ] Git summary view shows correct commit/branch/PR counts matching Gitea
- [ ] Rubric page shows mandatory dimensions prefilled and teacher's custom dimensions per project
- [ ] AI grading runs and populates `ai_suggested_score` + `ai_justification` for all dimensions
- [ ] Teacher can confirm, adjust, or override any AI score; only confirmed scores count as final
- [ ] Bulk AI grading triggers scoring for all consented students in a project in one action
- [ ] Timeline loads within 2 seconds for a student with 500 messages + 100 git events
- [ ] A user with `student` role cannot access any dashboard route

## 12. Open Questions

- Rubric dimensions are per-project. Platform provides mandatory prefilled dimensions; teacher adds custom ones with scoring criteria. AI uses the scoring criteria to suggest scores. Teacher confirms all final scores.
- Teachers can export final rubric scores to CSV per project for upload to external LMS (Canvas, Moodle, etc.). Export includes: student name, email, dimension scores, final total, teacher annotations.
- Teachers can flag any timeline entry as a personal marker (stored per teacher, not visible to other teachers or students). Flags are togglable and used for reference during grading.
- [ ] Do admins need a separate view to see all teachers' rubric scores across a course?

## 13. References

- `specs/conversation-logging.md` — source of conversation data displayed here
- `specs/git-integration.md` — source of Git activity data displayed here
- `specs/auth-and-consent.md` — consent status check enforced before data is shown
