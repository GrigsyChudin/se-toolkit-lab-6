import sys
import json
import os
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

class LLMSettings(BaseSettings):
    """LLM connection settings."""
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_api_base: str = Field(alias="LLM_API_BASE")
    llm_model: str = Field(alias="LLM_MODEL")
    lms_api_key: str = Field(alias="LMS_API_KEY")
    agent_api_base_url: str = Field(default="http://localhost:42002", alias="AGENT_API_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=(".env.agent.secret", ".env.docker.secret"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True
    )

class AgentResponse(BaseModel):
    """Structured response from the agent."""
    answer: str
    source: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = []

# -----------------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------------

def safe_path(path: str) -> str:
    """Ensure path is within project root and return absolute path."""
    project_root = os.getcwd()
    abs_path = os.path.abspath(os.path.join(project_root, path))
    if not abs_path.startswith(project_root):
        raise ValueError(f"Path traversal detected: {path}")
    return abs_path

def list_files(path: str) -> str:
    """List files and directories at a given path."""
    try:
        abs_path = safe_path(path)
        if not os.path.isdir(abs_path):
            return f"Error: {path} is not a directory."
        items = os.listdir(abs_path)
        return "\n".join(items)
    except Exception as e:
        return f"Error: {e}"

def read_file(path: str) -> str:
    """Read a file from the project repository."""
    try:
        abs_path = safe_path(path)
        if not os.path.isfile(abs_path):
            return f"Error: {path} is not a file."
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"

def query_api(method: str, path: str, body: Optional[str] = None, settings: Optional[LLMSettings] = None, use_auth: bool = True) -> str:
    """Call the deployed backend API."""
    if settings is None:
        return "Error: Settings not provided to query_api."
    
    url = f"{settings.agent_api_base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {
        "Content-Type": "application/json"
    }
    if use_auth:
        headers["Authorization"] = f"Bearer {settings.lms_api_key}"
    
    try:
        with httpx.Client() as client:
            resp = client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
                timeout=30.0
            )
            return json.dumps({
                "status_code": resp.status_code,
                "body": resp.text
            })
    except Exception as e:
        return f"Error querying API: {e}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative directory path from project root (e.g., 'wiki')."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path from project root (e.g., 'wiki/git.md')."}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the deployed backend API for system facts or data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE)."},
                    "path": {"type": "string", "description": "API endpoint path (e.g., '/items/')."},
                    "body": {"type": "string", "description": "Optional JSON request body."},
                    "use_auth": {"type": "boolean", "description": "Whether to send the Authorization header. Defaults to true. Set to false to test unauthenticated access."}
                },
                "required": ["method", "path"],
            },
        },
    },
]

def execute_tool(name: str, args: Dict[str, Any], settings: LLMSettings) -> str:
    """Execute a tool by name and return its result."""
    if name == "list_files":
        return list_files(args.get("path", "."))
    elif name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "query_api":
        return query_api(
            method=args.get("method", "GET"),
            path=args.get("path", "/"),
            body=args.get("body"),
            settings=settings,
            use_auth=args.get("use_auth", True)
        )
    else:
        return f"Error: unknown tool {name}"

# -----------------------------------------------------------------------------
# Agent logic
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a system and documentation assistant. Your goal is to answer questions using the project wiki files, source code, and the deployed backend API.

Structure:
- `wiki/`: Project documentation.
- `backend/app/`: Backend source code.
- `backend/app/routers/`: API router modules.
- `backend/app/etl.py`: ETL pipeline code.
- `caddy/Caddyfile`: Reverse proxy configuration.
- `Dockerfile`: Container configuration.

Tools:
1. `list_files` & `read_file`: Use these to explore the documentation, source code, and configuration files.
2. `query_api`: Use this to get live data from the system or check system status.

Rules:
1. For documentation questions, use `list_files` and `read_file` on the `wiki/` directory.
2. For system architecture, framework, or code questions, use `list_files` and `read_file` on the `backend/` directory.
3. If an API call fails or behaves unexpectedly, ALWAYS read the corresponding router in `backend/app/routers/` to diagnose the bug.
   - When looking for bugs, pay close attention to risky operations: division (potential ZeroDivisionError), sorting with `None` values, or list indexing without length checks.
4. For live data (counts, scores, analytics), use `query_api`.
   - If asked for a total count of items (e.g., learners, scores), query the relevant endpoint and count the entries in the returned JSON list.
5. While you are still searching or plan to call more tools, DO NOT provide a final JSON response. Just call the tools.
6. Once you have found the definitive answer, provide your final response as a JSON object with two fields: "answer" and "source".
   - "answer": A direct, concise and accurate answer based on the information found.
   - "source": (Optional) The wiki section reference in the format `file_path#section-anchor`.
7. Do not include any text outside this JSON object in your final answer.
8. If you cannot find the answer, state so in the "answer" field.
"""

def main():
    """Main entry point for the agent CLI."""
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"question\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load settings
    try:
        settings = LLMSettings()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize OpenAI client
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    all_tool_calls = []

    try:
        for _ in range(10):  # Limit to 10 iterations
            response = client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.0,
            )

            assistant_msg = response.choices[0].message
            
            # Handle tool calls
            if assistant_msg.tool_calls:
                messages.append(assistant_msg)
                
                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        print(f"Error: failed to parse tool arguments for {tool_name}: {tc.function.arguments}", file=sys.stderr)
                        tool_args = {}
                        result = f"Error: Invalid JSON in tool arguments for {tool_name}. Please provide valid JSON."
                    else:
                        print(f"Executing tool: {tool_name}({tool_args})", file=sys.stderr)
                        result = execute_tool(tool_name, tool_args, settings)
                    
                    # Record the call
                    all_tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })
                continue
            
            # Final answer
            content = assistant_msg.content or "{}"
            print(f"DEBUG: Raw LLM content: {content}", file=sys.stderr)

            try:
                import re
                # Try to find JSON block
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    clean_content = json_match.group(0)
                else:
                    clean_content = content.strip()

                final_data = json.loads(clean_content)
                answer = final_data.get("answer", content)
                source = final_data.get("source")
                if not isinstance(answer, str):
                    answer = str(answer)

                # If it's a documentation/source question (based on tools used), check if source is present
                # but if tools weren't used for wiki/code, maybe source is not needed
                needs_source = any(tc["tool"] in ["read_file", "list_files"] for tc in all_tool_calls)
                
                if needs_source and source is None and _ < 9:
                    print(f"Assistant provided answer without source, continuing: {answer[:50]}...", file=sys.stderr)
                    messages.append(assistant_msg)
                    messages.append({"role": "user", "content": "Your response was missing the 'source' field. Please provide the exact file path and section anchor in JSON format."})
                    continue

                agent_response = AgentResponse(
                    answer=answer,
                    source=source,
                    tool_calls=all_tool_calls
                )
            except json.JSONDecodeError:
                # If not valid JSON, and we still have steps, maybe it's just thinking?
                if _ < 9:
                    print(f"Assistant provided non-JSON content, continuing: {content[:50]}...", file=sys.stderr)
                    messages.append(assistant_msg)
                    # Also, if it looks like an answer but not JSON, nudge it
                    if len(content) > 50:
                         messages.append({"role": "user", "content": "Your response was not in the required JSON format. Please wrap your final answer in JSON: {\"answer\": \"...\", \"source\": \"...\"}"})
                    continue
                
                agent_response = AgentResponse(
                    answer=content,
                    tool_calls=all_tool_calls
                )

            print(agent_response.model_dump_json())
            sys.exit(0)

        print("Error: Hit maximum tool call limit (10).", file=sys.stderr)
        agent_response = AgentResponse(
            answer="Error: Hit maximum tool call limit.",
            tool_calls=all_tool_calls
        )
        print(agent_response.model_dump_json())
        sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
