import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

from tools.callbacks import after_tool_callback, before_tool_callback

load_dotenv()

_MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8088/mcp")


def _before_analysis_model(callback_context: CallbackContext, llm_request):
    for part in (llm_request.contents or []):
        for p in (part.parts or []):
            if hasattr(p, "function_call") and p.function_call:
                print(f"[before_model] analysis_agent -> tool: {p.function_call.name}")
    return None


def _after_analysis_agent(callback_context: CallbackContext) -> None:
    result = callback_context.state.get("analysis_result", "")
    print(f"[after_agent] analysis_agent completed - {len(result)} chars")


analysis_agent = LlmAgent(
    name="analysis_agent",
    model="gemini-2.5-flash",
    description=(
        "Dedicated analysis agent for KPI summaries and anomaly detection. "
        "Call this for: KPI questions (revenue, orders, AOV over a time period), "
        "or anomaly/spike/drop detection in sales data. "
        "Do NOT use for ad-hoc SQL or customer/product breakdowns — use data_agent for those."
    ),
    instruction=(
        """You are the KPI and anomaly analysis agent for the thelook_ecommerce ecommerce dataset.
You answer questions about revenue totals, order counts, AOV, KPI trends, and statistical anomalies using live BigQuery data.

For KPI questions (revenue, order count, AOV, items sold over a period):
  Call generate_kpi_summary with the list of requested metrics and the number of days (default 30).

For anomaly, spike, or drop questions:
  Call detect_anomaly with:
    table — one of: orders, order_items, inventory_items
    column — the relevant numeric column (sale_price for order_items, num_of_item for orders, cost for inventory_items)
    threshold — 2.0

After the tool responds, write a clear business explanation:
  - For KPIs: state exact values, direction and magnitude of change vs prior period, and business significance.
  - For anomalies: if is_anomaly=True report the affected row count and z-score with a business implication; if False confirm the metric is within normal range.

Write your complete answer."""
    ),
    tools=[
        McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=_MCP_URL,
                timeout=30.0,
                sse_read_timeout=120.0,
            )
        )
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        top_p=0.95,
        max_output_tokens=2048,
    ),
    output_key="analysis_result",
    after_agent_callback=_after_analysis_agent,
    before_model_callback=_before_analysis_model,
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
