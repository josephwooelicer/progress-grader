# Design: AI Proxy (Thin Custom Proxy)

**Spec:** [specs/ai-proxy.md](../specs/ai-proxy.md)
**Status:** Draft
**Author:** —
**Date:** 2026-03-26

---

## 1. Summary

A thin FastAPI service (~200 lines of application logic) that sits between the VS Code extension and upstream AI providers. It enforces auth, checks consent, resolves model config, streams responses, tracks context usage, and logs every exchange to PostgreSQL — without buffering the stream.

The same proxy is used by both students (via the VS Code extension) and the platform itself (for AI-assisted rubric grading).

---

## 2. Component Overview

```
VS Code Extension ──► POST /v1/chat ──► AI Proxy (FastAPI)
                                              │
                              ┌───────────────┼────────────────┐
                              │               │                │
                         Auth check    Consent check    Model resolution
                              │               │                │
                              └───────────────┴────────────────┘
                                              │
                                    Provider Adapter
                                              │
                          ┌───────────────────┼──────────────────┐
                          │                   │                  │
                       OpenAI            Anthropic          Ollama / Azure
                          │
                    SSE stream back ──► Extension
                          │
                    AsyncBackgroundTask
                          │
                    PostgreSQL (conversation_messages)
```

---

## 3. File Structure

```
proxy/
  main.py               # FastAPI app, single POST /v1/chat route
  auth.py               # JWT validation, extract student_id + project_id
  consent.py            # DB lookup: active consent for (student_id, project_id)
  model_resolver.py     # Resolution order: student → project → platform default
  context_tracker.py    # Token accumulation and context_usage_pct calculation
  logger.py             # Async write to conversation_messages
  providers/
    __init__.py         # Provider registry (PROVIDER env var → adapter)
    openai.py
    anthropic.py
    azure.py
    ollama.py
```

Total: ~200–250 lines of application logic across all files.

---

## 4. Request Flow (detailed)

```python
POST /v1/chat
  Authorization: Bearer <jwt>
  Body: { conversation_id, messages, stream: true }

1. auth.verify_jwt(token)
     → decode JWT with JWT_SECRET
     → extract student_id, project_id
     → 401 if invalid/expired

2. consent.check(student_id, project_id, db)
     → SELECT FROM consents WHERE student_id=? AND project_id=? AND revoked_at IS NULL
     → 403 if no active record

3. context_tracker.check_limit(conversation_id, messages, model, db)
     → calculate total tokens in conversation (sum of input_tokens for this conversation_id)
     → if >= model context window: return 429 with context_limit_reached

4. model_resolver.resolve(student_id, project_id, db)
     → check student_project_settings for (student_id, project_id)
     → fallback to projects table for project_id
     → fallback to env vars DEFAULT_PROVIDER / DEFAULT_MODEL / DEFAULT_API_KEY

5. provider = providers.get(resolved.provider)
   stream = provider.stream_chat(messages, resolved.model, resolved.api_key)

6. async def generate():
       accumulated = []
       token_count = 0
       async for chunk in stream:
           token_count += len(chunk)  # approximate; replaced with provider token count at end
           pct = context_tracker.pct(conversation_id, token_count, model)
           yield f"data: {json.dumps({'delta': chunk, 'context_usage_pct': pct})}\n\n"
           accumulated.append(chunk)
       yield "data: [DONE]\n\n"
       # fire-and-forget log write
       background_tasks.add_task(
           logger.write, student_id, project_id, conversation_id,
           messages, "".join(accumulated), resolved.model
       )

7. return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 5. Provider Adapter Interface

Each provider module implements one async generator function:

```python
async def stream_chat(
    messages: list[dict],   # [{"role": "user"|"assistant", "content": str}]
    model: str,
    api_key: str,
    base_url: str | None = None,
) -> AsyncIterator[str]:
    """Yield text chunks as they arrive from the provider."""
    ...
```

Provider is selected via the `PROVIDER` env var (platform default) or resolved per-request. Adding a new provider = adding one file implementing this interface.

---

## 6. Context Tracking

Context window size per model is stored in a static registry (updated as models change):

```python
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o":              128_000,
    "gpt-4o-mini":          128_000,
    "claude-opus-4-6":     200_000,
    "claude-sonnet-4-6":   200_000,
    "llama3":               8_000,
    # ...
}
```

`context_usage_pct` calculation:
```python
def pct(conversation_id, new_tokens, model, db):
    prior_tokens = db.query(
        "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) "
        "FROM conversation_messages WHERE conversation_id = ?",
        conversation_id
    )
    total = prior_tokens + new_tokens
    window = MODEL_CONTEXT_WINDOWS.get(model, 8_000)
    return min(100, int(total / window * 100))
```

---

## 7. Dual Use: Student vs Platform Grading

The proxy handles two caller types:

| Caller | Auth | Purpose |
|---|---|---|
| VS Code extension | Student JWT | Student ↔ AI conversation |
| Platform backend (grading) | Platform service token | AI-assisted rubric scoring |

Platform grading calls use a service JWT (role: `platform`) that bypasses the consent check (platform is grading its own data) and uses the platform-level API key regardless of project config.

---

## 8. Encryption of Student API Keys

Student-supplied API keys are encrypted at rest using AES-256-GCM via the `cryptography` library:

```python
from cryptography.fernet import Fernet
fernet = Fernet(os.environ["ENCRYPTION_KEY"])

# Store
encrypted = fernet.encrypt(raw_api_key.encode()).decode()

# Retrieve
raw = fernet.decrypt(encrypted.encode()).decode()
```

`ENCRYPTION_KEY` is a base64-encoded 32-byte key, stored as an env var / secret. Never logged.

---

## 9. Trade-offs

| Decision | Alternative | Why chosen |
|---|---|---|
| Single `/v1/chat` endpoint | OpenAI-compatible `/v1/chat/completions` | Simpler; extension is custom so no need for OpenAI wire format compatibility |
| Background task for logging | Synchronous log before stream | Doesn't block stream start; acceptable risk of log loss on crash (best-effort) |
| Static context window registry | Query provider API | Avoids extra API call per request; updated manually when models change |
| Fernet encryption for student keys | KMS (AWS/GCP) | Self-hosted; no external key management dependency in v1 |

---

## 10. Open Questions

None — all spec questions resolved.
