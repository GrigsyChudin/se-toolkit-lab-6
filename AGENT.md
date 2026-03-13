# Agent Documentation

This document describes the architecture and usage of the agent built for Lab 6.

## Overview
The agent is a CLI tool (`agent.py`) that interacts with an LLM using an OpenAI-compatible API. It is designed to answer questions about the project documentation, source code, and live system state by navigating the repository's file system and querying the backend API.

## Architecture
- **Language:** Python 3.14.2
- **Agentic Loop:** The agent implements a loop (up to 10 iterations) where the LLM can decide to call tools to gather information before providing a final answer.
- **Tools:**
  - `list_files(path)`: Lists entries in a directory relative to the project root.
  - `read_file(path)`: Reads the content of a file relative to the project root.
  - `query_api(method, path, body=None, use_auth=True)`: Sends HTTP requests to the deployed backend API.
- **LLM Provider:** Qwen Code API (OpenAI-compatible) deployed on a remote VM.
- **Model:** `qwen3-coder-plus` (Qwen 3 Coder Plus).

## System Agent Capabilities
With the addition of the `query_api` tool, the agent can now answer:
- **Static system facts:** Identifying frameworks (FastAPI), ports, and status codes by reading source code (e.g., `backend/app/main.py`) or configuration files.
- **Data-dependent queries:** Retrieving live data like item counts, student scores, or analytics directly from the running backend.
- **Bug diagnosis:** Investigating API errors by first querying the endpoint and then reading the corresponding router logic in `backend/app/routers/` to identify the root cause.

## Security & Authentication
- **File System:** Tools are restricted to the project root. Path traversal (e.g., `..`) is blocked.
- **API Authentication:** The `query_api` tool uses the `LMS_API_KEY` from environment variables to authenticate with the backend via a `Bearer` token in the `Authorization` header.

## Configuration
The agent reads its configuration from `.env.agent.secret` and `.env.docker.secret` files or environment variables:
- `LLM_API_KEY`: API key for the LLM provider.
- `LLM_API_BASE`: Base URL for the LLM API.
- `LLM_MODEL`: The model name to use for chat completions.
- `LMS_API_KEY`: Backend API key for `query_api` auth.
- `AGENT_API_BASE_URL`: Base URL for the backend API (default: `http://localhost:42002`).

## Tool Selection Logic
The agent follows a hierarchical strategy for tool selection:
1. **Wiki Tools:** For documentation and general project questions, it prioritizes `list_files` and `read_file` on the `wiki/` directory.
2. **System Tools:** For live data, it uses `query_api`.
3. **Source Code Tools:** For architectural or logic questions, it reads files in `backend/app/`. If an API call fails, it automatically switches to reading source code to diagnose the bug.

## Lessons Learned & Benchmark
The local evaluation benchmark (`run_eval.py`) was instrumental in refining the agent's behavior. Initial challenges included:
- **Missing Source:** The agent sometimes provided answers without the `source` field. A retry mechanism and improved system prompt were added to enforce structured output.
- **Tool Chaining:** For complex questions like "find the bug in /analytics/", the agent learned to first call the API to see the error, and then read the source code.
- **Auth Handling:** Ensuring the `query_api` correctly defaults to using the `LMS_API_KEY` was critical for passing system-level checks.

## Usage
Run the agent using `uv`:
```bash
uv run agent.py "How many items are in the database?"
```

## Output Format
The agent outputs a single JSON line to stdout:
```json
{
  "answer": "The text answer from the LLM.",
  "source": "wiki/some-file.md#section-anchor",
  "tool_calls": [...]
}
```
All logs are directed to stderr.
