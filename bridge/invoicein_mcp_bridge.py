"""InvoiceIn MCP bridge — a local stdio MCP server that forwards every tool call to the hosted
InvoiceIn server (https://invoicein-api.peculiar.systems/mcp).

Use it when your MCP client only speaks stdio, or when you want the remote server to appear as a
local command. No parsing happens here; the invoice goes to InvoiceIn and the answer comes back.

    pip install "mcp>=1.10"
    INVOICEIN_KEY=ii_...  python invoicein_mcp_bridge.py        # key optional: demo quota without it

Claude Desktop:
    "invoicein": { "command": "python", "args": ["/path/to/invoicein_mcp_bridge.py"],
                   "env": { "INVOICEIN_KEY": "ii_..." } }
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

from mcp import ClientSession

try:                                                     # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client

    def _http_client(url: str, headers: dict[str, str]):
        return streamable_http_client(url, http_client=create_mcp_http_client(headers=headers or None))
except ImportError:                                      # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server
    from mcp.client.streamable_http import streamablehttp_client

    def _http_client(url: str, headers: dict[str, str]):
        return streamablehttp_client(url, headers=headers or None)

REMOTE = os.environ.get("INVOICEIN_MCP_URL", "https://invoicein-api.peculiar.systems/mcp/")
KEY = os.environ.get("INVOICEIN_KEY", "")

mcp = _Server("invoicein", instructions=(
    "Reads and validates any European e-invoice a business receives — XRechnung, UBL, CII, ZUGFeRD/Factur-X PDF, "
    "Peppol BIS 3, FatturaPA, KSeF FA(3) — into canonical EN 16931 JSON with plain-language fix hints. "
    "Pass the file content base64-encoded. Calls are forwarded to the hosted InvoiceIn server."))


async def _forward(tool: str, args: dict[str, Any]) -> str:
    headers = {"X-Api-Key": KEY} if KEY else {}
    async with _http_client(REMOTE, headers) as streams:
        async with ClientSession(streams[0], streams[1]) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            texts = [c.text for c in res.content if getattr(c, "type", "") == "text"]
            return "\n".join(texts) if texts else json.dumps({"ok": False, "error": "empty response from InvoiceIn"})


@mcp.tool()
async def read_invoice(file_base64: str, lang: str = "en") -> str:
    """Parse an e-invoice into canonical EN 16931 JSON and validate it (lang: en, de, pl, it, fr)."""
    return await _forward("read_invoice", {"file_base64": file_base64, "lang": lang})


@mcp.tool()
async def validate_invoice(file_base64: str, lang: str = "en") -> str:
    """Validation report only: rule sets applied, errors and warnings with fix hints."""
    return await _forward("validate_invoice", {"file_base64": file_base64, "lang": lang})


@mcp.tool()
async def invoice_to_html(file_base64: str, lang: str = "en") -> str:
    """Human-readable HTML rendering of the invoice."""
    return await _forward("invoice_to_html", {"file_base64": file_base64, "lang": lang})


@mcp.tool()
async def invoice_to_csv(file_base64: str, level: str = "lines") -> str:
    """Flat CSV: one row per line item (level=lines) or per document (level=documents)."""
    return await _forward("invoice_to_csv", {"file_base64": file_base64, "level": level})


@mcp.tool()
async def invoice_to_datev(file_base64: str, skr: str = "03", creditor_account: str = "70000") -> str:
    """DATEV Buchungsstapel (EXTF 700) for the incoming invoice."""
    return await _forward("invoice_to_datev", {"file_base64": file_base64, "skr": skr, "creditor_account": creditor_account})


if __name__ == "__main__":
    mcp.run(transport="stdio")
