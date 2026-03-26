# Design: Authentication and Consent

**Spec:** [specs/auth-and-consent.md](../specs/auth-and-consent.md)
**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Summary

Authentication is handled by Keycloak (OIDC) with an email/password fallback. The platform issues its own short-lived JWTs after Keycloak login. Consent is per-project — a student must explicitly agree before their first workspace opens. Consent is permanent once given and enforced at the API layer on every request.

---

## 2. Auth Flow

```
Student visits platform
  │
  ├─► Keycloak login (school SSO / local user)
  │     → OIDC authorization code flow
  │     → Platform callback: POST /auth/callback
  │           → validate OIDC token with Keycloak
  │           → upsert user in users table (keycloak_id, email, name, role)
  │           → issue platform JWT (1h expiry) + refresh token (8h)
  │           → set httpOnly cookie
  │
  └─► Student lands on project selector
        │
        └─► Student clicks a project
              │
              ├─► Check consents table: (student_id, project_id) with revoked_at IS NULL
              │     → consent exists → open workspace
              │
              └─► No consent → show blocking consent modal
                    → student clicks "I Agree"
                    → POST /api/consent { project_id }
                    → INSERT INTO consents (student_id, project_id, agreed_at, agreement_text, ip_address)
                    → workspace opens
```

---

## 3. JWT Structure

```json
{
  "sub":   "uuid-student-id",
  "role":  "student",
  "email": "student@university.edu",
  "name":  "Student Name",
  "iat":   1700000000,
  "exp":   1700003600
}
```

- Signed with `JWT_SECRET` (HS256)
- `role` determines API access — not consent (consent is a DB lookup per project)
- Refresh token stored in `refresh_tokens` table; invalidated on logout

---

## 4. Consent Modal Design

Shown as a full-screen blocking modal (cannot be dismissed with Escape or clicking outside):

```
┌─────────────────────────────────────────────────────┐
│  Before you begin: [Project Name]                   │
│                                                     │
│  This platform records your AI conversations for    │
│  academic assessment purposes.                      │
│                                                     │
│  Your teacher [Teacher Name] will be able to view   │
│  your full AI conversation history for this project │
│  to evaluate your thought process and prompting     │
│  strategy.                                          │
│                                                     │
│  By clicking "I Agree":                             │
│  • Your conversations will be logged automatically  │
│  • This consent cannot be revoked once agreed       │
│  • Your data is stored on school infrastructure     │
│                                                     │
│  [I Agree — Open Workspace]  [I Do Not Agree]       │
└─────────────────────────────────────────────────────┘
```

The exact wording shown is stored verbatim in `consents.agreement_text`.

---

## 5. Role Enforcement

All API routes are protected by a role middleware:

```python
# FastAPI dependency
def require_role(*roles):
    def check(jwt: JWT = Depends(verify_jwt)):
        if jwt.role not in roles:
            raise HTTPException(403)
    return check

# Usage
@router.get("/api/teacher/...")
async def teacher_endpoint(_=Depends(require_role("teacher", "admin"))):
    ...
```

| Route prefix | Allowed roles |
|---|---|
| `/api/student/*` | `student`, `admin` |
| `/api/teacher/*` | `teacher`, `admin` |
| `/api/admin/*` | `admin` |
| `/v1/chat` (proxy) | `student`, `platform` (service token) |

---

## 6. Consent Check Middleware

For any route that returns student data, consent is checked after role:

```python
def require_consent(student_id: UUID, project_id: UUID, db: DB):
    row = db.execute(
        "SELECT id FROM consents WHERE student_id=? AND project_id=? AND revoked_at IS NULL",
        student_id, project_id
    ).first()
    if not row:
        raise HTTPException(403, "Student has not consented for this project")
```

This runs in: AI proxy, teacher conversation API, teacher timeline API, student conversation history API.

---

## 7. Database Schema

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('student', 'teacher', 'admin')),
    keycloak_id TEXT UNIQUE,
    gitea_username TEXT UNIQUE,   -- set at account creation for git identity
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ       -- soft delete only
);

CREATE TABLE refresh_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    token_hash  TEXT NOT NULL UNIQUE,  -- bcrypt hash of the token
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ
);

-- consents table defined in conversation-logging-design.md
```

---

## 8. Keycloak vs Better Auth

| | Keycloak | Better Auth |
|---|---|---|
| SSO support | SAML, OIDC, LDAP | OIDC only |
| Self-hosted | Yes | Yes |
| Language | Java (heavy) | TypeScript (light) |
| When to use | School has existing SSO | Fresh deployment, no SSO |

The platform backend abstracts auth behind an `AuthProvider` interface. Switching from Keycloak to Better Auth (or vice versa) requires only swapping the adapter, not changing routes or JWT handling.

---

## 9. Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| Per-project consent | Per-platform one-time | Students see exactly what each teacher will access; more transparent |
| No consent revocation | Self-service revocation | Simplifies grading integrity; stated clearly in consent wording |
| Consent DB lookup per request | Embed consent flag in JWT | JWT can't be per-project; DB lookup with index is fast enough (< 5ms) |
| httpOnly cookie for JWT | localStorage | XSS protection |

---

## 10. Open Questions

None — all spec questions resolved.
