# Changelog

All notable changes to this plugin are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/).

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
