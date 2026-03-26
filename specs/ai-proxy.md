# Spec: AI Proxy (Thin Custom Proxy)

**Status:** Approved
**Author:** —
**Date:** 2026-03-26

---

## 1. Overview

The AI Proxy is a thin FastAPI service that sits between the VS Code extension (running in each student workspace) and the upstream AI provider APIs (OpenAI, Anthropic, Azure, Ollama, etc.). All AI calls must pass through this proxy — the extension never calls providers directly. The proxy enforces authentication, logs every exchange server-side, and abstracts provider differences behind a single interface.

## 2. Goals

- Intercept and log every student prompt and AI response before it leaves or enters the platform
- Provide a single, stable API surface for the VS Code extension regardless of which AI provider is configured
- Support streaming responses (SSE) so the student sees tokens as they arrive
- Allow admins to configure which AI model/provider is active without changing the extension

## 3. Non-Goals

- Complex routing logic, load balancing, or fallback chains (use a single configured provider per deployment, v1)
- Rate limiting beyond basic per-student request throttling (v2)
- Caching or semantic deduplication of prompts
- Replacing a full gateway product — this is intentionally thin (~150–200 lines of application logic)

## 4. Requirements

### Functional Requirements

| ID   | Requirement | Priority |
|------|-------------|----------|
| FR-1 | Proxy exposes a single endpoint: `POST /v1/chat` | Must |
| FR-2 | Request must include a valid student session token; proxy rejects unauthenticated requests with 401 | Must |
| FR-3 | Proxy resolves `student_id` and `project_id` from the session token before forwarding | Must |
| FR-4 | Proxy forwards the request to the configured upstream provider, translating to the provider's API format | Must |
| FR-5 | Proxy supports streaming responses via Server-Sent Events (SSE) | Must |
| FR-6 | Every request and response is logged to PostgreSQL before the response is returned to the client (see `specs/conversation-logging.md`) | Must |
| FR-7 | Platform-level provider/model defaults are configured via environment variables; per-project overrides are stored in the `projects` table | Must |
| FR-8 | Supported providers in v1: OpenAI, Anthropic, Azure OpenAI, Ollama (local) | Must |
| FR-9 | Adding a new provider requires only a new adapter module — no changes to the core proxy logic | Should |
| FR-10 | Proxy attaches metadata to each log entry: `student_id`, `project_id`, `conversation_id`, `timestamp`, `model`, `input_tokens`, `output_tokens` | Must |
| FR-11 | Students can supply their own API key per project; stored encrypted at rest, never logged or exposed | Must |
| FR-12 | Model resolution order per request: student-supplied key → project config → platform default | Must |
| FR-13 | Every SSE response chunk includes a `context_usage_pct` field (0–100) reflecting cumulative token usage for the current conversation | Must |
| FR-14 | At 100% context usage, the proxy blocks the request and returns 429 with a message instructing the student to start a new conversation | Must |
| FR-15 | The extension displays `context_usage_pct` as a persistent indicator visible at all times during a chat session | Must |

### Non-Functional Requirements

| ID    | Requirement | Target |
|-------|-------------|--------|
| NFR-1 | Proxy added latency (over direct provider call) | < 50ms |
| NFR-2 | Proxy must not buffer the full response before streaming to client | Streaming passthrough |
| NFR-3 | Logging must not block the streaming response — write to DB asynchronously | Must |
| NFR-4 | Proxy runs as a standalone Docker container | Must |

## 5. User Stories

```
As a student, I want my AI responses to stream token-by-token in the IDE
so that I get fast feedback without waiting for the full response.

As a teacher, I want every student prompt and AI response captured automatically
so that I can review them later for grading without relying on the student to submit them.

As an admin, I want to switch the AI provider or model by changing environment variables
so that I can control costs and model access without redeploying the extension.
```

## 6. API Design

### Request

```
POST /v1/chat
Authorization: Bearer <student_session_token>

{
  "conversation_id": "uuid",        // client-generated, groups messages into one session
  "messages": [                     // standard chat messages array
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "stream": true                    // always true in v1
}
```

### Response (SSE stream)

```
data: {"delta": "token text", "context_usage_pct": 42}
data: {"delta": "more text",  "context_usage_pct": 43}
data: [DONE]
```

- `context_usage_pct`: integer 0–100, calculated as `total_tokens_in_conversation / model_context_window * 100`
- The extension renders this as a persistent indicator (e.g. progress bar or % label) visible at all times during the chat session

### Error responses

| Code | Meaning |
|------|---------|
| 401  | Missing or invalid session token |
| 403  | Student has not given consent (see `specs/auth-and-consent.md`) |
| 429  | Context window full (100%) — student must start a new conversation; response body includes `{"error": "context_limit_reached", "message": "You've reached the context limit. Please start a new conversation to continue."}` |
| 502  | Upstream provider error |
| 503  | Proxy misconfigured (no provider set) |

## 7. Provider Abstraction

Each provider is implemented as a Python module with a single async function:

```python
async def stream_chat(messages: list[dict], model: str, api_key: str) -> AsyncIterator[str]:
    ...
```

The proxy selects the active provider module based on the `PROVIDER` environment variable. Adding a new provider = adding one file implementing this interface.

## 8. Logging Flow

```
Extension → POST /v1/chat
  → Auth check (reject if invalid)
  → Consent check (reject if not consented)
  → Resolve student_id, project_id from token
  → Resolve model config:
      1. Student-supplied API key + model (if set for this project)
      2. Project-level config (provider + model + platform key)
      3. Platform default (env vars)
  → Forward to provider, open stream
  → Simultaneously:
      - Stream tokens back to extension (SSE)
      - Accumulate full response in memory
  → On stream complete: write log entry to PostgreSQL (async)
      NOTE: log records model name and token counts — never API keys
```

Log schema is defined in `specs/conversation-logging.md`.

## 9. Configuration (Environment Variables)

**Platform-level defaults (env vars):**

| Variable | Description | Example |
|---|---|---|
| `DEFAULT_PROVIDER` | Fallback provider if no project/student config | `openai` |
| `DEFAULT_MODEL` | Fallback model | `gpt-4o` |
| `DEFAULT_API_KEY` | Platform API key for the default provider | `sk-...` |
| `DEFAULT_BASE_URL` | Base URL for Azure/Ollama | `http://ollama:11434` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Secret for validating session tokens | — |
| `ENCRYPTION_KEY` | Key for encrypting student-supplied API keys at rest | — |

**Per-project config (stored in `projects` table):**
`provider`, `model`, `api_key_encrypted` (nullable — falls back to platform default)

**Per-student per-project config (stored in `student_project_settings` table):**
`provider`, `model`, `api_key_encrypted` (nullable — falls back to project config)

## 10. Design Notes

- See `design/ai-proxy-design.md` (to be written after spec approval)
- The proxy is intentionally thin — no middleware frameworks, no plugin systems. If complexity grows beyond ~300 lines, revisit this spec.

## 11. Acceptance Criteria

- [ ] A valid request from the extension returns a streaming SSE response
- [ ] An unauthenticated request returns 401 and nothing is logged
- [ ] A request from a student who has not consented returns 403
- [ ] Every completed exchange is written to the `conversation_messages` table in PostgreSQL
- [ ] Switching `PROVIDER=anthropic` and restarting the proxy routes subsequent requests to Anthropic without extension changes
- [ ] Proxy latency overhead is < 50ms on a local network
- [ ] The full response is logged even if the student closes the IDE mid-stream (best-effort, log what was accumulated)
- [ ] Every SSE chunk includes a `context_usage_pct` value
- [ ] A request sent when conversation is at 100% returns 429 with `context_limit_reached` error and nothing is forwarded to the provider
- [ ] The extension displays the context usage indicator throughout the chat session

## 12. Open Questions

- `conversation_id` is generated by the extension. The student controls conversation boundaries — this is an explicit grading signal. The proxy never merges or splits conversations.
- Model config is per-project. Each project has a configured provider + model (set by teacher/admin). Students can additionally supply their own API key for their own model — stored encrypted at rest, never logged. Resolution order: student-supplied key → project config → platform default.
- The proxy tracks token usage per conversation and returns a `context_usage_pct` field on every response. The extension displays this as a persistent % indicator at all times. At 100%, the proxy blocks the request and returns a specific error code instructing the student to start a new conversation.

## 13. References

- `specs/conversation-logging.md` — log schema written by this proxy
- `specs/auth-and-consent.md` — consent check enforced before proxying
- `specs/workspace-lifecycle.md` — proxy endpoint configured in each workspace container's extension settings
