# RAG Service - Test Coverage Summary

## Overview

Comprehensive test suite for the RAG (Retrieval-Augmented Generation) service covering all agentic chat functionality.

## Test File Location

`/Users/dan/dev/waifu_solutions/reicam_server/services/rag/app/test_main.py`

## Test Coverage

### 1. **Health & Public Endpoints** (3 tests)

- ✅ `test_health_endpoint` - Verifies health check returns proper status
- ✅ `test_landing_page_public_access` - Tests both `/` and `/rag` landing pages
- ✅ `test_exception_handlers` - Validates error envelope format

### 2. **Authentication & Authorization** (5 tests)

- ✅ `test_chat_endpoints_require_auth` - Ensures endpoints require valid JWT
- ✅ `test_session_ownership_enforcement` - Users can only access their own sessions
- ✅ `test_inactive_user_rejected` - Inactive users cannot access endpoints
- ✅ `test_expired_token_rejected` - Expired tokens are rejected
- ✅ `test_invalid_token_rejected` - Malformed tokens are rejected

### 3. **Session Management** (5 tests)

- ✅ `test_create_and_list_sessions` - Create sessions and list them
- ✅ `test_create_session_with_auto_title` - Auto-generated titles work
- ✅ `test_get_messages_empty_session` - New sessions have no messages
- ✅ `test_session_pagination` - Pagination with limit/offset works
- ✅ `test_partner_not_found` - Creating session for non-existent partner fails

### 4. **Message Sending & Streaming** (4 tests)

- ✅ `test_send_message_non_streaming` - Non-streaming message flow
- ✅ `test_send_message_streaming` - SSE streaming message flow
- ✅ `test_message_validation` - Empty messages are rejected
- ✅ `test_retrieval_context_integration` - RAG retrieval integration

### 5. **Agentic Features** (3 tests)

- ✅ `test_token_counting_and_memory_creation` - Token counting and memory threshold
- ✅ `test_personality_core_integration` - Partner personality in system prompt
- ✅ `test_retrieval_context_integration` - Context retrieval and sources

## Running the Tests

### Prerequisites

1. Ensure PostgreSQL database is running
2. Set environment variables in `.env` file:

   ```bash
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=waifu_solutions
   JWT_SECRET=your_jwt_secret
   OPENAI_API_KEY=your_openai_key  # or Azure credentials
   ```

### Run All Tests

```bash
cd /Users/dan/dev/waifu_solutions/reicam_server
source ../env/bin/activate  # Activate virtual environment
python -m pytest -v services/rag/app/test_main.py
```

### Run Specific Test

```bash
python -m pytest -v services/rag/app/test_main.py::test_send_message_non_streaming
```

### Run with Coverage

```bash
python -m pytest --cov=services.rag.app --cov-report=html services/rag/app/test_main.py
```

## Test Architecture

### Fixtures

- **`client`** - FastAPI TestClient for RAG service
- **`auth_ctx`** - Authenticated user context (creates real user via Auth service)
- **`partner_ctx`** - Partner context (creates real partner via Partners service)

### Mocking Strategy

- **LLM calls** are mocked using `unittest.mock.patch` to avoid API costs
- **Database** uses real PostgreSQL for integration testing
- **Auth/Partners** services are called via TestClient for realistic integration

### Key Testing Patterns

1. **Session-scoped fixtures** - Reuse user/partner across tests
2. **JWT minting** - Local token generation for auth testing
3. **Mock LLM responses** - Avoid external API calls
4. **Streaming validation** - Test SSE event streams
5. **Error envelope validation** - Consistent error format

## Integration with Other Services

### Dependencies

- **Auth Service** - User creation and authentication
- **Partners Service** - Partner creation for chat sessions
- **Shared Database** - All services use same PostgreSQL instance

### Cross-Service Testing

Tests validate:

- JWT tokens work across services
- Partner ownership is enforced
- Database foreign key constraints work
- Error handling is consistent

## Test Data Cleanup

- Uses unique email generation (`qa.rag.{uuid}@example.com`)
- Session-scoped fixtures minimize database writes
- Tests are idempotent and can run multiple times

## Known Limitations

1. **Memory creation** - Requires high token count, tested with mocks
2. **Streaming** - Full SSE validation limited by TestClient
3. **Vector retrieval** - Mocked as placeholder (TODO: integrate pgvector)

## Next Steps

1. Add vector database integration tests when pgvector is implemented
2. Add performance/load tests for streaming
3. Add tests for concurrent session access
4. Add tests for memory summarization quality
