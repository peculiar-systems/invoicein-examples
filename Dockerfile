# stdio bridge to the hosted InvoiceIn MCP server (see bridge/). Used by directories that start a
# container to introspect the tool list; the parsing itself happens at invoicein-api.peculiar.systems.
# The bridge mirrors the hosted server's tool definitions; bridge/tools.json is the offline fallback.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "mcp>=1.10,<3"
COPY bridge/ /app/bridge/
ENV INVOICEIN_KEY=""
ENTRYPOINT ["python", "/app/bridge/invoicein_mcp_bridge.py"]
