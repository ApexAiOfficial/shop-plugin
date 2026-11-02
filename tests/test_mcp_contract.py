"""Every MCP tool, argument and result field a skill or doc names exists in the store's published contract.

Skills write a tool call as ``tool_name(arg, arg)`` with argument names only. A name in an "MCP tool" table
column must be a contract tool; a call's arguments must be that tool's input properties and include every
required one.
"""

from __future__ import annotations

import hashlib
import json
import re

import pytest
from conftest import CONTRACT, DOC_FILES, ROOT, SKILL_FILES, contract, load_json, tools

TOOLS = tools()
FILES = [*SKILL_FILES, *DOC_FILES]
CALL = re.compile(r"`([a-z_][a-z0-9_]*)\(([^`()]*)\)`")


def _calls(text: str) -> list[tuple[str, list[str]]]:
    return [(name, [arg.strip() for arg in args.split(",") if arg.strip()])
            for name, args in CALL.findall(text) if name in TOOLS]


def _mcp_column_names(text: str) -> list[str]:
    """Backticked names in the "MCP tool" column of every Markdown table."""
    names: list[str] = []
    column = None
    for line in text.splitlines():
        if not line.startswith("|"):
            column = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if column is None:
            column = next((i for i, cell in enumerate(cells) if cell.lower() == "mcp tool"), -1)
            continue
        if 0 <= column < len(cells) and not set(cells[column]) <= set("-: "):
            cell = cells[column]
            names += re.findall(r"`([a-z_][a-z0-9_]*)\(", cell)
            names += re.findall(r"^`([a-z_][a-z0-9_]*)`", cell)
    return names


def test_the_vendored_contract_matches_its_manifest() -> None:
    manifest = load_json(ROOT / "contracts" / "MANIFEST.json")
    data = CONTRACT.read_bytes()
    assert manifest["files"]["merchant-mcp-v1.json"] == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    assert manifest["api_revision"] == contract()["api_revision"]
    assert contract()["path"] == "/api/merchant/v1/mcp"


def test_every_tool_only_reads_and_has_a_scope_entry() -> None:
    document = contract()
    assert set(document["scopes"]) == set(TOOLS) and len(TOOLS) == 12
    for tool in TOOLS.values():
        assert tool["annotations"]["readOnlyHint"] is True and tool["annotations"]["destructiveHint"] is False
        assert tool["inputSchema"]["type"] == "object"


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_named_tool_exists(path) -> None:
    text = path.read_text(encoding="utf-8")
    named = set(_mcp_column_names(text)) | {name for name, _ in _calls(text)}
    # A host-prefixed name, like mcp__plugin_shop_shop__get_store, names a tool too.
    named |= {match for match in re.findall(r"mcp__plugin_shop_shop__([a-z_]+)", text)}
    unknown = sorted(name for name in named if name not in TOOLS)
    assert not unknown, f"{path.name} names tools the contract does not have: {unknown}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_call_uses_real_arguments_and_all_required_ones(path) -> None:
    for name, args in _calls(path.read_text(encoding="utf-8")):
        schema = TOOLS[name]["inputSchema"]
        properties = set(schema.get("properties", {}))
        for arg in args:
            assert re.fullmatch(r"[a-z_][a-z0-9_]*", arg), f"{path.name}: {name}({arg}): names only, no values"
            assert arg in properties, f"{path.name}: {name} has no argument {arg!r} (has {sorted(properties)})"
        missing = set(schema.get("required", [])) - set(args)
        assert not missing, f"{path.name}: {name}(...) leaves out required {sorted(missing)}"


def test_the_skills_cover_every_tool() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in SKILL_FILES)
    named = set(_mcp_column_names(text)) | {name for name, _ in _calls(text)}
    assert set(TOOLS) <= named, sorted(set(TOOLS) - named)


def test_the_parser_finds_what_it_should() -> None:
    sample = ("| Step | MCP tool |\n| --- | --- |\n| a | `get_order(order_id)` |\n| b | `needs_attention` |\n"
              "\nprose `list_orders(status, since)` and `len(x)`")
    assert _mcp_column_names(sample) == ["get_order", "needs_attention"]
    assert _calls(sample) == [("get_order", ["order_id"]), ("list_orders", ["status", "since"])]


#: Result fields the skills tell the agent to read, by tool. A contract update that drops one fails here.
RESULT_FIELDS = {
    "get_store": ["store", "token", "name", "tier", "scopes", "expires_at"],
    "needs_attention": ["needs_operator", "low_stock", "open_tickets"],
    "list_payments": ["health", "data", "needs_operator", "pending_fulfillment", "unverified",
                      "oldest_open_age_seconds", "reconciler_stale", "order_id", "state", "anomaly_code",
                      "total_amount"],
    "list_stock": ["data", "available", "title"],
    "sales_summary": ["current", "previous", "gross_stars", "net_stars", "paid_orders", "average_order_stars",
                      "refunded_orders", "refunded_stars", "coupon_discounts", "referral_discounts",
                      "membership_charges", "membership_stars", "live_members", "top_items", "title", "quantity",
                      "revenue_stars", "new_buyers", "returning_buyers", "checkouts", "checkouts_paid",
                      "open_tickets", "series", "bucket_days"],
    "list_orders": ["summary", "orders", "total_stars", "id", "status", "created_at", "paid_at",
                    "buyer_tg_user_id", "next_cursor"],
    "list_items": ["id", "title", "price_stars", "status", "category_id", "sells_keys", "is_bundle", "has_photo"],
    "get_item": ["description", "category_title", "delivery", "file", "stock", "variants", "bundle",
                 "members_only", "has_sales", "version", "publish_blocker", "available", "label", "is_active",
                 "file_status", "components", "ready", "name", "size", "mime"],
    "get_order": ["items", "subtotal_stars", "coupon_discount_stars", "referral_discount_stars", "receipts",
                  "charge", "amount_stars", "state", "key_counts", "delivered", "revoked", "grants", "refundable",
                  "refunded_at", "refund_reason", "refund_request", "in_progress", "requested_at", "source",
                  "reason", "title", "quantity", "unit_price_stars"],
}


@pytest.mark.parametrize("tool", sorted(RESULT_FIELDS))
def test_the_result_fields_the_skills_read_exist(tool: str) -> None:
    schema = TOOLS[tool]["outputSchema"]
    properties = set(schema.get("properties", {}))
    for definition in schema.get("$defs", {}).values():
        properties |= set(definition.get("properties", {}))
    missing = [field for field in RESULT_FIELDS[tool] if field not in properties]
    assert not missing, f"{tool} no longer returns {missing}"


def test_the_contract_is_plain_json_with_sorted_keys() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"
