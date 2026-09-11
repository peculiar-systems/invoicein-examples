"""The bridge proxies the hosted server, so its tool surface lives in bridge/tools.json.

That snapshot is what an offline client and a static analyser see, which makes it worth a test
of its own: a directory that cannot reach the live endpoint judges the server by this file, and
a missing annotation there reads as a tool with no safety hints at all.

    python3 -m pytest tests -q        (or: python3 tests/test_tool_snapshot.py)
"""
import json
from pathlib import Path

SNAPSHOT = Path(__file__).resolve().parent.parent / "bridge" / "tools.json"
HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")
EXPECTED = {"read_invoice", "validate_invoice", "invoice_to_html", "invoice_to_csv", "invoice_to_datev"}


def tools():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data["tools"]


def test_every_tool_is_present():
    assert {t["name"] for t in tools()} == EXPECTED


def test_every_tool_declares_all_four_hints_as_booleans():
    """OpenAI's directory rejects a tool where any of the four is missing or non-boolean."""
    for t in tools():
        ann = t.get("annotations") or {}
        for hint in HINTS:
            assert isinstance(ann.get(hint), bool), f"{t['name']}: {hint} is {ann.get(hint)!r}"


def test_no_tool_claims_to_be_destructive():
    """Every tool here reads an invoice and returns a rendering of it; nothing writes."""
    for t in tools():
        ann = t["annotations"]
        assert ann["readOnlyHint"] is True and ann["destructiveHint"] is False, t["name"]


def test_every_tool_has_a_description_worth_reading():
    for t in tools():
        assert len((t.get("description") or "").strip()) > 200, f"{t['name']}: description too thin"


if __name__ == "__main__":
    for fn in (test_every_tool_is_present, test_every_tool_declares_all_four_hints_as_booleans,
               test_no_tool_claims_to_be_destructive, test_every_tool_has_a_description_worth_reading):
        fn(); print("ok", fn.__name__)
