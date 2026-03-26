# Spec: Authentication and Consent

**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Overview

This spec defines how users (students, teachers, admins) authenticate to the platform, how roles are enforced, and how student consent to conversation logging is obtained, recorded, and enforced across the system. Consent is the legal and ethical foundation of the grading model — no grading data is accessible without it.

## 2. Goals

- Provide secure, role-based authentication for students, teachers, and admins
- Support school SSO (SAML/OIDC) via Keycloak, with a fallback to email/password for institutions without SSO
- Obtain and record explicit student consent before any AI conversation is logged or made visible to teachers
- Enforce consent at the API layer — not just the UI — so it cannot be bypassed

## 3. Non-Goals

- Building a custom identity provider (Keycloak handles this)
- Per-session consent (consent is one-time per student per platform)
- MFA in v1 (delegated to the institution's SSO provider)
- Student-initiated consent revocation in the UI (can be done by admin; policy decision)

## 4. Requirements

### Functional Requirements

| ID   | Requirement | Priority |
|------|-------------|----------|
| FR-1 | Platform supports three roles: `student`, `teacher`, `admin` | Must |
| FR-2 | Authentication is handled by Keycloak (OIDC); platform issues its own short-lived JWT after Keycloak login | Must |
| FR-3 | Email/password login is available as a fallback for institutions without SSO | Should |
| FR-4 | On first login, students are shown a blocking consent modal before accessing any workspace | Must |
| FR-5 | The consent modal displays the exact wording of what will be collected and who can view it | Must |
| FR-6 | Consent is only recorded after the student actively clicks "I Agree" — pre-ticked boxes are not permitted | Must |
| FR-7 | The consent record stores: student_id, timestamp, IP address, exact consent wording shown | Must |
| FR-8 | A student who has not consented cannot open any workspace | Must |
| FR-9 | The AI proxy rejects requests from students without an active consent record (403) | Must |
| FR-10 | Teacher API endpoints reject requests for students without active consent (403) | Must |
| FR-11 | Admins can view and manage consent records | Must |
| FR-12 | Teachers can see a consent status badge per student in the dashboard | Must |
| FR-13 | Role assignment is managed in Keycloak (or by admin in the platform for non-SSO setups) | Must |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | JWTs expire after 1 hour; refresh tokens valid for 8 hours (one school day) | Must |
| NFR-2 | All auth endpoints use HTTPS | Must |
| NFR-3 | Consent check adds < 5ms to API response time (single indexed DB lookup) | Must |

## 5. User Stories

```
As a student, I want to see exactly what data will be collected and who can see it
so that I can make an informed decision before agreeing.

As a student, I want to only agree once for the whole platform
so that I'm not interrupted on every login.

As a teacher, I want to know at a glance which students have consented
so that I understand which students' data I can review.

As an admin, I want to manage user roles and consent records
so that I can resolve disputes or onboard new users.

As a platform, I want to reject all data access requests for unconsented students
so that consent enforcement is not dependent on UI-level guards.
```

## 6. Authentication Flow

### Student login (SSO path)

```
Student visits platform
  → Redirected to Keycloak
  → Keycloak authenticates via school SAML/OIDC
  → Keycloak returns OIDC token to platform
  → Platform validates token, resolves/creates user record
  → Platform issues signed JWT (role: student, student_id, exp: +1h)
  → Check consent record:
      → No record → show blocking consent modal
      → Record exists → proceed to workspace selector
```

### Student login (email/password fallback)

```
Student submits email + password
  → Platform validates against local credentials (Keycloak local user)
  → Same flow from "Platform issues signed JWT" above
```

### Consent modal flow

```
Blocking modal shown (cannot be dismissed without action):
  "This platform records your conversations with the AI assistant
   for the purpose of academic assessment by your teacher.
   Your teacher [name] can view your full conversation history
   for project [project name]. You may not revoke this consent
   once the project has begun.
   [I Agree] [I Do Not Agree — Exit]"

Student clicks "I Agree":
  → POST /consent with student_id, agreement_text, ip_address
  → consent record written to DB
  → Student proceeds to platform

Student clicks "I Do Not Agree":
  → Session terminated, student redirected to exit page
  → No workspace is created
```

## 7. Role Permissions Matrix

| Action | student | teacher | admin |
|---|---|---|---|
| Open own workspace | ✓ | — | ✓ |
| View own conversations | ✓ (future v2) | — | ✓ |
| View student conversations | — | ✓ (consented only) | ✓ |
| Submit rubric scores | — | ✓ | ✓ |
| Pause/destroy any workspace | — | ✓ | ✓ |
| Manage users and roles | — | — | ✓ |
| View consent records | — | Status only | ✓ (full) |
| Configure AI provider | — | — | ✓ |

## 8. JWT Structure

```json
{
  "sub": "uuid-student-id",
  "role": "student",
  "email": "student@school.edu",
  "name": "Student Name",
  "consented": true,
  "iat": 1700000000,
  "exp": 1700003600
}
```

- `consented` is embedded in the JWT so the proxy can check it without a DB call
- If consent is revoked, the JWT must be invalidated (via a blocklist or by waiting for expiry — policy decision)

## 9. Data Schema

### `users` table

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'admin')),
    keycloak_id TEXT UNIQUE,   -- NULL for local-only users
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `consents` table

*(defined in `specs/conversation-logging.md` — reproduced here for reference)*

```sql
CREATE TABLE consents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id      UUID NOT NULL REFERENCES users(id),
    agreed_at       TIMESTAMPTZ NOT NULL,
    agreement_text  TEXT NOT NULL,
    ip_address      INET,
    revoked_at      TIMESTAMPTZ
);
```

## 10. Design Notes

- See `design/auth-and-consent-design.md` (to be written after spec approval)
- Keycloak is the authoritative identity source; the platform's `users` table is a local mirror for foreign key integrity
- For small deployments without Keycloak, Better Auth (TypeScript, self-hosted) is an acceptable substitute — swap only the auth adapter

## 11. Acceptance Criteria

- [ ] A new student who logs in for the first time sees the consent modal and cannot dismiss it without choosing an option
- [ ] A student who clicks "I Do Not Agree" has no workspace created and no data logged
- [ ] A student who consents can open a workspace immediately after agreeing
- [ ] The AI proxy returns 403 for a student with no consent record, even with a valid JWT
- [ ] A teacher API call for an unconsented student returns 403
- [ ] JWTs expire after 1 hour; the client can refresh without re-showing the consent modal
- [ ] An admin can view the full consent record including the exact wording the student agreed to

## 12. Open Questions

- [ ] Should consent be per-project (student sees the project name in the modal) or per-platform? Current spec: per-platform, but the modal can reference the course name.
- [ ] What happens mid-project if a student wants to withdraw consent? Current spec: admin-only action, deferred to institutional policy.
- [ ] Should the platform support guardian consent for minors (e.g. students under 18)? Likely needed for secondary schools.
- [ ] Do we need audit logging of admin actions on consent records?

## 13. References

- `specs/conversation-logging.md` — consent check gates all conversation data access
- `specs/ai-proxy.md` — enforces consent before proxying any AI request
- `specs/teacher-dashboard.md` — displays consent status, enforces 403 for unconsented students
- `specs/workspace-lifecycle.md` — workspace creation blocked until consent is recorded
