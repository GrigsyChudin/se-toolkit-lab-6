import sys
import json
import os
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

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
        extra="ignore"
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
]

def execute_tool(name: str, args: Dict[str, Any]) -> str:
    """Execute a tool by name and return its result."""
    if name == "list_files":
        return list_files(args.get("path", "."))
    elif name == "read_file":
        return read_file(args.get("path", ""))
    else:
        return f"Error: unknown tool {name}"

# -----------------------------------------------------------------------------
# Agent logic
# -----------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a documentation assistant. Your goal is to answer questions based ONLY on the project wiki files.

Rules:
1. ALWAYS use `list_files` to discover relevant files in the `wiki/` directory first.
2. ALWAYS use `read_file` to read the contents of relevant files before answering.
3. If the answer is not in the first file you read, CONTINUE searching other relevant files using `read_file`.
4. While you are still searching or plan to call more tools, DO NOT provide a final JSON response. Just call the tools.
5. Once you have found the definitive answer and the source, provide your final response as a JSON object with two fields: "answer" and "source".
   - "answer": A direct, concise and accurate answer based on the information found using tools. If asked to list something, list it.
   - "source": The wiki section reference in the format `file_path#section-anchor` (e.g., `wiki/git.md#merge-conflict`).
6. Do not include any text outside this JSON object in your final answer.
7. If you cannot find the answer after searching all relevant files, state that the information is not available in the wiki in the "answer" field and set "source" to null.
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
            
            # If there are tool calls, execute them
            if assistant_msg.tool_calls:
                # Add assistant message to history
                messages.append(assistant_msg)
                
                for tc in assistant_msg.tool_calls:
                    tool_name = tc.function.name
                    tool_args = json.loads(tc.function.arguments)
                    
                    print(f"Executing tool: {tool_name}({tool_args})", file=sys.stderr)
                    result = execute_tool(tool_name, tool_args)
                    
                    # Record the call
                    all_tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result
                    })
                    
                    # Add tool result to history
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result
                    })
                # Continue the loop to get another response from LLM
                continue
            
            # No tool calls, check if it is a final answer
            content = assistant_msg.content
            if not content:
                content = "{}"

            # Try to parse the final answer JSON
            try:
                clean_content = content.strip()
                if clean_content.startswith("```json"):
                    clean_content = clean_content[7:]
                if clean_content.endswith("```"):
                    clean_content = clean_content[:-3]
                clean_content = clean_content.strip()
                
                final_data = json.loads(clean_content)
                source = final_data.get("source")
                answer = final_data.get("answer", content)
                
                # Ensure answer is a string
                if not isinstance(answer, str):
                    answer = str(answer)

                # If source is missing but LLM seems to want to continue (or just failed to provide source),
                # and we still have steps, let's continue.
                if source is None and _ < 9:
                    print(f"Assistant provided answer without source, continuing: {answer[:50]}...", file=sys.stderr)
                    messages.append(assistant_msg)
                    # Add a nudge
                    messages.append({"role": "user", "content": "You provided an answer without a source. Please use tools to find the exact source in the wiki or state that it cannot be found."})
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
                    continue
                
                agent_response = AgentResponse(
                    answer=content,
                    tool_calls=all_tool_calls
                )

            # Output JSON to stdout
            print(agent_response.model_dump_json())
            sys.exit(0)

        # If we hit the loop limit
        print("Error: Hit maximum tool call limit (10).", file=sys.stderr)
        # Try to return what we have
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
