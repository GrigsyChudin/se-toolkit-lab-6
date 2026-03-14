# Task 3 Implementation Plan: The System Agent

## Goal
Update `agent.py` to include the `query_api` tool, allowing the agent to interact with the deployed backend. The agent should be able to answer static system facts and data-dependent queries.

## New Tool: `query_api`
- **Functionality:** Sends HTTP requests to the backend API.
- **Parameters:**
  - `method`: HTTP method (GET, POST, etc.).
  - `path`: API endpoint path (e.g., `/items/`).
  - `body`: Optional JSON request body.
- **Implementation:**
  - Use `httpx` to send requests.
  - Base URL from `AGENT_API_BASE_URL` (default: `http://localhost:42002`).
  - Authentication: Add `Authorization: Bearer <LMS_API_KEY>` header.
  - Load `LMS_API_KEY` from environment (originally in `.env.docker.secret`).

## Environment Variables
Ensure all configuration is loaded from environment variables:
- `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL` (from `.env.agent.secret`).
- `LMS_API_KEY` (from `.env.docker.secret`).
- `AGENT_API_BASE_URL` (default: `http://localhost:42002`).

## System Prompt Updates
- Inform the LLM about the `query_api` tool.
- Instruct the LLM on when to use `wiki` tools vs. `query_api`.
- For questions about the system (framework, ports, database content), prioritize `query_api` or reading source code.

## Iteration Strategy & Benchmark Results
1. **Initial Implementation:** `query_api` and environment variable loading implemented.
2. **Local Evaluation:**
   - Ran `uv run run_eval.py`.
   - Encountered 401 Unauthorized errors in `run_eval.py` due to missing autochecker credentials.
   - Verified the agent manually for system and data queries:
     - `What Python web framework does this project use?` -> Correctly uses `read_file` to find FastAPI.
     - `How many items are in the database?` -> Correctly uses `query_api` and reports 0 items.
3. **Refinement:** Updated system prompt to improve structured output (JSON enforcement) and retry for missing `source` field.

## Hidden Evaluation Diagnosis
After initial submission, the agent passed 3/5 hidden questions (60%). Two failures were identified and addressed:

### Failure 1: Learner Count (Question 14)
- **Issue:** The agent failed to correctly count distinct learners.
- **Root Cause:** The agent was not explicitly instructed to query the list endpoint and count the results in the JSON response.
- **Fix:** Updated the `SYSTEM_PROMPT` to include a rule for data counting: "If asked for a total count of items (e.g., learners, scores), query the relevant endpoint and count the entries in the returned JSON list."

### Failure 2: Analytics Bug (Question 16)
- **Issue:** The agent failed to identify the specific operation causing a crash in `/analytics/completion-rate`.
- **Root Cause:** The agent's bug-finding heuristic was too general. It didn't specifically look for common risky operations in Python.
- **Diagnosis:** Reading `backend/app/routers/analytics.py` revealed a potential `ZeroDivisionError` on line 219: `rate = (passed_learners / total_learners) * 100`. This happens if `total_learners` is 0 (no data).
- **Fix:** Updated the `SYSTEM_PROMPT` to instruct the agent to "pay close attention to risky operations: division (potential ZeroDivisionError), sorting with `None` values, or list indexing without length checks" when investigating bugs.

## Verification
- [x] Run local benchmark: `uv run run_eval.py` (partially verified, 6/10 passing on accessible questions).
- [x] Add 2 regression tests in `tests/test_agent.py`: `test_agent_framework_info` and `test_agent_item_count`.
- [x] Update `AGENT.md`.
- [x] Improve `SYSTEM_PROMPT` for bug diagnosis and data counting.
