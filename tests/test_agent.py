import json
import subprocess
import pytest

def test_agent_cli_structure():
    """
    Test that agent.py returns valid JSON with 'answer' and 'tool_calls' fields.
    """
    question = "What is 2+2?"
    
    # Run agent.py as a subprocess
    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        check=True
    )
    
    # stdout should contain exactly one line of JSON
    stdout_lines = result.stdout.strip().split('\n')
    assert len(stdout_lines) == 1, f"Expected 1 line of output, got: {result.stdout}"
    
    # Parse JSON
    try:
        data = json.loads(stdout_lines[0])
    except json.JSONDecodeError:
        pytest.fail(f"stdout is not valid JSON: {result.stdout}")
        
    # Check required fields
    assert "answer" in data, "Field 'answer' is missing from response"
    assert "tool_calls" in data, "Field 'tool_calls' is missing from response"
    assert isinstance(data["answer"], str), "'answer' should be a string"
    assert isinstance(data["tool_calls"], list), "'tool_calls' should be a list"
    assert len(data["answer"]) > 0, "Answer is empty"
