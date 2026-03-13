import json
import subprocess
import pytest

def run_agent(question: str):
    """Helper to run the agent and parse JSON output."""
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        check=True
    )
    # Filter out stderr lines (like "Executing tool: ...")
    stdout_lines = [line for line in result.stdout.strip().split('\n') if line.startswith('{')]
    assert len(stdout_lines) == 1, f"Expected 1 line of JSON output, got: {result.stdout}"
    return json.loads(stdout_lines[0])

def test_agent_cli_structure():
    """
    Test that agent.py returns valid JSON with 'answer' and 'tool_calls' fields.
    """
    data = run_agent("What is 2+2?")
    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["answer"], str)
    assert isinstance(data["tool_calls"], list)

def test_agent_merge_conflict():
    """
    Test that the agent can answer about merge conflicts using tools.
    """
    data = run_agent("How do you resolve a merge conflict?")
    
    # Check tool calls
    tool_names = [tc["tool"] for tc in data["tool_calls"]]
    assert "list_files" in tool_names
    assert "read_file" in tool_names
    
    # Check source
    assert "source" in data
    assert data["source"] is not None
    assert "wiki/git" in data["source"]
    assert "merge-conflict" in data["source"] or "resolve-a-merge-conflict" in data["source"]

def test_agent_list_wiki():
    """
    Test that the agent can list wiki files.
    """
    data = run_agent("What files are in the wiki?")
    
    # Check tool calls
    tool_names = [tc["tool"] for tc in data["tool_calls"]]
    assert "list_files" in tool_names
    
    # Check answer contains some known wiki files
    assert "git.md" in data["answer"].lower()
    assert "docker.md" in data["answer"].lower()
