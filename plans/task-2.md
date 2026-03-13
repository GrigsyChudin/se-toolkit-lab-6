# Task 2 Implementation Plan: The Documentation Agent

## Goal
Update `agent.py` to include an agentic loop and two tools (`read_file`, `list_files`) to allow the agent to read project documentation.

## Tools Implementation
- **`list_files(path: str)`**:
  - Uses `os.listdir` or `os.walk`.
  - Returns a string listing files in the given directory.
  - Security: Ensure `path` is within the project root (no `..`).
- **`read_file(path: str)`**:
  - Uses `open().read()`.
  - Returns file content or error message.
  - Security: Ensure `path` is within the project root (no `..`).

## Agentic Loop
- Max 10 iterations.
- Message history will store `system`, `user`, `assistant` (with `tool_calls`), and `tool` messages.
- If LLM returns `tool_calls`, execute them and append to history, then call LLM again.
- If LLM returns a final answer (no `tool_calls`), stop and return JSON.

## System Prompt
- Instruct the LLM to use `list_files` to find relevant documentation in `wiki/`.
- Instruct the LLM to use `read_file` to get the content.
- Require the LLM to provide a `source` reference in the format `file_path#section-anchor`.
- The final answer should be a JSON-like string that we can parse or a specific format that the assistant uses.
- Actually, the task says: "Your system prompt should tell the LLM to use list_files to discover wiki files, then read_file to find the answer, and include the source reference (file path + section anchor)."
- I will use OpenAI function calling. The final answer will still be in the `content` of the assistant's message.

## Updated `agent.py` Structure
- Add `tools` list with function schemas.
- Implement a loop that handles `tool_calls`.
- Record all `tool_calls` in the final `AgentResponse`.
- Extract `source` from the LLM's final response using a regex or by asking for a specific format.

## Security
- `abspath` validation to ensure no path traversal outside the current directory.

## Verification
- Manual test with "How do you resolve a merge conflict?".
- Manual test with "What files are in the wiki?".
- Add 2 regression tests in `tests/test_agent.py`.
- Update `AGENT.md`.
