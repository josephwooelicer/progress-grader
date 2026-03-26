# Spec: AI Proxy (Thin Custom Proxy)

**Status:** Draft
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
| FR-7 | Provider, model name, and API credentials are configured via environment variables — not hardcoded | Must |
| FR-8 | Supported providers in v1: OpenAI, Anthropic, Azure OpenAI, Ollama (local) | Must |
| FR-9 | Adding a new provider requires only a new adapter module — no changes to the core proxy logic | Should |
| FR-10 | Proxy attaches metadata to each log entry: `student_id`, `project_id`, `conversation_id`, `timestamp`, `model`, `input_tokens`, `output_tokens` | Must |

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
data: {"delta": "token text"}
data: {"delta": "more text"}
data: [DONE]
```

### Error responses

| Code | Meaning |
|------|---------|
| 401  | Missing or invalid session token |
| 403  | Student has not given consent (see `specs/auth-and-consent.md`) |
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
  → Forward to provider, open stream
  → Simultaneously:
      - Stream tokens back to extension (SSE)
      - Accumulate full response in memory
  → On stream complete: write log entry to PostgreSQL (async)
```

Log schema is defined in `specs/conversation-logging.md`.

## 9. Configuration (Environment Variables)

| Variable | Description | Example |
|---|---|---|
| `PROVIDER` | Active provider module | `openai`, `anthropic`, `azure`, `ollama` |
| `MODEL` | Model name to use | `gpt-4o`, `claude-opus-4-6` |
| `PROVIDER_API_KEY` | API key for the provider | `sk-...` |
| `PROVIDER_BASE_URL` | Base URL (for Azure/Ollama) | `http://ollama:11434` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://...` |
| `JWT_SECRET` | Secret for validating session tokens | — |

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

## 12. Open Questions

- [ ] Should `conversation_id` be generated by the extension or the proxy? (Currently: extension, so the student controls conversation boundaries — which is a grading signal)
- [ ] Do we want per-student model configuration (teacher assigns a model to a class), or is it global per deployment?
- [ ] Should the proxy enforce a maximum context window size to prevent runaway token usage?

## 13. References

- `specs/conversation-logging.md` — log schema written by this proxy
- `specs/auth-and-consent.md` — consent check enforced before proxying
- `specs/workspace-lifecycle.md` — proxy endpoint configured in each workspace container's extension settings
