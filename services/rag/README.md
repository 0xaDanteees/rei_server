# RAG Service

Agentic Retrieval-Augmented Generation microservice with per-partner chat sessions, streaming responses, and automatic memory summarization to save tokens over time.

## Features

- **Per-partner chat sessions**: Every session is linked to a `partner` owned by the authenticated user.
- **Streaming responses (SSE)**: Real-time token streaming via Server-Sent Events.
- **Automatic memories**: After a configurable token threshold, the service generates a compact memory summary and activates it as primary context for subsequent turns.
- **Personality-aware**: Merges the partner's `personality_core` into the system prompt.
- **Extensible retrieval**: A placeholder `_retrieve_context()` is provided to plug your vector DB (pgvector/FAISS/etc.).

## API

Base path: `/rag`

### Health

- `GET /rag/health` — returns `{ status, db }`.

### Chat Sessions

- `POST /rag/chat/{partner_id}/sessions`
  - Query/body: optional `title`
  - Creates a new chat session for the given partner. Returns `{ id, title, created_at }`.

- `GET /rag/chat/{partner_id}/sessions`
  - Query: `limit`, `offset`
  - Lists sessions for the partner. Returns a list of `{ id, title, total_tokens, created_at, updated_at }`.

- `GET /rag/chat/sessions/{session_id}/messages`
  - Returns ordered messages for a session. Each item: `{ id, role, content, token_count, created_at }`.

- `POST /rag/chat/sessions/{session_id}/message`
  - Body:

    ```jso{n
    { "message": "string", "stream": true }
    ```

  - If `stream=true`, returns SSE stream with events:
    - `token`: incremental token text
    - `sources`: optional list of source URLs (if retrieval is plugged in)
    - `memory`: emitted when a memory summary is created (`"memory_created"`)
    - `done`: end of stream
  - If `stream=false`, returns `{ message, sources }`.

Authentication: Bearer JWT, same secret as other services. The service expects `sub` to be a UUID.

## Models

Tables (created by this service):

- `rag_chat_sessions` (`id`, `user_id`, `partner_id`, `title`, `total_tokens`, timestamps)
- `rag_chat_messages` (`id`, `session_id`, `role`, `content`, `token_count`, `created_at`)
- `rag_chat_memories` (`id`, `session_id`, `summary`, `is_active`, `created_at`)

External reference:

- `partners` table is reflected (read-only) to validate ownership and fetch `personality_core`.

## Environment

See `app/settings.py` for all settings. Key variables:

- `POSTGRES_DSN` or (`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`)
- `CORS_ORIGINS` (default `*`)
- `JWT_SECRET` and optional `JWT_ISSUER`
- `LLM_PROVIDER` = `openai` (default) or `azure`
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL` (default `gpt-4o-mini`)
- Azure: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_DEPLOYMENT`
- Token policy: `TOKEN_MEMORY_THRESHOLD` (default 4000), `MAX_CONTEXT_TOKENS`

## Local Run

Install deps:

```bash
pip install -r requirements.txt
```

Run API:

```bash
uvicorn app.main:app --reload --port 8003
```

Docs: open `http://localhost:8003/rag/docs`.

## Streaming Example

JavaScript (SSE):

```js
const token = "<bearer-token>";
const sessionId = "<uuid>";
const url = `http://localhost:8003/rag/chat/sessions/${sessionId}/message`;

fetch(url, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ message: "Hello", stream: true })
}).then(res => {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  (async function read() {
    const { value, done } = await reader.read();
    if (done) return;
    const chunk = decoder.decode(value);
    console.log(chunk); // parse SSE events
    read();
  })();
});
```

## Integrating Retrieval

Replace `_retrieve_context(query, partner_id)` in `app/routers/chat.py` to call your vector DB and return `(context_text, sources_urls)`.
