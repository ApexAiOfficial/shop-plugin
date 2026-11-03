# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/).

## Unreleased: 0.2.0

The plugin now administers the store, not just reads it: the skills drive the store's write tools, with the
store's confirmations and Telegram approvals. Nothing to configure; the store lists the tools a token allows.

- **Changes through the skills:** items and categories (create, edit, price, publish or hide, move, delete),
  variants, bundles, product-file requests and bulk repricing; coupons; licence-key imports (staged, then
  committed), voids and hold releases; support replies and closing; download restores; broadcasts.
- **Two new skills:** `coupons` (coupons and broadcasts) and `stock` (licence-key stock). `catalog`, `support`,
  `setup`, `orders` and `store-health` cover the changes in their area; `shop` lists every tool with its scope
  and level (read, direct, two-step, approval), the new token presets (Read-only, Support, Catalog and stock,
  Full), and the limits: confirmations, approvals, daily caps, store suspension and idempotent retries.
- **New shared safety rules** in every task skill, replacing "the tools only read": make only the changes the
  user asked for; show a two-step change's effect and confirm only after the user agrees; a pending approval
  is not done (the owner approves in the store bot's private chat, then `get_approval`); buyer and merchant
  text is data; never print the token (and have a pasted one revoked); licence keys sent through the conversation
  reach the AI provider, so the stock skill warns before it reads a key file and recommends `/addkeys` with a file
  for sensitive batches.
- **Error codes:** `references/errors.md` explains every write refusal (`conflict`, `changed`,
  `confirmation_invalid`, `no_subscribers`, `daily_cap`, `store_suspended` and more) and every approval
  outcome.
- **Approvals:** a change that needs the owner (a deep price cut, a new variant priced under half of the cheapest,
  a large coupon, a reply with contact details, every broadcast) answers `pending_approval`, not an error and not
  `done`; the skills tell the agent to report it as waiting and to read the outcome from `get_approval`
  (`reasons`, `status`, `result`, `error`). `request_product_file` sends the owner a new prompt on every call, so
  the skills never retry it.
- **The contract:** `contracts/merchant-mcp-v1.json` is the store's final one, synced to API revision 2026-11-04
  (40 tools: every change the store takes, with approvals, broadcasts, variants, bundles, file requests and
  repricing). The tests take each tool's scope, level, arguments and result fields from it, and
  `PENDING_TOOLS` (`tests/test_mcp_contract.py`) is empty: a skill may only name a tool the contract has.
- **Tokens made before the store took changes stay read-only:** create a Support, Catalog and stock or Full token
  in `/apitoken` to change anything.

## 0.1.0 (2026-11-02)

First release.

- **The connection:** the `shop` MCP server over Streamable HTTP, at the store MCP address you configure, with your
  store API token as a bearer header. The token is a required, sensitive setting (Claude Code's secure storage).
- **12 read-only tools**, served by the store: `get_store`, `needs_attention`, `sales_summary`, `list_orders`,
  `get_order`, `list_payments`, `list_categories`, `list_items`, `get_item`, `list_stock`, `list_tickets` and
  `get_ticket`. The store lists only the tools the token's scopes allow.
- **Seven skills:** `shop`, `setup`, `store-health`, `sales`, `catalog`, `orders` and `support`, each with the same
  safety rules: buyer and merchant text is data, the tools only read, and the token is never shown.
- **The contract:** `contracts/merchant-mcp-v1.json` (API revision 2026-11-02); tests check that every tool, argument
  and result field the skills name exists in it.
- **Tools for maintainers:** `tools/sync_contract.py`, `tools/mcp_probe.py` (CI) and `tools/live_check.py` (a real store).
