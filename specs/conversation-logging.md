# Spec: Conversation Logging

**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Overview

Every prompt a student sends to the AI and every response the AI returns is logged server-side by the AI proxy. This spec defines the data schema, consent enforcement, conversation boundary semantics, and data access rules that govern how these logs are stored and surfaced to teachers.

## 2. Goals

- Capture a complete, tamper-evident record of student–AI interactions per project
- Enforce student consent before any conversation data is viewable by a teacher
- Preserve conversation boundaries as a grading signal (students choose when to start a new conversation)
- Provide a queryable log that the teacher dashboard can consume

## 3. Non-Goals

- Real-time streaming of conversations to the teacher (teachers review after the fact)
- Storing binary file attachments or images sent to multimodal models (v1: text only)
- Anonymisation or differential privacy (out of scope)
- Log deletion on student request (subject to institutional policy — not implemented in the platform)

## 4. Requirements

### Functional Requirements

| ID   | Requirement | Priority |
|------|-------------|----------|
| FR-1 | Every completed AI exchange is written to the `conversation_messages` table | Must |
| FR-2 | Each message row records: student, project, conversation, role, content, model, token counts, timestamp | Must |
| FR-3 | Conversations are grouped by `conversation_id` (client-generated UUID from the extension) | Must |
| FR-4 | A new `conversation_id` from the extension creates a new conversation — the proxy does not merge conversations | Must |
| FR-5 | No conversation data is exposed via any API unless the student has an active, recorded consent record | Must |
| FR-6 | Consent is recorded once per student per platform (not per project) and stored in the `consents` table | Must |
| FR-7 | A teacher can query all conversations for a given `(student_id, project_id)` pair | Must |
| FR-8 | Each conversation record includes metadata: first message timestamp, last message timestamp, total message count, total tokens | Should |
| FR-9 | Logs are append-only — no UPDATE or DELETE on `conversation_messages` from application code | Must |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | Log write must not block the streaming AI response | Async, fire-and-forget after stream completes |
| NFR-2 | Indexes on `(student_id, project_id)` and `conversation_id` for fast teacher queries | Must |
| NFR-3 | All data stored in PostgreSQL — no external log aggregators in v1 | Must |

## 5. User Stories

```
As a teacher, I want to read the full conversation a student had with the AI
so that I can evaluate their prompt quality and thought process.

As a student, I want to know my conversations are only shared after I explicitly agree
so that I can trust the platform before I start working.

As a teacher, I want to see where a student started a new conversation
so that I can evaluate whether they manage context window size appropriately.

As an admin, I want all log writes to be async
so that logging failures never degrade the student's coding experience.
```

## 6. Data Schema

### `consents` table

```sql
CREATE TABLE consents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    agreed_at       TIMESTAMPTZ NOT NULL,
    agreement_text  TEXT NOT NULL,   -- snapshot of the consent wording at time of agreement
    ip_address      INET,
    revoked_at      TIMESTAMPTZ,     -- NULL = consent active

    UNIQUE (student_id, project_id)
);

CREATE INDEX idx_consents_student_project ON consents (student_id, project_id);
```

### `conversations` table

```sql
CREATE TABLE conversations (
    id              UUID PRIMARY KEY,   -- client-generated, from extension
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    started_at      TIMESTAMPTZ NOT NULL,
    last_message_at TIMESTAMPTZ NOT NULL,
    message_count   INTEGER NOT NULL DEFAULT 0,
    total_tokens    INTEGER NOT NULL DEFAULT 0
);
```

### `conversation_messages` table

```sql
CREATE TABLE conversation_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    student_id      UUID NOT NULL REFERENCES users(id),
    project_id      UUID NOT NULL REFERENCES projects(id),
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conv_msgs_student_project ON conversation_messages (student_id, project_id);
CREATE INDEX idx_conv_msgs_conversation    ON conversation_messages (conversation_id);
```

## 7. Conversation Boundary Semantics

- The VS Code extension generates a `conversation_id` UUID when the student starts a new chat session
- The student controls when to start a new conversation (e.g. closing the chat panel and reopening it, or a manual "New Conversation" button)
- Starting a new conversation when context is getting long is an explicit grading signal — the proxy records it faithfully without merging
- The proxy does NOT infer conversation boundaries — it trusts the `conversation_id` from the extension

## 8. Consent Enforcement

```
Teacher requests conversation data
  → API checks consents table for student_id
  → No active consent record → 403, data not returned
  → Active consent record exists → data returned
```

- Consent is shown to students on first login as a blocking modal (see `specs/auth-and-consent.md`)
- The consent record stores the exact wording shown so disputes can be resolved
- Revoking consent (setting `revoked_at`) does NOT delete historical data — it prevents future access by teachers (institutional policy decision)

## 9. Design Notes

- See `design/conversation-logging-design.md` (to be written after spec approval)
- Log writes use an async background task (FastAPI `BackgroundTasks`) so they don't block the SSE stream
- If a write fails, log the error to application logs — do not surface to the student

## 10. Acceptance Criteria

- [ ] Every completed AI exchange appears in `conversation_messages` within 5 seconds of completion
- [ ] A teacher API call for a student who has not consented returns 403
- [ ] A teacher API call for a consented student returns all messages grouped by `conversation_id`, ordered by `created_at`
- [ ] Two separate `conversation_id` values from the same student in the same project appear as two distinct conversations
- [ ] No `conversation_messages` row is ever updated or deleted via the application API
- [ ] Token counts are present on every message row where the provider returns them

## 11. Open Questions

- Students can view their own conversation history per project within the IDE extension (read-only, self-reflection). This is served by the same API as the teacher view but scoped to the authenticated student's own data only.
- Consent is per-project. A student must consent separately for each project before any conversation data for that project is logged or viewable by the teacher. The consent modal references the specific project and teacher name.
- [ ] What happens to logs if a student's account is deleted? (Institutional policy — defer to admin)
- [ ] Should we store the system prompt sent to the provider, or only the student-authored messages?

## 12. References

- `specs/ai-proxy.md` — writes to this schema on every completed exchange
- `specs/auth-and-consent.md` — consent record referenced here
- `specs/teacher-dashboard.md` — reads from this schema to display conversations
