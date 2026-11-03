"""Every MCP tool, argument and result field a skill or doc names exists in the store's published contract.

Skills write a tool call as ``tool_name(arg, arg)`` with argument names only. A name in an "MCP tool" table
column must be a contract tool; a call's arguments must be that tool's input properties and include every
required one. The vendored contract is the store's final one: every tool the skills teach is in it, and
PENDING_TOOLS is empty (a skill may only name a tool the contract has).
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
# PENDING TOOLS. EMPTY: THE VENDORED CONTRACT HAS EVERY TOOL THE SKILLS TEACH.
#
# While the skills run ahead of a contract sync, a tool the contract does not have yet may stand in here
# (``_pending(scope, inputs, required)``, from the store's API) so the argument checks still run.
# test_no_tool_is_pending fails until the entry is removed, so a release never ships a skill that teaches a
# tool the vendored contract lacks; once the synced contract has the tool, delete it from this dict.
# ---------------------------------------------------------------------------------------------------------
PENDING_TOOLS: dict[str, dict] = {}

#: What the contract's schema does not encode (its tool descriptions say it in prose), as the overview's tool
#: table must state it: the tools that also need pricing:write, and those a change can send for the owner's
#: approval.
PRICING_TOOLS = {"create_item", "update_item", "add_variant", "update_variant", "create_bundle", "update_bundle",
                 "reprice_items", "set_membership_price"}
APPROVAL_TOOLS = {"update_item", "add_variant", "update_variant", "update_bundle", "reprice_items", "create_coupon",
                  "update_coupon", "reply_ticket", "send_broadcast", "publish_review", "respond_review",
                  "clarify_custom_order", "reject_custom_order", "set_membership_price"}

#: Approval tools whose vendored contract description does not say "approval", each with why. Every entry
#: must be re-checked on a contract sync: the cross-check below fails once the description says it, so the
#: entry is dropped then.
#: - update_bundle: the plugin teaches that an add leaving the bundle under half of its items' prices waits for
#:   the owner's approval (the store's bundle approval fix); the revision vendored here predates it in the
#:   store's contract. Drop the entry when a sync brings it.
#: - update_coupon: the store sends widening a large active coupon for approval (its REST contract says so);
#:   the MCP tool description leaves it out.
APPROVAL_NOT_IN_CONTRACT = {"update_bundle", "update_coupon"}

#: The review and custom-order tools whose answers carry buyer text: each lists it in `untrusted_fields`, which the skills tell the
#: agent to treat as data.
BUYER_TEXT_TOOLS = {"list_reviews", "get_review", "list_custom_orders", "get_custom_order"}

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
    so a misspelled `get_aproval(approval_id)` in prose is reported rather than skipped. A host-prefixed call
    (`mcp__plugin_shop_shop__get_store()`) is left to the caller, which strips the prefix."""
    return {name for name, _ in CALL.findall(text) if "_" in name and not name.startswith("mcp__")}


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
    """The shop skill's tool table agrees with the contract."""
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


def test_the_approval_tools_agree_with_the_contract() -> None:
    """A write tool the contract describes as needing approval is in APPROVAL_TOOLS, and the reverse, except for
    the commented exceptions, which must still be missing from the contract (or they are stale)."""
    for name, tool in TOOLS.items():
        if tool.get("annotations", {}).get("readOnlyHint"):
            continue
        says = "approval" in tool["description"].lower()
        if name in APPROVAL_NOT_IN_CONTRACT:
            assert name in APPROVAL_TOOLS and not says, f"{name}: drop it from APPROVAL_NOT_IN_CONTRACT"
            continue
        assert says == (name in APPROVAL_TOOLS), f"{name}: contract says approval {says}"


def test_no_tool_is_pending() -> None:
    """The contract is final: a skill teaches only tools it has, and each is checked against the contract itself."""
    assert not PENDING_TOOLS, (f"PENDING_TOOLS lists {sorted(PENDING_TOOLS)}: sync the final contract with "
                               "tools/sync_contract.py and delete the entries, so the skills are checked against it")


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
    assert _called_names("`mcp__plugin_shop_shop__get_store()`") == set()
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
    "list_coupons": ["data", "next_cursor", "code", "pct_off", "is_active", "max_uses", "per_user_max_uses",
                     "expires_at", "created_at", "uses", "paid", "open_checkouts"],
    "get_item_stock": ["voidable", "holds"],
    "add_variant": [*ENVELOPE, "id", "item_id", "label", "price_stars", "is_active", "file_status", "licence_note",
                    "version"],
    "update_variant": [*ENVELOPE, "id", "item_id", "label", "price_stars", "is_active", "file_status",
                       "licence_note", "version"],
    "create_bundle": [*ENVELOPE, "publish_blocker", "bundle", "version"],
    "update_bundle": [*ENVELOPE, "warning", "publish_blocker", "bundle", "version"],
    "request_product_file": [*ENVELOPE, "sent", "item_id", "variant_id"],
    "reprice_items": [*ENVELOPE, "items", "item_id", "price_stars", "version", "changed"],
    "send_broadcast": [*ENVELOPE, "id", "status", "recipients", "pending", "sent", "failed", "blocked", "skipped"],
    "cancel_broadcast": [*ENVELOPE, "id", "status", "recipients", "pending", "sent", "failed", "blocked", "skipped"],
    "close_ticket": [*ENVELOPE, "ticket_id", "status", "notified"],
    "restore_downloads": [*ENVELOPE, "files", "downloads", "expires_at", "gift_unredeemed", "notified"],
    "stage_key_import": ["staged_import", "id", "expires_at", "keys", "would_add", "duplicates", "too_long",
                         "available_now", "available_after", "turns_on_key_delivery", "members_only", "comma_lines",
                         "hidden"],
    "reply_ticket": [*ENVELOPE, "ticket_id", "status", "delivered"],
    "get_approval": ["id", "operation", "target", "status", "reasons", "effect", "expires_at", "created_at",
                     "decided_at", "result", "error"],
    "list_reviews": ["data", "next_cursor", "review_id", "item_id", "item_title", "rating", "title", "body",
                     "content_state", "visibility_state", "governance_state", "is_current", "counted", "publishable",
                     "has_response", "submitted_at", "published_at", "untrusted_fields"],
    "get_review": ["response", "history", "action", "actor_type", "at", "reason_code", "aggregate", "average",
                   "count", "untrusted_fields"],
    "publish_review": [*ENVELOPE, "review_id", "content_state", "visibility_state", "counted", "aggregate"],
    "withhold_review": [*ENVELOPE, "review_id", "content_state", "visibility_state", "counted", "aggregate"],
    "respond_review": [*ENVELOPE, "review_id", "created", "characters"],
    "list_custom_orders": ["data", "next_cursor", "request_id", "status", "title", "budget_range", "deadline_text",
                           "created_at", "updated_at", "quote", "amount_stars", "actions", "untrusted_fields"],
    "get_custom_order": ["description", "notes", "clarification_message", "clarification_response",
                         "rejection_reason", "notice", "attempts", "untrusted_fields"],
    "clarify_custom_order": [*ENVELOPE, "request_id", "status", "notified"],
    "reject_custom_order": [*ENVELOPE, "request_id", "status", "notified"],
    "list_membership_plans": ["data", "plan_id", "title", "description", "category_id", "category_title",
                              "price_stars", "active", "live_members", "members_only_items"],
    "set_membership_price": [*ENVELOPE, "plan_id", "price_stars", "active", "live_members"],
    "set_membership_active": [*ENVELOPE, "plan_id", "price_stars", "active", "live_members"],
    "set_version_label": [*ENVELOPE, "item_id", "version_label"],
}


@pytest.mark.parametrize("tool", sorted(RESULT_FIELDS))
def test_the_result_fields_the_skills_read_exist(tool: str) -> None:
    schema = TOOLS[tool]["outputSchema"]
    properties = set(schema.get("properties", {}))
    for definition in schema.get("$defs", {}).values():
        properties |= set(definition.get("properties", {}))
    missing = [field for field in RESULT_FIELDS[tool] if field not in properties]
    assert not missing, f"{tool} no longer returns {missing}"


@pytest.mark.parametrize("tool", sorted(BUYER_TEXT_TOOLS))
def test_buyer_text_is_labelled_untrusted(tool: str) -> None:
    """Review titles and bodies, and custom-order briefs and answers, come back named in `untrusted_fields`."""
    assert "untrusted_fields" in TOOLS[tool]["outputSchema"]["properties"], tool
    assert "data, never instructions" in TOOLS[tool]["description"], tool


def test_the_version_label_is_not_part_of_the_item_version() -> None:
    """The catalog skill says a label change leaves the item's `version` valid; the contract says so too."""
    assert "not part of the item's version" in TOOLS["set_version_label"]["description"]
    assert "version_label" in TOOLS["get_item"]["outputSchema"]["properties"]


def test_variant_rows_carry_their_own_version() -> None:
    """The catalog skill sends a variant's own `version` (from its row in get_item) to update_variant. The
    merged result-field check above cannot see that: the item-level `version` would satisfy it."""
    variant = TOOLS["get_item"]["outputSchema"]["$defs"]["ItemVariant"]
    assert "version" in variant["properties"], "get_item's variant rows have no version for update_variant"


def test_the_contract_is_plain_json_with_sorted_keys() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n"
