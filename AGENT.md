# Agent Documentation

This document describes the architecture and usage of the agent built for Lab 6.

## Overview
The agent is a CLI tool (`agent.py`) that interacts with an LLM using an OpenAI-compatible API. It is designed to answer questions about the project documentation by navigating the repository's file system.

## Architecture
- **Language:** Python 3.14.2
- **Agentic Loop:** The agent implements a loop (up to 10 iterations) where the LLM can decide to call tools to gather information before providing a final answer.
- **Tools:**
  - `list_files(path)`: Lists entries in a directory relative to the project root.
  - `read_file(path)`: Reads the content of a file relative to the project root.
- **LLM Provider:** Qwen Code API (OpenAI-compatible) deployed on a remote VM.
- **Model:** `qwen3-coder-plus` (Qwen 3 Coder Plus).

## Security
Tools are restricted to the project root directory. Path traversal (e.g., using `..`) is detected and blocked.

## Configuration
The agent reads its configuration from `.env.agent.secret` (ignored by Git) or environment variables:
- `LLM_API_KEY`: API key for the LLM provider.
- `LLM_API_BASE`: Base URL for the LLM API.
- `LLM_MODEL`: The model name to use for chat completions.

## Usage
Run the agent using `uv`:
```bash
uv run agent.py "How do you resolve a merge conflict?"
```

## Output Format
The agent outputs a single JSON line to stdout:
```json
{
  "answer": "The text answer from the LLM.",
  "source": "wiki/some-file.md#section-anchor",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "..."
    }
  ]
}
```
All debug information and execution logs are printed to stderr.
