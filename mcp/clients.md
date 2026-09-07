# InvoiceIn as an MCP server

Remote server, streamable HTTP: `https://invoicein-api.peculiar.systems/mcp`

Tools: `read_invoice` (canonical JSON + validation), `validate_invoice` (report only), `invoice_to_html`, `invoice_to_csv`, `invoice_to_datev`. Every tool takes `file_base64` (the invoice file) and, where relevant, `lang` (`en`, `de`, `pl`, `it`, `fr`). One tool call = one credit; without a key the demo quota (20 a day per IP) applies. A file that carries several invoices returns only the first one over MCP — use the REST API for lots.

## Claude Desktop / Claude Code

`claude_desktop_config.json` (or `claude mcp add --transport http invoicein https://invoicein-api.peculiar.systems/mcp --header "X-Api-Key: ii_..."`):

```json
{
  "mcpServers": {
    "invoicein": {
      "type": "http",
      "url": "https://invoicein-api.peculiar.systems/mcp",
      "headers": { "X-Api-Key": "ii_..." }
    }
  }
}
```

## Cursor

`.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "invoicein": {
      "url": "https://invoicein-api.peculiar.systems/mcp",
      "headers": { "X-Api-Key": "ii_..." }
    }
  }
}
```

## Any MCP client (Python SDK)

```python
import asyncio, base64, json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client("https://invoicein-api.peculiar.systems/mcp/") as (read, write, *_):
        async with ClientSession(read, write) as s:
            await s.initialize()
            b64 = base64.b64encode(open("samples/xrechnung-3.0-ubl.xml", "rb").read()).decode()
            res = await s.call_tool("read_invoice", {"file_base64": b64, "lang": "de"})
            print(json.loads(res.content[0].text)["validation"])

asyncio.run(main())
```

Registry manifest: [`server.json`](server.json).
