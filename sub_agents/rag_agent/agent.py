import os
import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

from tools.callbacks import after_tool_callback, before_tool_callback

load_dotenv()

_MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8088/mcp")


def _after_rag_agent(callback_context: CallbackContext) -> None:
    result = callback_context.state.get("rag_result", "")
    status = "FOUND" if result and "ANSWER NOT FOUND" not in result else "ANSWER NOT FOUND"
    print(f"[after_agent] rag_agent - {status}", file=sys.stderr)


rag_agent = LlmAgent(
    name="rag_agent",
    model="gemini-2.5-flash",
    description=(
        "Knowledge retrieval agent. Searches the approved-answer knowledge base "
        "before any expensive BigQuery or analysis operation runs."
    ),
    instruction=(
        """You are the knowledge cache agent. Your only job is to check whether this question has been answered before.

Call search_knowledge_base with the user's exact question.

If the results contain a relevant answer:
  Respond with exactly this format — no other text:
  is_cached=True
  <full answer text from the results>

If the results are empty or not relevant to the question:
  Respond with exactly: ANSWER NOT FOUND

Do not explain, summarise, or add any other text."""
    ),
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=_MCP_URL,
                timeout=30.0,
                sse_read_timeout=60.0,
            ),
            tool_filter=["search_knowledge_base"],
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        top_p=0.95,
        max_output_tokens=1024,
    ),
    output_key="rag_result",
    after_agent_callback=_after_rag_agent,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
