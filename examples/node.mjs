// InvoiceIn from Node 18+ — no dependencies.
//   INVOICEIN_KEY=ii_... node examples/node.mjs samples/xrechnung-3.0-ubl.xml
import { readFile } from "node:fs/promises";
import { basename } from "node:path";

const API = process.env.INVOICEIN_API ?? "https://invoicein-api.peculiar.systems";
const file = process.argv[2] ?? "samples/factur-x-en16931.pdf";

const form = new FormData();
form.append("file", new Blob([await readFile(file)]), basename(file));

const res = await fetch(`${API}/v1/invoice?include=validation,datev&lang=en`, {
  method: "POST",
  headers: process.env.INVOICEIN_KEY ? { "X-Api-Key": process.env.INVOICEIN_KEY } : {},
  body: form,
});
const data = await res.json();
if (!data.ok) {
  console.error(`${res.status} ${data.error.code}: ${data.error.message}`, data.error.hint ?? "");
  process.exit(1);
}

const { source, invoice, validation } = data;
console.log(`${source.format} (${source.profile}) — ${invoice.document.id} from ${invoice.seller?.name}`);
console.log(`net ${invoice.totals.net} + VAT ${invoice.totals.tax} = ${invoice.totals.gross} ${invoice.document.currency}`);
console.log(`valid: ${validation.valid} (${validation.errors} errors, ${validation.warnings} warnings), rule sets: ${validation.rule_sets.map(r => r.id).join(", ")}`);
for (const i of validation.issues) console.log(`  [${i.severity}] ${i.id}: ${i.hint ?? i.message}`);
console.log(`credits remaining: ${res.headers.get("X-Credits-Remaining")}`);
// data.datev holds the DATEV Buchungsstapel as text (cp1252 when fetched via /v1/export.datev)
