# Task 1 Implementation Plan: Call an LLM from Code

## Goal
Build a CLI `agent.py` that takes a question as an argument, calls an LLM, and outputs a JSON answer.

## LLM Provider
- **Provider:** Qwen Code API (deployed on VM).
- **Model:** `qwen3-coder-plus`.
- **API Base:** `http://92.246.139.186:42005/v1`.
- **Authentication:** `LLM_API_KEY` from `.env.agent.secret`.

## Agent Structure
- **Language:** Python.
- **Dependencies:** `openai`, `pydantic`, `python-dotenv`.
- **Architecture:**
  - `LLMSettings`: Pydantic settings to load config from `.env.agent.secret`.
  - `AgentResponse`: Pydantic model for the structured output.
  - `main()` function:
    - Parse command-line arguments using `sys.argv`.
    - Initialize OpenAI client with base URL and key.
    - Call Chat Completions API.
    - Print the result as a single JSON line to stdout.
    - All other output to stderr.

## Verification
- Run `uv run agent.py "What does REST stand for?"` and check the JSON output.
- Add a regression test in `tests/test_agent.py`.
- Document in `AGENT.md`.
