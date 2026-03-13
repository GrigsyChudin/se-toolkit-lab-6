# Agent Documentation

This document describes the architecture and usage of the agent built for Lab 6.

## Overview
The agent is a CLI tool (`agent.py`) that interacts with an LLM using an OpenAI-compatible API. It takes a natural language question as input and returns a structured JSON response.

## Architecture
- **Language:** Python 3.14.2
- **Frameworks:**
  - `openai`: Client for communicating with the LLM API.
  - `pydantic`: For structured data validation and JSON serialization.
  - `pydantic-settings`: For managing environment variables and secrets.
- **LLM Provider:** Qwen Code API (OpenAI-compatible) deployed on a remote VM.
- **Model:** `qwen3-coder-plus` (Qwen 3 Coder Plus).

## Configuration
The agent reads its configuration from `.env.agent.secret` (ignored by Git) or environment variables:
- `LLM_API_KEY`: API key for the LLM provider.
- `LLM_API_BASE`: Base URL for the LLM API.
- `LLM_MODEL`: The model name to use for chat completions.

## Usage
Run the agent using `uv`:
```bash
uv run agent.py "Your question here"
```

## Output Format
The agent always outputs a single JSON line to stdout:
```json
{
  "answer": "The text answer from the LLM.",
  "tool_calls": []
}
```
All debug information and errors are printed to stderr.
