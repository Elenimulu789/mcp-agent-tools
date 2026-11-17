"""Own an isolated stdio child and its MCP session for each run."""
import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
import os
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]
TOOL_NAMES = frozenset({"query_database", "get_current_weather", "calculate_expression"})


@asynccontextmanager
async def connect():
    """Start the server without passing provider credentials to the child."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server.mcp_server"],
        cwd=ROOT,
        env={"PYTHONNOUSERSITE": "1", "PATH": os.defpath},
    )
    with open(os.devnull, "w", encoding="utf-8") as server_stderr:
        async with stdio_client(params, errlog=server_stderr) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=12)) as session:
                await session.initialize()
                yield session


async def discover(session: ClientSession) -> list:
    """Discover the server's tools and enforce the host's capability allowlist."""
    found = (await session.list_tools()).tools
    return [tool for tool in found if tool.name in TOOL_NAMES]


async def invoke(session: ClientSession, name: str, args: dict) -> dict:
    """Call an authorized MCP tool and cap what can re-enter the model context."""
    if name not in TOOL_NAMES:
        return {"ok": False, "error": "That tool is unavailable."}
    try:
        async with asyncio.timeout(10):
            result = await session.call_tool(name, args)
        if result.isError or not isinstance(result.structuredContent, dict):
            return {"ok": False, "error": "The server rejected the tool arguments or response."}
        return result.structuredContent
    except Exception:
        return {"ok": False, "error": "The tool failed or timed out."}
