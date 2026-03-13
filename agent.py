import sys
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import OpenAI

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
    tool_calls: List[dict] = []

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

    try:
        # Call LLM
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
        )

        content = response.choices[0].message.content
        if content is None:
            content = ""

        # Construct AgentResponse
        agent_response = AgentResponse(
            answer=content,
            tool_calls=[]
        )

        # Output JSON to stdout
        print(agent_response.model_dump_json())
        sys.exit(0)

    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
