#!/usr/bin/env python3
r"""Deploy orchestrator to Agent Runtime including sub_agents/ and tools/.

Must be run with the agents-cli Python (NOT uv run):
    "C:\Users\madhanmohan\AppData\Roaming\uv\tools\google-agents-cli\Scripts\python.exe" `
        deploy_agent_runtime.py `
        --mcp-url https://bi-tools-server-492257799932.us-central1.run.app/mcp `
        --audit-url https://audit-agent-service-492257799932.us-central1.run.app

Why: agents-cli deploy only packages ./orchestrator by default.
This script calls deploy_agent_runtime() with source_packages that also include
./sub_agents and ./tools so all imports resolve in the Agent Runtime container.
"""

import argparse
import os
import sys

# Change to project root so relative paths (./orchestrator, uv run, etc.) work
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv() -> None:
    """Minimal .env parser — avoids python-dotenv dep not present in agents-cli venv."""
    env_path = ".env"
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


_load_dotenv()

from google.agents.cli._project import find_project_root, read_project_config  # noqa: E402
from google.agents.cli.deploy.agent_runtime import deploy_agent_runtime  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deploy orchestrator to Agent Runtime with all source packages"
    )
    parser.add_argument("--project", default="agentic-bi-497010")
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--mcp-url", required=True)
    parser.add_argument("--audit-url", required=True)
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Start deployment and return immediately (poll with: agents-cli deploy --status)",
    )
    args = parser.parse_args()

    rag_corpus_id = os.environ.get("RAG_CORPUS_ID", "")

    # Build comma-separated KEY=VALUE string that deploy_agent_runtime expects.
    # GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION / GOOGLE_CLOUD_REGION are reserved
    # by Agent Runtime and injected automatically — do NOT include them here.
    env_vars_parts = [
        f"MCP_URL={args.mcp_url}",
        f"AUDIT_A2A_URL={args.audit_url}",
        "GOOGLE_GENAI_USE_VERTEXAI=true",
        "LOCAL_DEV=false",
    ]
    if rag_corpus_id:
        env_vars_parts.append(f"RAG_CORPUS_ID={rag_corpus_id}")

    cfg = read_project_config(find_project_root())

    req_file = "orchestrator/app_utils/.requirements.txt"
    if not os.path.exists(req_file):
        import subprocess  # noqa: PLC0415
        os.makedirs(os.path.dirname(req_file), exist_ok=True)
        # Use uv pip freeze (not uv export --locked) — captures ALL installed packages,
        # including those installed via `uv pip install` outside pyproject.toml (e.g. a2a-sdk, google-adk).
        # Strip Windows-only packages that have no Linux distribution (Agent Runtime runs Linux).
        _WIN_ONLY = {"pywin32", "pywin32-ctypes", "pywinpty", "pyreadline3", "pyreadline"}
        result = subprocess.run(
            ["uv", "pip", "freeze"],
            capture_output=True, text=True, check=True,
        )
        lines = [
            l for l in result.stdout.splitlines()
            if not any(l.lower().startswith(pkg) for pkg in _WIN_ONLY)
        ]
        with open(req_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Requirements written to {req_file}")

    deploy_agent_runtime(
        cfg=cfg,
        project=args.project,
        location=args.region,
        # Include sub_agents/ and tools/ — default would only have ./orchestrator
        source_packages=("./orchestrator", "./sub_agents", "./tools"),
        # Pass explicitly so deploy_agent_runtime skips auto-generation (avoids emoji encoding crash)
        requirements_file=req_file,
        set_env_vars=",".join(env_vars_parts),
        no_wait=args.no_wait,
    )


if __name__ == "__main__":
    main()
