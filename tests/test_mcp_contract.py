"""Every MCP tool, argument and result field a skill or doc names exists in the store's published contract.

Skills write a tool call as ``tool_name(arg, arg)`` with argument names only. A name in an "MCP tool" table
column must be a contract tool; a call's arguments must be that tool's input properties and include every
required one. Tools the skills already teach but the vendored contract does not have yet are listed in
PENDING_TOOLS below, which the next contract sync must empty.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re

import pytest
from conftest import CONTRACT, DOC_FILES, ROOT, SKILL_FILES, SKILLS_DIR, contract, load_json, tools

TOOLS = tools()
FILES = [*SKILL_FILES, *DOC_FILES]
CALL = re.compile(r"`([a-z_][a-z0-9_]*)\(([^`()]*)\)`")
CELL_NAME = re.compile(r"`([a-z_][a-z0-9_]*)(?:\([^`()]*\))?`")
LIST_SEPARATOR = re.compile(r",? and |, ")


def _pending(scope: str | None, inputs: list[str], required: list[str], *, read: bool = False) -> dict:
    return {"scope": scope, "inputs": frozenset(inputs), "required": frozenset(required), "read": read}


# ---------------------------------------------------------------------------------------------------------
# PENDING CONTRACT SYNC. THE NEXT CONTRACT SYNC MUST EMPTY THIS LIST.
#
# The skills already teach the store's whole write surface (licence keys, support and downloads; approvals,
# broadcasts, variants, bundles, file requests and repricing), but the vendored contract (the exact bytes
# PENDING_CONTRACT_SHA256 pins) has only the reads and the category, item and coupon writes. Until the final
# contract is synced, the tools below stand in for it, with the scope, inputs and required inputs the store's
# API defines for them, so the argument checks still run.
#
# After `python tools/sync_contract.py <final merchant-mcp-v1.json>`:
#   1. delete every entry the contract now has (test_pending_tools_are_not_in_the_contract fails until then);
#   2. fix the skills for any tool, argument or result field the final contract names differently;
#   3. the list should then be empty: test_pending_tools_are_emptied_by_the_next_sync fails while it is not
#      and the contract's bytes differ from the pinned digest, whatever its api_revision says (the store can
#      change its contract without moving the revision). A deliberate partial sync sets PENDING_CONTRACT_SHA256
#      to the new MANIFEST.json digest, after checking every entry left below against the store's API.
# ---------------------------------------------------------------------------------------------------------
PENDING_CONTRACT_SHA256 = "7a7583d4f8882eb08c845f9cb54788f610551533b2c8ed5277265b6ba7b9675c"
PENDING_TOOLS: dict[str, dict] = {
    # Licence keys, support and downloads
    "get_item_stock": _pending("inventory:read", ["item_id"], ["item_id"], read=True),
    "stage_key_import": _pending("inventory:write", ["item_id", "keys_text"], ["item_id", "keys_text"]),
    "commit_key_import": _pending("inventory:write", ["item_id", "staged_import", "enable_key_delivery"],
                                  ["item_id", "staged_import"]),
    "void_keys": _pending("inventory:write", ["item_id", "confirmation"], ["item_id"]),
    "release_key_holds": _pending("inventory:write", ["item_id", "confirmation"], ["item_id"]),
    "reply_ticket": _pending("support:write", ["ticket_id", "body"], ["ticket_id", "body"]),
    "close_ticket": _pending("support:write", ["ticket_id"], ["ticket_id"]),
    "restore_downloads": _pending("fulfillment:write", ["order_id", "downloads"], ["order_id"]),
    # Approvals, broadcasts, variants, bundles, file requests and repricing
    "get_approval": _pending(None, ["approval_id"], ["approval_id"], read=True),
    "send_broadcast": _pending("broadcasts:write", ["text"], ["text"]),
    "cancel_broadcast": _pending("broadcasts:write", ["broadcast_id"], ["broadcast_id"]),
    "add_variant": _pending("catalog:write", ["item_id", "label", "price_stars"], ["item_id", "label", "price_stars"]),
    "update_variant": _pending("catalog:write", ["variant_id", "version", "label", "price_stars", "note", "active"],
                               ["variant_id"]),
    "create_bundle": _pending("catalog:write", ["category_id", "title", "price_stars"],
                              ["category_id", "title", "price_stars"]),
    "update_bundle": _pending("catalog:write", ["bundle_id", "add_item_id", "remove_item_id"], ["bundle_id"]),
    "request_product_file": _pending("catalog:write", ["item_id", "variant_id"], ["item_id"]),
    "reprice_items": _pending("catalog:write", ["changes", "confirmation"], ["changes"]),
}

#: What the contract's schema does not encode (its tool descriptions say it in prose), as the overview's tool
#: table must state it: the tools that also need pricing:write, and those a change can send for the owner's
#: approval.
PRICING_TOOLS = {"create_item", "update_item", "add_variant", "update_variant", "create_bundle", "reprice_items"}
APPROVAL_TOOLS = {"update_item", "update_variant", "reprice_items", "create_coupon", "update_coupon", "reply_ticket",
                  "send_broadcast"}

#: Every answer of a tool that changes the store (the write envelope).
ENVELOPE = ["status", "replayed", "noop", "result", "confirmation", "approval", "effect", "next"]


def _known() -> set[str]:
    return set(TOOLS) | set(PENDING_TOOLS)


def _inputs(name: str) -> tuple[set[str], set[str]]:
    """(the input properties, the required ones) of a contract or pending tool."""
    if name in TOOLS:
        schema = TOOLS[name]["inputSchema"]
        return set(schema.get("properties", {})), set(schema.get("required", []))
    return set(PENDING_TOOLS[name]["inputs"]), set(PENDING_TOOLS[name]["required"])


def _scope(name: str) -> str | None:
    return contract()["scopes"][name] if name in TOOLS else PENDING_TOOLS[name]["scope"]


def _reads(name: str) -> bool:
    return TOOLS[name]["annotations"]["readOnlyHint"] if name in TOOLS else PENDING_TOOLS[name]["read"]


def _calls(text: str) -> list[tuple[str, list[str]]]:
    return [(name, [arg.strip() for arg in args.split(",") if arg.strip()])
            for name, args in CALL.findall(text) if name in _known()]


def _called_names(text: str) -> set[str]:
    """Every name written as a call, known or not: a tool name always has an underscore (`len(x)` is no tool),
    so a misspelled `get_aproval(approval_id)` in prose is reported rather than skipped."""
    return {name for name, _ in CALL.findall(text) if "_" in name}


def _cell_names(cell: str) -> list[str]:
    """Every call in a table cell, and the plain names it starts with (`a`, `b` and `c`)."""
    found = re.findall(r"`([a-z_][a-z0-9_]*)\(", cell)
    position = 0
    while match := CELL_NAME.match(cell, position):
        found.append(match.group(1))
        separator = LIST_SEPARATOR.match(cell, match.end())
        if not separator:
            break
        position = separator.end()
    return list(dict.fromkeys(found))


def _tables(text: str) -> list[list[dict[str, str]]]:
    """Every Markdown table in TEXT, as rows keyed by the header cells."""
    tables: list[list[dict[str, str]]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            tables.append([])
        elif not all(set(cell) <= set("-: ") for cell in cells):
            tables[-1].append(dict(zip(header, cells)))
    return tables


def _mcp_column_names(text: str) -> list[str]:
    """Tool names in the "MCP tool" column of every Markdown table."""
    names: list[str] = []
    for table in _tables(text):
        for row in table:
            column = next((cell for key, cell in row.items() if key.lower() == "mcp tool"), None)
            if column is not None:
                names += _cell_names(column)
    return names


def test_the_vendored_contract_matches_its_manifest() -> None:
    manifest = load_json(ROOT / "contracts" / "MANIFEST.json")
    data = CONTRACT.read_bytes()
    assert manifest["files"]["merchant-mcp-v1.json"] == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    assert manifest["api_revision"] == contract()["api_revision"]
    assert contract()["path"] == "/api/merchant/v1/mcp"


def test_every_tool_has_a_scope_and_annotations_that_agree() -> None:
    """Read tools only read; write tools need a write scope; two-step tools are marked destructive."""
    document = contract()
    assert set(document["scopes"]) == set(TOOLS)
    reads = {name for name, tool in TOOLS.items() if tool["annotations"]["readOnlyHint"] is True}
    assert reads and reads < set(TOOLS), "the contract has both read and write tools"
    for name, tool in TOOLS.items():
        hints, scope = tool["annotations"], document["scopes"][name]
        assert {"readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint"} <= set(hints), name
        assert tool["inputSchema"]["type"] == "object", name
        if name in reads:
            assert hints["destructiveHint"] is False and (scope is None or scope.endswith(":read")), name
        else:
            assert hints["readOnlyHint"] is False and scope and scope.endswith(":write"), name
        if "confirmation" in tool["inputSchema"].get("properties", {}):
            assert name not in reads and hints["destructiveHint"] is True, name


def test_every_write_answers_the_envelope() -> None:
    """The skills read status, noop, replayed, effect, confirmation, approval and next from every change."""
    for name, tool in TOOLS.items():
        if tool["annotations"]["readOnlyHint"]:
            continue
        schema = tool["outputSchema"]
        assert set(ENVELOPE) <= set(schema["required"]), name
        assert schema["properties"]["status"]["enum"] == ["done", "confirmation_required", "pending_approval"], name
        definitions = schema["$defs"]
        assert {"id", "expires_at"} <= set(definitions["ConfirmationInfo"]["properties"]), name
        assert {"id", "status", "expires_at"} <= set(definitions["ApprovalInfo"]["properties"]), name
        assert {"summary", "details"} <= set(definitions["Effect"]["properties"]), name


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_named_tool_exists(path) -> None:
    text = path.read_text(encoding="utf-8")
    named = set(_mcp_column_names(text)) | _called_names(text)
    # A host-prefixed name, like mcp__plugin_shop_shop__get_store, names a tool too.
    named |= {match for match in re.findall(r"mcp__plugin_shop_shop__([a-z_]+)", text)}
    unknown = sorted(name for name in named if name not in _known())
    assert not unknown, f"{path.name} names tools neither the contract nor PENDING_TOOLS has: {unknown}"


@pytest.mark.parametrize("path", FILES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_call_uses_real_arguments_and_all_required_ones(path) -> None:
    for name, args in _calls(path.read_text(encoding="utf-8")):
        properties, required = _inputs(name)
        for arg in args:
            assert re.fullmatch(r"[a-z_][a-z0-9_]*", arg), f"{path.name}: {name}({arg}): names only, no values"
            assert arg in properties, f"{path.name}: {name} has no argument {arg!r} (has {sorted(properties)})"
        missing = required - set(args)
        assert not missing, f"{path.name}: {name}(...) leaves out required {sorted(missing)}"


def test_the_skills_cover_every_tool() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in SKILL_FILES)
    named = set(_mcp_column_names(text)) | {name for name, _ in _calls(text)}
    assert _known() <= named, sorted(_known() - named)


def test_two_step_tools_are_shown_with_their_confirmation_call() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in SKILL_FILES)
    calls = _calls(text)
    for name in sorted(_known()):
        if "confirmation" in _inputs(name)[0]:
            assert any(called == name and "confirmation" in args for called, args in calls), name


def test_the_overview_table_gives_every_tool_its_scope_and_level() -> None:
    """The shop skill's tool table agrees with the contract (and, until the sync, with PENDING_TOOLS)."""
    text = (SKILLS_DIR / "shop" / "SKILL.md").read_text(encoding="utf-8")
    [table] = [table for table in _tables(text) if table and {"MCP tool", "Scope", "Level"} <= set(table[0])]
    rows: dict[str, dict[str, str]] = {}
    for row in table:
        [name] = _cell_names(row["MCP tool"])
        assert name not in rows, f"{name} is listed twice"
        rows[name] = row
    assert set(rows) == _known(), sorted(set(rows) ^ _known())
    for name, row in rows.items():
        scope, level = row["Scope"], row["Level"]
        expected = _scope(name)
        if expected is None:
            assert scope.startswith("any"), f"{name}: scope {scope!r}"
        else:
            assert scope.startswith(f"`{expected}`"), f"{name}: scope {scope!r}, the contract says {expected}"
        assert ("`pricing:write`" in scope) == (name in PRICING_TOOLS), f"{name}: pricing:write"
        assert (level == "read") == _reads(name), f"{name}: level {level!r}"
        assert ("two-step" in level) == ("confirmation" in _inputs(name)[0]), f"{name}: level {level!r}"
        assert ("approval" in level) == (name in APPROVAL_TOOLS), f"{name}: level {level!r}"


def test_pending_tools_are_not_in_the_contract() -> None:
    """A synced tool is checked against the contract itself: take it out of PENDING_TOOLS."""
    synced = sorted(set(PENDING_TOOLS) & set(TOOLS))
    assert not synced, (f"contracts/merchant-mcp-v1.json now has {synced}: delete them from PENDING_TOOLS in "
                        "tests/test_mcp_contract.py, and fix the skills where the contract differs")


def test_pending_tools_are_emptied_by_the_next_sync() -> None:
    """Pinned to the contract's bytes, not its api_revision: the store can change its contract within a revision."""
    digest = load_json(ROOT / "contracts" / "MANIFEST.json")["files"]["merchant-mcp-v1.json"]["sha256"]
    assert not PENDING_TOOLS or digest == PENDING_CONTRACT_SHA256, (
        f"the contract was synced (sha256 {digest[:12]}), but PENDING_TOOLS still lists {sorted(PENDING_TOOLS)}: "
        "every skill tool must be in the synced contract. Empty PENDING_TOOLS (or, for a deliberate partial sync, "
        "check every entry left and set PENDING_CONTRACT_SHA256 to the new digest)")


def test_the_parser_finds_what_it_should() -> None:
    sample = ("| Step | MCP tool |\n| --- | --- |\n| a | `get_order(order_id)` |\n| b | `needs_attention` |\n"
              "| c | `list_orders`, `get_order` and `list_payments` (with `include_closed`) |\n"
              "| d | `list_tickets(include_closed, limit)` with `include_closed` false |\n"
              "\nprose `list_orders(status, since)` and `len(x)`")
    assert _mcp_column_names(sample) == ["get_order", "needs_attention", "list_orders", "get_order",
                                         "list_payments", "list_tickets"]
    assert _calls(sample) == [("get_order", ["order_id"]), ("list_tickets", ["include_closed", "limit"]),
                              ("list_orders", ["status", "since"])]
    # A misspelled call in prose is named (and so reported), never dropped as unknown; `len(x)` is no tool.
    assert _called_names(sample + " `get_aproval(approval_id)`") == {"get_order", "list_tickets", "list_orders",
                                                                    "get_aproval"}


def _live_check():
    spec = importlib.util.spec_from_file_location("live_check", ROOT / "tools" / "live_check.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_live_check_calls_only_read_tools() -> None:
    module = _live_check()
    for name in module.NO_ARGUMENT_TOOLS:
        assert TOOLS[name]["annotations"]["readOnlyHint"] is True, name
        assert not TOOLS[name]["inputSchema"].get("required"), name
    listed = {name: TOOLS[name] for name in module.NO_ARGUMENT_TOOLS}
    assert module.tools_to_call(TOOLS, listed) == (list(module.NO_ARGUMENT_TOOLS), [])


def test_the_live_check_never_calls_a_tool_the_store_lists_differently() -> None:
    """A listing that differs from the contract, or is not read-only, is reported and never called."""
    module = _live_check()
    changed = json.loads(json.dumps(TOOLS["list_payments"]))
    changed["inputSchema"].setdefault("required", []).append("cursor")
    writable = json.loads(json.dumps(TOOLS["list_stock"]))
    writable["annotations"]["readOnlyHint"] = False
    contract_view = {**TOOLS, "list_stock": writable}  # even when the contract itself says so
    calls, problems = module.tools_to_call(contract_view, {"get_store": TOOLS["get_store"], "list_payments": changed,
                                                           "list_stock": writable})
    assert calls == ["get_store"]
    assert problems == ["list_stock: not read-only, not called", "list_payments: differs from the contract, not called"]


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
    "create_category": [*ENVELOPE, "summary", "details", "id", "expires_at", "title", "is_active"],
    "delete_category": [*ENVELOPE, "summary", "details", "id", "expires_at"],
    # Pending (see PENDING_TOOLS): checked once the contract has the tool.
    "list_coupons": ["data", "next_cursor", "code", "pct_off", "is_active", "max_uses", "per_user_max_uses",
                     "expires_at", "created_at", "uses", "paid", "open_checkouts"],
    "get_item_stock": ["voidable", "holds"],
    "stage_key_import": ["staged_import", "id", "expires_at", "keys", "would_add", "duplicates", "too_long",
                         "available_now", "available_after", "turns_on_key_delivery", "members_only", "comma_lines",
                         "hidden"],
    "reply_ticket": [*ENVELOPE, "delivered"],
    "get_approval": ["id", "operation", "target", "status", "effect", "expires_at", "created_at", "decided_at",
                     "result", "error"],
}


@pytest.mark.parametrize("tool", sorted(RESULT_FIELDS))
def test_the_result_fields_the_skills_read_exist(tool: str) -> None:
    if tool in PENDING_TOOLS:
        pytest.skip(f"{tool} is pending a contract sync (PENDING_TOOLS)")
    schema = TOOLS[tool]["outputSchema"]
    properties = set(schema.get("properties", {}))
    for definition in schema.get("$defs", {}).values():
        properties |= set(definition.get("properties", {}))
    missing = [field for field in RESULT_FIELDS[tool] if field not in properties]
    assert not missing, f"{tool} no longer returns {missing}"


def test_the_contract_is_plain_json_with_sorted_keys() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"
