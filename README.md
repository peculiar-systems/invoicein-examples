# InvoiceIn — examples

**Any European e-invoice a business *receives* → one canonical EN 16931 JSON, a validation report with plain-language fix hints, a PDF, CSV or DATEV export.** One stateless endpoint, nothing stored.

Accepts: XRechnung (UBL and CII), EN 16931 UBL 2.1 Invoice/CreditNote, Peppol BIS Billing 3, CII D16B, ZUGFeRD 1.0 / 2.x and Factur-X hybrid PDFs, Italy's FatturaPA 1.2, Poland's KSeF FA(2)/FA(3).

- Product page: https://invoicein.peculiar.systems (EN · [DE](https://invoicein.peculiar.systems/de) · [PL](https://invoicein.peculiar.systems/pl) · [IT](https://invoicein.peculiar.systems/it) · [FR](https://invoicein.peculiar.systems/fr))
- API reference (interactive): https://invoicein-api.peculiar.systems/docs
- OpenAPI: https://invoicein-api.peculiar.systems/openapi.json
- MCP server: `https://invoicein-api.peculiar.systems/mcp` (streamable HTTP)

This repository holds runnable examples, sample invoices you can test with, and the MCP registry manifest. The service itself is not open source.

## 60 seconds

```bash
curl -X POST "https://invoicein-api.peculiar.systems/v1/invoice?include=validation&lang=en" \
  -H "X-Api-Key: $INVOICEIN_KEY" \
  -F file=@samples/factur-x-en16931.pdf
```

No key yet? Leave the header out: 20 invoices a day per IP, same output. A trial key (100 invoices, 30 days, no card) comes from the product page.

The response ([full example](examples/response-peppol.json)):

```jsonc
{
  "ok": true,
  "source":  { "syntax": "UBL", "format": "peppol-bis3", "profile": "Peppol BIS Billing 3.0", "container": "xml" },
  "invoice": {                         // canonical EN 16931, field names carry BT/BG numbers in /v1/schema
    "document": { "id": "Snippet1", "issue_date": "2017-11-13", "type_code": "380", "currency": "EUR", "due_date": "2017-12-01", ... },
    "seller":   { "name": "SupplierOfficialName Ltd", "vat_id": "GB1232434", "electronic_address": { "value": "9482348239847239874", "scheme": "0088" }, ... },
    "buyer":    { ... },
    "lines":    [ { "id": "1", "quantity": 7, "unit": "DAY", "net_amount": 2800, "tax": { "category": "S", "rate": 25 }, "item": { "name": "item name" } }, ... ],
    "tax_breakdown": [ { "taxable_amount": 1325, "tax_amount": 331.25, "category": "S", "rate": 25 } ],
    "totals":   { "line_net": 1300, "charges": 25, "net": 1325, "tax": 331.25, "gross": 1656.25, "due": 1656.25 },
    "payment":  { "means_code": "30", "remittance_info": "Snippet1", "credit_transfers": [ { "iban": "IBAN32423940", "account_name": "AccountName", "bic": "BIC324098" } ] }
  },
  "validation": { "valid": true, "errors": 0, "warnings": 0,
                  "rule_sets": [ { "id": "XSD:ubl-invoice" }, { "id": "EN16931-UBL", "version": "EN 16931 validation artefacts 1.3.16" }, { "id": "Peppol-UBL" } ],
                  "issues": [] },
  "timings_ms": { "detect": 0.5, "map": 14.4, "validate": 86.0, "total": 100.8 },
  "credits": { "mode": "key", "remaining": 99 }
}
```

When something is wrong, every failed rule carries a hint in the requested language ([example, KSeF FA(3) in Polish](examples/response-fa3-invalid.json)):

```jsonc
{ "id": "XSD-UNEXPECTED-ELEMENT", "severity": "error", "rule_set": "XSD:fa3",
  "message": "Element '{http://crd.gov.pl/wzor/2025/06/25/13775/}Adnotacje': This element is not expected. Expected is one of ( {http://crd.gov.pl/wzor/2025/06/25/1 …",
  "hint": "XML zawiera element, którego schemat nie dopuszcza w tym miejscu. Nazwa elementu jest błędna, element należy do innego profilu/wersji (np. UBL 2.0 lub ZUGFeRD EXTENDED), jest zdublowany albo jest własnym rozszerzeniem. Usuń go lub zmień jego nazwę.",
  "who": "sender", "location": "/*/*[4]/*[8]", "line": 43 }
```

## Endpoints

| Call | Returns |
|---|---|
| `POST /v1/invoice?include=validation,html,pdf,csv,datev&lang=en\|de\|pl\|it\|fr` | everything in one JSON (extras base64/inline) |
| `POST /v1/parse` | canonical JSON only |
| `POST /v1/validate` | validation report only |
| `POST /v1/render.html` · `POST /v1/render.pdf` | human-readable rendering, labels in the five languages |
| `POST /v1/export.csv?level=lines\|documents` | flat CSV |
| `POST /v1/export.datev?skr=03\|04&creditor_account=70000` | DATEV Buchungsstapel (EXTF 700, cp1252) |
| `GET /v1/formats` · `GET /v1/rules/{id}?lang=de` · `GET /v1/schema` | formats + rule versions · explain a rule id · field guide |

Body: multipart field `file`, or the raw XML/PDF. Send a real `User-Agent` (Cloudflare rejects the default `Python-urllib` one with error 1010). Auth: `X-Api-Key` or `Authorization: Bearer`. One invoice = one credit whatever outputs you request; a file that carries several invoices (a FatturaPA lot) costs one per invoice. Remaining credits come back in `X-Credits-Remaining`.

## Examples in this repo

- [`examples/curl.sh`](examples/curl.sh) — every endpoint once
- [`examples/node.mjs`](examples/node.mjs) — `fetch` + `FormData`, no dependencies
- [`examples/python.py`](examples/python.py) — standard library only
- [`examples/n8n-workflow.json`](examples/n8n-workflow.json) — mailbox attachment → InvoiceIn → JSON, importable into n8n
- [`mcp/server.json`](mcp/server.json) — manifest for the MCP registry; [`mcp/clients.md`](mcp/clients.md) — Claude Desktop / Cursor config

## Sample invoices

| File | What it is | Source / licence |
|---|---|---|
| `samples/xrechnung-3.0-ubl.xml`, `samples/xrechnung-3.0-cii.xml` | the same XRechnung 3.0 invoice in both syntaxes | [KoSIT XRechnung testsuite](https://github.com/itplr-kosit/xrechnung-testsuite), Apache-2.0 |
| `samples/peppol-bis3-base-example.xml` | Peppol BIS Billing 3 base example | [OpenPeppol](https://github.com/OpenPEPPOL/peppol-bis-invoice-3), Apache-2.0 |
| `samples/factur-x-en16931.pdf` | Factur-X hybrid PDF, EN 16931 profile | [ZUGFeRD corpus](https://github.com/ZUGFeRD/corpus) (FNFE-MPE examples), Apache-2.0 |
| `samples/ksef-fa3-przyklad-1.xml` | KSeF FA(3) official example no. 1 | Polish Ministry of Finance, public |
| `samples/fatturapa-fpr01.xml` | FatturaPA 1.2 official example FPR01 | Agenzia delle Entrate, public |

Both XRechnung files produce the same canonical JSON (only the syntax-specific `extensions` block differs) — that is the point of the canonical model.

## What it does not do

No OCR (a PDF without embedded XML is rejected with `pdf-no-xml`). Not a Peppol access point, not a French PDP, not a KSeF or SdI client: it reads what you already received and never transmits anything. Factur-X/ZUGFeRD profiles below EN 16931 (MINIMUM, BASIC WL, BASIC) get schema and arithmetic checks only, because the EN 16931 rules would only produce noise there. Validation results are informational, not legal advice.

## Licence

The examples in this repository are MIT. Sample invoices keep the licences listed above.
