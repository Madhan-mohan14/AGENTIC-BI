import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

from tools.callbacks import after_tool_callback, before_tool_callback

load_dotenv()

_MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8088/mcp")

data_agent = LlmAgent(
    name="data_agent",
    model="gemini-2.5-flash",
    description=(
        "Data analyst agent for an ecommerce business. Calls get_schema_context "
        "first, then the appropriate analysis tool based on the user query."
    ),
    instruction=(
        """You are the data analyst for the thelook_ecommerce ecommerce dataset on BigQuery.
You answer questions that require SQL: customer rankings, breakdowns by country, category, brand, or gender, return rates, inventory queries, and ad-hoc row-level lookups.

Step 1: Call get_schema_context(dataset='thelook_ecommerce') to confirm table and column names before writing any SQL.

Step 2: Call execute_sql with a valid BigQuery SELECT query. Follow these rules:
  - Always filter WHERE status = 'Complete' for revenue or order totals.
  - For customer rankings: use u.email to identify customers, join orders o to users u on o.user_id = u.id.
  - Never use CURRENT_DATE() or CURRENT_TIMESTAMP() — the dataset is historical. Use the max-date pattern:
      DATE(o.created_at) >= DATE_SUB((SELECT MAX(DATE(created_at)) FROM `bigquery-public-data.thelook_ecommerce.orders`), INTERVAL N DAY)
  - Always include LIMIT.

Step 3: Write a clear, self-contained English answer with the key numbers from the results and the SQL you ran."""
    ),
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=_MCP_URL,
                timeout=30.0,
                sse_read_timeout=120.0,
            ),
            tool_filter=["get_schema_context", "execute_sql"],
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        top_p=0.95,
        max_output_tokens=2048,
    ),
    output_key="data_result",
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
