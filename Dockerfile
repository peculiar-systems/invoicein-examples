# stdio bridge to the hosted InvoiceIn MCP server (see bridge/). Used by directories that start a
# container to introspect the tool list; the parsing itself happens at invoicein-api.peculiar.systems.
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "mcp>=1.10,<3"
COPY bridge/invoicein_mcp_bridge.py /app/invoicein_mcp_bridge.py
ENV INVOICEIN_KEY=""
ENTRYPOINT ["python", "/app/invoicein_mcp_bridge.py"]
