"""InvoiceIn MCP bridge — a local stdio MCP server in front of the hosted InvoiceIn MCP server
(https://invoicein-api.peculiar.systems/mcp).

Use it when your MCP client only speaks stdio, or when you want the remote server to appear as a
local command. It exposes the hosted server's tools one-to-one — same names, descriptions, input and
output schemas, annotations — and forwards every call. No parsing happens here; the invoice goes to
InvoiceIn and the answer comes back.

    pip install "mcp>=1.10,<3"
    INVOICEIN_KEY=ii_...  python invoicein_mcp_bridge.py        # key optional: demo quota without it
    python invoicein_mcp_bridge.py --snapshot                    # refresh tools.json from the hosted server

Tool definitions are fetched from the hosted server when the first client asks for them; if it cannot
be reached, the bundled tools.json snapshot answers `tools/list` so the server still introspects.

Claude Desktop:
    "invoicein": { "command": "python", "args": ["/path/to/invoicein_mcp_bridge.py"],
                   "env": { "INVOICEIN_KEY": "ii_..." } }
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import mcp.types as types
from mcp import ClientSession

try:                                                     # mcp 2.x
    from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client

    def _http_client(url: str, headers: dict[str, str]):
        return streamable_http_client(url, http_client=create_mcp_http_client(headers=headers or None))
except ImportError:                                      # mcp 1.x
    from mcp.client.streamable_http import streamablehttp_client

    def _http_client(url: str, headers: dict[str, str]):
        return streamablehttp_client(url, headers=headers or None)

REMOTE = os.environ.get("INVOICEIN_MCP_URL", "https://invoicein-api.peculiar.systems/mcp/")
KEY = os.environ.get("INVOICEIN_KEY", "")
SNAPSHOT = Path(__file__).with_name("tools.json")
FETCH_TIMEOUT = float(os.environ.get("INVOICEIN_MCP_FETCH_TIMEOUT", "10"))

INSTRUCTIONS = (
    "InvoiceIn reads the e-invoices a business receives. Five read-only tools, each taking one invoice file "
    "(XML in UBL, CII, XRechnung, Peppol BIS 3, FatturaPA or KSeF syntax, or a ZUGFeRD/Factur-X hybrid PDF) "
    "base64-encoded in `file_base64`, up to 25 MB: read_invoice (data + validation), validate_invoice (verdict only), "
    "invoice_to_html (printable view), invoice_to_csv (flat table), invoice_to_datev (German bookkeeping import). "
    "Every tool call costs one invoice credit; without an API key the anonymous quota is 20 invoices per day per IP. "
    "Calls are forwarded to the hosted InvoiceIn server; files are processed in memory and never stored."
)


def _headers() -> dict[str, str]:
    return {"X-Api-Key": KEY} if KEY else {}


async def _fetch_tools() -> list[types.Tool]:
    async with _http_client(REMOTE, _headers()) as streams:
        async with ClientSession(streams[0], streams[1]) as s:
            await s.initialize()
            return list((await s.list_tools()).tools)


def _load_snapshot() -> list[types.Tool]:
    with SNAPSHOT.open(encoding="utf-8") as f:
        return [types.Tool.model_validate(t) for t in json.load(f)["tools"]]


_tools: list[types.Tool] | None = None


async def _tools_cached() -> list[types.Tool]:
    global _tools
    if _tools is None:
        try:
            _tools = await asyncio.wait_for(_fetch_tools(), FETCH_TIMEOUT)
        except Exception as e:  # offline, sandboxed, or the hosted server is down
            print(f"invoicein bridge: hosted server not reachable ({type(e).__name__}); using bundled tools.json",
                  file=sys.stderr)
            _tools = _load_snapshot()
    return _tools


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult.model_validate({
        "content": [{"type": "text", "text": json.dumps({"ok": False, "error": {"code": "bridge", "message": message}})}],
        "isError": True,
    })


async def _forward(name: str, args: dict[str, Any]) -> types.CallToolResult:
    try:
        async with _http_client(REMOTE, _headers()) as streams:
            async with ClientSession(streams[0], streams[1]) as s:
                await s.initialize()
                res = await s.call_tool(name, args)
    except Exception as e:
        return _error_result(f"InvoiceIn not reachable: {type(e).__name__}: {e}")
    # re-validate through the wire shape so the same code works on mcp 1.x (camelCase) and 2.x (snake_case)
    return types.CallToolResult.model_validate(res.model_dump(by_alias=True, exclude_none=True))


def build_server():
    from mcp.server.lowlevel import Server

    async def on_list_tools(ctx, params):
        return types.ListToolsResult(tools=await _tools_cached())

    async def on_call_tool(ctx, params):
        return await _forward(params.name, params.arguments or {})

    try:                                                 # mcp 2.x: handlers go through the constructor
        return Server("invoicein", version="0.1.1", instructions=INSTRUCTIONS,
                      on_list_tools=on_list_tools, on_call_tool=on_call_tool)
    except TypeError:                                    # mcp 1.x: decorators
        server = Server("invoicein", version="0.1.1", instructions=INSTRUCTIONS)

        @server.list_tools()
        async def _list_tools() -> list[types.Tool]:
            return await _tools_cached()

        @server.call_tool()
        async def _call_tool(name: str, arguments: dict[str, Any] | None):
            return await _forward(name, arguments or {})
        return server


async def _serve() -> None:
    from mcp.server.stdio import stdio_server
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


async def _snapshot() -> None:
    tools = await _fetch_tools()
    payload = {
        "source": REMOTE,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tools": [t.model_dump(by_alias=True, exclude_none=True) for t in tools],
    }
    SNAPSHOT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {SNAPSHOT} ({len(tools)} tools)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="InvoiceIn MCP bridge (stdio → hosted server)")
    ap.add_argument("--snapshot", action="store_true", help="fetch the hosted server's tool list into tools.json and exit")
    a = ap.parse_args()
    asyncio.run(_snapshot() if a.snapshot else _serve())
