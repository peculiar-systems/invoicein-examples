"""InvoiceIn from Python — standard library only.

    INVOICEIN_KEY=ii_... python3 examples/python.py samples/ksef-fa3-przyklad-1.xml
"""
import json
import os
import sys
import urllib.request

API = os.environ.get("INVOICEIN_API", "https://invoicein-api.peculiar.systems")
path = sys.argv[1] if len(sys.argv) > 1 else "samples/xrechnung-3.0-ubl.xml"

with open(path, "rb") as fh:
    body = fh.read()

# raw body works for XML and PDF alike; multipart (field `file`) is accepted too
headers = {"Content-Type": "application/octet-stream"}
if os.environ.get("INVOICEIN_KEY"):
    headers["X-Api-Key"] = os.environ["INVOICEIN_KEY"]

req = urllib.request.Request(f"{API}/v1/invoice?include=validation&lang=en", data=body, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.load(resp)
        remaining = resp.headers.get("X-Credits-Remaining")
except urllib.error.HTTPError as e:
    err = json.load(e)["error"]
    sys.exit(f"{e.code} {err['code']}: {err['message']} {err.get('hint', '')}")

inv, val = data["invoice"], data["validation"]
print(f"{data['source']['format']} ({data['source'].get('profile')}) — {inv['document'].get('id')} from {inv.get('seller', {}).get('name')}")
print(f"net {inv['totals'].get('net')} + VAT {inv['totals'].get('tax')} = {inv['totals'].get('gross')} {inv['document'].get('currency')}")
print(f"valid: {val['valid']} ({val['errors']} errors, {val['warnings']} warnings)")
for i in val["issues"]:
    print(f"  [{i['severity']}] {i['id']}: {i.get('hint') or i['message']}")
print(f"credits remaining: {remaining}")
