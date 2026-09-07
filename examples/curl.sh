#!/usr/bin/env bash
# InvoiceIn — every endpoint once. Run from the repository root.
#   INVOICEIN_KEY=ii_... ./examples/curl.sh
# Without INVOICEIN_KEY the calls use the no-key demo quota (20 invoices a day per IP).
set -euo pipefail
API="${INVOICEIN_API:-https://invoicein-api.peculiar.systems}"
AUTH=(); [ -n "${INVOICEIN_KEY:-}" ] && AUTH=(-H "X-Api-Key: $INVOICEIN_KEY")

echo "== formats and rule-set versions"
curl -s "$API/v1/formats" | head -c 600; echo

echo "== everything in one call (JSON + validation), German hints"
curl -s "${AUTH[@]}" -X POST "$API/v1/invoice?include=validation&lang=de" -F file=@samples/xrechnung-3.0-ubl.xml | head -c 800; echo

echo "== a hybrid PDF: the XML is pulled out of the Factur-X container"
curl -s "${AUTH[@]}" -X POST "$API/v1/parse" --data-binary @samples/factur-x-en16931.pdf | head -c 400; echo

echo "== validation only, Polish hints, KSeF FA(3)"
curl -s "${AUTH[@]}" -X POST "$API/v1/validate?lang=pl" --data-binary @samples/ksef-fa3-przyklad-1.xml | head -c 400; echo

echo "== A4 PDF rendering → out.pdf"
curl -s "${AUTH[@]}" -X POST "$API/v1/render.pdf?lang=en" --data-binary @samples/peppol-bis3-base-example.xml -o out.pdf && ls -la out.pdf

echo "== CSV (one row per line item) and DATEV Buchungsstapel"
curl -s "${AUTH[@]}" -X POST "$API/v1/export.csv" --data-binary @samples/fatturapa-fpr01.xml | head -3
curl -s "${AUTH[@]}" -X POST "$API/v1/export.datev?skr=03&creditor_account=70000" --data-binary @samples/xrechnung-3.0-cii.xml | head -3

echo "== explain a rule id"
curl -s "$API/v1/rules/BR-CO-15?lang=en"; echo
