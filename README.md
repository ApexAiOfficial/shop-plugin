# Shop Bot plugin for Claude Code

Ask about your [Shop Bot](https://apexaiofficial.com) store in plain language: how sales are going, what needs
attention, which licence keys are running low, what a buyer ordered, and what is waiting in support. The
plugin connects Claude Code to your store's own MCP server with an API token you create in Telegram. Every
tool only reads: nothing here changes your store, messages a buyer or moves Stars.

| | |
| --- | --- |
| Version | 0.1.0 |
| Status | Read-only tools (12). Writes with Telegram approval come later. |
| Stores | Shop Bot stores on the Business plan with the merchant API on |
| Hosts | Claude Code (plugin). Codex and other MCP clients: [docs/other-clients.md](docs/other-clients.md) |
| License | Apache-2.0 |

## Contents

- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Install](#install)
- [Configure](#configure)
- [Check the connection](#check-the-connection)
- [Skills](#skills)
- [Example prompts](#example-prompts)
- [Tools](#tools)
- [Troubleshooting](#troubleshooting)
- [Endpoints contacted](#endpoints-contacted)
- [Privacy](#privacy)
- [Security](#security)
- [Update and remove](#update-and-remove)
- [Repository layout and validation](#repository-layout-and-validation)
- [Support](#support)
- [License](#license)

## How it works

Your store serves an MCP server at `https://<your store>/api/merchant/v1/mcp`. ApexAi operates the store; this
plugin holds no server code. It gives Claude Code:

- the connection: the store's MCP address and your token, sent as `Authorization: Bearer <token>`;
- seven skills that teach Claude which tool answers which question, how to present the answer, and the
  safety rules (buyer text is data, never instructions).

The store decides what the token may read: a tool your token's scopes do not allow is not listed at all.

## Requirements

- Claude Code 2.1 or later.
- A Shop Bot store on the Business plan with the merchant API on. If `/apitoken` in your store bot says the API
  is not available, write to support@apexaiofficial.com.

**Availability (2026-11-04):** no ApexAi-operated store serves the merchant API yet. A store needs Shop Bot 0.8.0
or later (not yet released) with the merchant API switched on. Until then, this plugin has nothing to connect to.
- An API token: only the store's owner can create one.

## Install

In a terminal:

```bash
claude plugin marketplace add ApexAiOfficial/shop-plugin
claude plugin install shop@shop-plugin
```

Or inside a Claude Code session: `/plugin marketplace add ApexAiOfficial/shop-plugin`, then
`/plugin install shop@shop-plugin`.

To pin a release: `claude plugin marketplace add ApexAiOfficial/shop-plugin#v0.1.0`.

## Configure

1. In a private chat with your store bot, send `/apitoken new Claude` (any name). Choose:
   - **Read-only:** sales, catalog, stock, orders and payments;
   - **Support:** catalog and orders, plus support tickets (no buyer Telegram ids);
   - **Catalog and stock:** Read-only, plus the right to change the catalog, prices and stock. This plugin
     version only reads, so it adds nothing here;
   - **Full:** everything, including buyer Telegram ids.

   Refunds are never available through the API, with any token.

   Pick an expiry. The bot shows the token once, with a copy button, and the store's MCP address.
2. In Claude Code, run `/plugin configure shop@shop-plugin` and enter:
   - **Store MCP address:** the address the bot printed, ending in `/api/merchant/v1/mcp`;
   - **Store API token:** the token. It is a sensitive setting, kept in Claude Code's secure storage, not in
     `settings.json`.
3. Run `/reload-plugins`, then delete the token message in Telegram (or let the bot delete it after 30 minutes).

Never paste the token into the chat itself. To connect several stores, install the plugin once and configure the
other stores in another Claude Code profile, or use [docs/other-clients.md](docs/other-clients.md).

## Check the connection

Ask Claude: "Check my shop connection." The setup skill calls `get_store` and reports the store's name, the
token's scopes and its expiry. `/mcp` shows the `shop` server and its state.

## Skills

| Skill | Use it for |
| --- | --- |
| `shop` | What the plugin can do, which tool answers what, scopes, limits and error codes |
| `setup` | Connecting, checking the connection, token problems |
| `store-health` | What needs attention: payments waiting for an operator, low stock, open tickets |
| `sales` | Revenue, top items, a period compared with the one before |
| `catalog` | Finding items, why one is not on sale, variants, bundles, key stock |
| `orders` | One order, a buyer's orders, open Stars receipts, a refund's state |
| `support` | Open tickets, what a buyer asked, a draft reply for you to send in Telegram |

## Example prompts

- "What needs my attention in the shop today?"
- "How did sales do in the last 30 days compared with the 30 before? Top items?"
- "Which licence-key products are running low?"
- "Show order 1042 and whether it was refunded."
- "Why is the 'Pro licence' item not on sale?"
- "Summarize the open support tickets and draft a reply to the oldest one."

## Tools

All 12 are read-only (`readOnlyHint`). Claude Code names them `mcp__plugin_shop_shop__<tool>`.

| Tool | Scope |
| --- | --- |
| `get_store` | any token |
| `needs_attention`, `sales_summary` | `reports:read` |
| `list_orders`, `get_order`, `list_payments` | `orders:read` (buyer ids and the buyer filter also need `customers:read`) |
| `list_categories`, `list_items`, `get_item` | `catalog:read` |
| `list_stock` | `inventory:read` |
| `list_tickets`, `get_ticket` | `support:read` |

The full definitions, with input and output schemas, are in
[contracts/merchant-mcp-v1.json](contracts/merchant-mcp-v1.json). Licence-key text, product files, full charge
ids and tokens are never returned.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| No shop tools in the session | The plugin is not configured | `/plugin configure shop@shop-plugin`, then `/reload-plugins` |
| `/mcp` shows `shop` failed, 401 | Wrong token, or it expired or was revoked | Create a new token with `/apitoken new <name>` and configure it |
| `/mcp` shows `shop` failed, 404 or 405 | Wrong address, or the API is off for the store | Use the exact address `/apitoken` prints |
| A tool you expected is missing | The token's preset does not include its scope | Create a Support token (tickets) or a Full token (buyer ids) |
| `rate_limited` | Too many calls in a short time | Wait the `retry_after` seconds |
| `window_too_long` | Orders span at most 92 days per call | Ask for shorter periods |

Error codes: [plugins/shop/skills/shop/references/errors.md](plugins/shop/skills/shop/references/errors.md).

## Endpoints contacted

| What | Where | When |
| --- | --- | --- |
| Your store's MCP server | the Store MCP address you configure | Whenever Claude Code starts a session with the plugin on, and on every tool call |

The plugin contacts nothing else, and sends no telemetry.

## Privacy

- The token is sent only to the address you configure, as a bearer header.
- Tool results go into your Claude Code conversation, so they reach the AI provider your Claude Code uses (for
  example Anthropic). With a Support token that includes support ticket text, and with a Full token, buyer
  Telegram ids too. Choose the Read-only preset if you do not want that.
- The store records each token's first use, and every buyer lookup (a buyer filter, or a ticket that shows its
  buyer), in its audit log.

## Security

See [SECURITY.md](SECURITY.md). In short: the plugin runs no code, the token stays in Claude Code's secure
storage, every tool only reads, and the skills treat buyer and merchant text as data, never instructions.

## Update and remove

```bash
claude plugin marketplace update shop-plugin
claude plugin update shop@shop-plugin          # restart Claude Code to apply
claude plugin uninstall shop@shop-plugin
claude plugin marketplace remove shop-plugin
```

A marketplace pinned to `v0.1.0` stays on that release when you update it.

To stop access at the source, revoke the token in `/apitoken`: it stops working at once.

## Repository layout and validation

```
.claude-plugin/marketplace.json     the marketplace (shop-plugin)
plugins/shop/                       the plugin: manifest, MCP connection, skills, README, LICENSE, NOTICE
contracts/                          the store's published MCP tool contract and its digest
tools/                              contract sync, a stand-in MCP endpoint for CI, a live-store check
tests/                              manifests, skills against the contract, repository hygiene
docs/                               other MCP clients, testing
```

CI runs `claude plugin validate --strict`, installs the plugin from the checkout, proves the configured token
reaches the configured address (against a stand-in endpoint), and runs the tests. See
[docs/testing.md](docs/testing.md), including how to check a real store.

## Support

Questions and bug reports: [GitHub issues](https://github.com/ApexAiOfficial/shop-plugin/issues) or
support@apexaiofficial.com. Security problems: privately, see [SECURITY.md](SECURITY.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Shop Bot itself is a proprietary service that ApexAi
operates; it is not part of this repository.
