import os

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.genai import types

load_dotenv()

research_agent = LlmAgent(
    name="research_agent",
    model="gemini-2.5-flash",
    description=(
        "Research agent for explaining WHY business trends happen. "
        "Use for: why revenue dropped, what caused an anomaly, market context, external causes. "
        "Do NOT use for BigQuery data or KPI numbers."
    ),
    instruction=(
        """You are the market research agent. You explain WHY business trends happen using live web search.

Call google_search with a focused, specific query about the business topic in the question.
Include the product category, time period, or metric name to get useful results — avoid broad queries.

Synthesize the search results into a clear explanation:
  - Lead with the most likely primary cause.
  - Include 2-3 supporting factors if the results support them.
  - Be specific — cite numbers, events, or named trends from the results where possible.
  - If search returns nothing useful, answer from your training knowledge and state that explicitly.

Write your complete analysis."""
    ),
    tools=[google_search],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.4,
        top_p=0.95,
        max_output_tokens=2048,
    ),
    output_key="research_result",
)
