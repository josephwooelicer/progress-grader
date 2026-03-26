# Design: Teacher Dashboard

**Spec:** [specs/teacher-dashboard.md](../specs/teacher-dashboard.md)
**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Summary

A Next.js web application where teachers review student work via a unified activity timeline, apply rubric scores (AI-pre-scored, teacher-confirmed), leave timeline comments and personal flags, and export grades to CSV.

---

## 2. Architecture

```
Teacher browser
  └─► Next.js app (App Router)
        │
        ├─► /api/* (Next.js Route Handlers — thin BFF layer)
        │     └─► Platform Backend API (FastAPI)
        │               ├─► PostgreSQL (conversations, git_events, rubric_scores)
        │               └─► Gitea API (deep link URL generation)
        │
        └─► shadcn/ui components
```

The Next.js app does **not** query PostgreSQL or Gitea directly. All data flows through the platform backend API, which enforces auth and consent.

---

## 3. Page Structure and Routes

```
/                               → redirect to /dashboard
/dashboard                      → course list (teacher's assigned courses)
/dashboard/courses/[courseId]   → student list with consent badges + grading status
/dashboard/students/[studentId]/projects/[projectId]
  /timeline                     → unified activity timeline (default tab)
  /rubric                       → rubric scoring form with AI suggestions
  /git                          → git summary + Gitea deep links
```

---

## 4. Unified Activity Timeline

### Data assembly (platform backend)

```
GET /api/teacher/students/{sid}/projects/{pid}/timeline

1. Consent check → 403 if no consent
2. Fetch conversation_messages ordered by created_at
3. Fetch git_events ordered by created_at
4. Fetch timeline_comments for (teacher_id, student_id, project_id)
5. Fetch timeline_flags for (teacher_id, student_id, project_id)
6. Merge all into single array sorted by timestamp
7. Return typed event array
```

### Timeline event types

```typescript
type TimelineEvent =
  | { type: 'conversation_start'; conversationId: string; timestamp: string; model: string }
  | { type: 'user_message';       messageId: string; content: string; inputTokens: number; contextUsagePct: number; timestamp: string }
  | { type: 'assistant_message';  messageId: string; content: string; outputTokens: number; timestamp: string }
  | { type: 'git_commit';         eventId: string; sha: string; message: string; branch: string; gitea_url: string; forced: boolean; timestamp: string }
  | { type: 'git_branch_create';  eventId: string; branchName: string; timestamp: string }
  | { type: 'git_pr_open';        eventId: string; prNumber: number; title: string; description: string; gitea_url: string; timestamp: string }
  | { type: 'git_pr_merge';       eventId: string; prNumber: number; title: string; gitea_url: string; timestamp: string }
```

Each event carries a `comments: Comment[]` and `flagged: boolean` field resolved from the teacher's own records.

### Component tree

```
<TimelinePage>
  <TimelineFilter />          ← filter by event type, date range
  <TimelineList>
    {events.map(event => (
      <TimelineEntry event={event} key={event.id}>
        <EventCard />          ← renders per type
        <CommentThread />      ← teacher comments on this entry
        <FlagButton />         ← personal marker toggle
      </TimelineEntry>
    ))}
  </TimelineList>
</TimelinePage>
```

---

## 5. Rubric Scoring

### AI grading flow

```
Teacher clicks "Run AI Grading" (per student or bulk)
  │
  ├─► Platform backend assembles grading prompt:
  │     - All conversation messages for this student+project
  │     - All git_events for this student+project
  │     - Each rubric dimension: name + description + scoring_criteria + max_score
  │
  ├─► POST to AI proxy (/v1/chat) with platform service token
  │     - Prompt instructs AI to return JSON: [{dimension_id, score, justification}]
  │
  ├─► Parse response, write to rubric_scores:
  │     ai_suggested_score, ai_justification, ai_graded_at
  │
  └─► Teacher dashboard re-fetches rubric data, shows AI scores with justifications
```

### Rubric page component

```
<RubricPage>
  <AIGradeButton onTrigger={runAIGrading} />
  {dimensions.map(dim => (
    <DimensionRow key={dim.id}>
      <DimensionName />
      <DimensionCriteria />         ← collapsible
      <AIScore score={dim.ai_suggested_score} justification={dim.ai_justification} />
      <ScoreInput                   ← number input, 1–max_score
          defaultValue={dim.ai_suggested_score}
          onChange={setFinalScore}
      />
      <AnnotationInput />
      <ConfirmButton />
    </DimensionRow>
  ))}
  <TotalScore />
  <ExportCSVButton />
</RubricPage>
```

---

## 6. CSV Export

```
GET /api/teacher/projects/{projectId}/rubric/export.csv

Columns:
  student_name, student_email,
  [one column per rubric dimension (name)],
  total_score, max_possible_score,
  teacher_annotations (concatenated)

Only rows where final_score IS NOT NULL are included.
```

---

## 7. Timeline Comments and Flags

### Comment creation

```
POST /api/teacher/timeline/comments
Body: { student_id, project_id, entry_type, entry_id, comment }
  → INSERT INTO timeline_comments
```

### Flag toggle

```
POST /api/teacher/timeline/flags/toggle
Body: { student_id, project_id, entry_type, entry_id }
  → INSERT ... ON CONFLICT DO DELETE  (toggle behaviour)
```

---

## 8. Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| Next.js App Router + Route Handlers as BFF | Direct DB queries from frontend | Keeps auth + consent enforcement server-side; no DB credentials in browser |
| shadcn/ui | Fully custom UI | Fast to build; unstyled enough to customise; no runtime dependency |
| AI grading via platform backend → proxy | Direct AI call from dashboard | Consistent logging; uses same proxy infrastructure |
| Single merged timeline endpoint | Separate endpoints joined on client | Correct ordering guaranteed server-side; simpler client code |

---

## 9. Open Questions

None — all spec questions resolved.
