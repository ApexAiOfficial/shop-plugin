# Shop Bot plugin for Claude Code

Run your [Shop Bot](https://apexaiofficial.com) store in plain language: ask how sales are going and what
needs attention, then add and price products, publish or hide them, create coupons, import licence keys,
answer support tickets and restore a buyer's downloads. The plugin connects Claude Code to your store's own
MCP server with an API token you create in Telegram. The token decides what Claude may change; deletions and
other destructive changes take a second, confirmed call, and big ones (deep price cuts, large coupons,
replies with contact details, broadcasts) wait until you tap Approve in Telegram. Refunds never go through
the plugin.

| | |
| --- | --- |
| Version | 0.3.0, unreleased (0.1.0, the current release, only reads) |
| Status | Reads and changes, with confirmations and Telegram approvals enforced by the store |
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
- [How changes work](#how-changes-work)
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
- twelve skills that teach Claude which tool does what, how to present the answer, and the safety rules: make
  only the changes you asked for, show you the effect of a two-step change before confirming it, never call
  a change done while it waits for your Approve, and treat buyer text as data, never instructions.

The store decides what the token may do: a tool your token's scopes do not allow is not listed at all, and
the store, not the plugin, enforces confirmations, approvals and daily limits.

## Requirements

- Claude Code 2.1 or later.
- A Shop Bot store on the Business plan with the merchant API on. If `/apitoken` in your store bot says the API
  is not available, write to support@apexaiofficial.com.
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

1. In a private chat with your store bot, send `/apitoken new Claude` (any name). Choose what it may do:
   - **Read-only:** sales, catalog, stock, orders, payments, coupons, reviews and custom-order requests;
     changes nothing;
   - **Support:** reply to and close support tickets, restore an order's downloads, read orders and the
     catalog (no buyer ids, coupons or catalog changes);
   - **Catalog and stock:** Read-only plus creating, editing, pricing, publishing and deleting items and
     categories, membership plan prices and switches, version labels, and licence-key imports;
   - **Full:** everything, buyer Telegram ids, coupons, broadcasts, review moderation and custom-order
     questions and rejections included.

   Pick the smallest preset that does the job, and an expiry. The bot shows the token once, with a copy
   button, and the store's MCP address. Tokens created before your store took changes through the API stay
   read-only: create a new one to change anything.
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
| `shop` | What the plugin can do, which tool does what, scopes, levels, limits and error codes |
| `setup` | Connecting, checking the connection, token presets and problems |
| `store-health` | What needs attention: payments waiting for an operator, low stock, open tickets |
| `sales` | Revenue, top items, a period compared with the one before |
| `catalog` | Finding, creating, editing, pricing, publishing, moving and deleting items and categories; variants, bundles, product files, version labels |
| `memberships` | Membership plans: price changes (new joins only; live members keep their price), switching a plan on or off |
| `coupons` | Listing, creating and changing coupons; broadcasts to buyers |
| `stock` | Licence-key counts, key imports (staged, then committed), voiding unsold keys, releasing held keys |
| `orders` | One order, a buyer's orders, open Stars receipts, a refund's state |
| `support` | Open tickets, replies and closing, restoring an order's downloads |
| `reviews` | The review moderation queue, publishing, rejecting or hiding reviews by your rules, responding to buyers |
| `custom-orders` | Custom-order requests: reading briefs, asking the buyer a question, rejecting a request |

## Example prompts

- "What needs my attention in the shop today?"
- "How did sales do in the last 30 days compared with the 30 before? Top items?"
- "Create a 'Templates' category and add a 'Notion budget template' item for 250 Stars."
- "Why is the 'Pro licence' item not on sale? Publish it once it can be."
- "Create a coupon SPRING20: 20% off, 200 uses, ending on 31 May."
- "Import the keys in keys.txt into item 12." (Before reading the file, Claude tells you that keys passing
  through the conversation reach the AI provider, and suggests `/addkeys` with a file for sensitive batches.)
- "Restore the downloads for order 1042, then reply to ticket 31 that the download link was reset, and close
  the ticket."
- "Show the review queue. Publish honest reviews of any rating, reject spam, and draft a thank-you response
  to the 5-star ones for me to check." (Claude shows its plan per review before changing anything; a review's
  own text never decides what happens to it.)
- "Ask the buyer of custom order 7 which file format they need." (Claude shows the question and what the
  buyer will be told, and sends it only after you agree.)
- "Raise the VIP membership to 300 Stars a month." / "Set item 12's version label to v2.1."

## How changes work

Each change is one of three kinds. The store decides which, from the change itself:

- **Direct:** one call. Routine edits: a new item, a new description, a raise, publishing, a reply.
- **Two-step:** deleting items and categories, voiding keys, releasing held keys, switching off a used
  coupon, bulk repricing, changing a membership plan's price or switching a plan off, rejecting or hiding a
  review the rating counts, and asking or rejecting a custom-order buyer. The first call changes nothing and returns the exact effect; Claude shows it to
  you and confirms only after you agree. A confirmation is single use and expires in 5 minutes.
- **Approval:** a price cut to less than half the price (an item, a variant or a bulk reprice), a new variant
  priced under half of the cheapest one, an item added to a bundle that leaves it under half of what its items
  sell for apart, a coupon of 50% or more or with unlimited or more than 1,000 uses, a membership price cut
  to less than half, a support reply, review response or custom-order question or reason with a link or
  contact details, publishing a review that holds them, and every broadcast. The store answers `pending_approval`, and the store bot sends
  the store owner a card in its private chat; nothing happens until the owner taps Approve (within 15
  minutes), and Claude reports the change as waiting until then.

A create, reply or download restore repeated with identical arguments within 10 minutes answers the first
result instead of happening twice, and an edit repeated with the same values changes nothing. A file request
is the exception: each one sends the owner a new prompt. Daily
caps apply per token (500 changes, 20 coupon changes, 50 review changes, 50 texts to buyers: ticket replies
and custom-order questions and rejections together), per ticket (10 replies), per review (5 responses), per
custom order (3 questions), per order (3 download restores) and per store (3 broadcasts). Refunds, resolving
payments, custom-order quotes, other messages to a single buyer, photos and file uploads stay in Telegram.

## Tools

Claude Code names them `mcp__plugin_shop_shop__<tool>`. The store lists only the tools a token's scopes allow.

| MCP tool | Scope | Level |
| --- | --- | --- |
| `get_store` | any token | read |
| `get_approval` | any token with a write scope | read |
| `needs_attention`, `sales_summary` | `reports:read` | read |
| `list_orders`, `get_order`, `list_payments` | `orders:read` (buyer ids and the buyer filter also need `customers:read`) | read |
| `list_categories`, `list_items`, `get_item`, `list_membership_plans` | `catalog:read` | read |
| `list_stock`, `get_item_stock` | `inventory:read` | read |
| `list_coupons` | `coupons:read` | read |
| `list_tickets`, `get_ticket` | `support:read` | read |
| `list_reviews`, `get_review` | `reviews:read` | read |
| `list_custom_orders`, `get_custom_order` | `custom_orders:read` | read |
| `create_category`, `update_category`, `move_category`, `move_item`, `request_product_file`, `set_version_label` | `catalog:write` | direct |
| `update_bundle` | `catalog:write` (and `pricing:write` to add an item) | direct; approval when an add leaves the bundle under half of what its items sell for apart |
| `create_item`, `create_bundle` | `catalog:write` and `pricing:write` | direct |
| `add_variant` | `catalog:write` and `pricing:write` | direct; approval for a price under half of the cheapest variant on sale |
| `update_item`, `update_variant` | `catalog:write` (and `pricing:write` for a price) | direct; approval for a deep price cut |
| `delete_category`, `delete_item` | `catalog:write` | two-step |
| `reprice_items` | `catalog:write` and `pricing:write` | two-step; approval if any cut is deep |
| `set_membership_price` | `catalog:write` and `pricing:write` | two-step; approval for a deep price cut |
| `set_membership_active` | `catalog:write` | direct to switch on; two-step to switch off |
| `create_coupon`, `update_coupon` | `coupons:write` | direct; two-step to switch off a used coupon; approval for a large coupon |
| `stage_key_import`, `commit_key_import` | `inventory:write` | direct (the stage changes nothing) |
| `void_keys`, `release_key_holds` | `inventory:write` | two-step |
| `reply_ticket`, `close_ticket` | `support:write` | direct; approval for a reply with contact details |
| `restore_downloads` | `fulfillment:write` | direct |
| `send_broadcast`, `cancel_broadcast` | `broadcasts:write` | approval to send; direct to cancel |
| `publish_review`, `respond_review` | `reviews:write` | direct; approval with contact details |
| `withhold_review` | `reviews:write` | direct; two-step for a review the rating counts |
| `clarify_custom_order`, `reject_custom_order` | `custom_orders:write` | two-step; approval with contact details |

The full definitions, with input and output schemas, are in
[contracts/merchant-mcp-v1.json](contracts/merchant-mcp-v1.json) (API revision 2026-11-05, 53 tools: the reads, and
every change in the tables above, approvals, broadcasts, variants, bundles, file requests, repricing, reviews,
custom orders, membership plans and version labels included).
Licence-key text, product files, full charge ids and tokens are never returned.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| No shop tools in the session | The plugin is not configured | `/plugin configure shop@shop-plugin`, then `/reload-plugins` |
| `/mcp` shows `shop` failed, 401 | Wrong token, or it expired or was revoked | Create a new token with `/apitoken new <name>` and configure it |
| `/mcp` shows `shop` failed, 404 or 405 | Wrong address, or the API is off for the store | Use the exact address `/apitoken` prints |
| A tool you expected is missing | The token's preset does not include its scope, or your store does not offer that change yet | If "Check my shop connection" shows the scope, a new token does not help; otherwise create a token with a preset that has it |
| No review or custom-order tools | The token was created before your store offered them (a stored token is never widened), or its preset has no such scope (Support, Catalog and stock) | Create a Full token, or a custom one with `reviews:*` or `custom_orders:*` |
| No change tools at all | The token has no write scope (or was created before the store took changes), or changes through the API are off for your store | If the token shows `:write` scopes, ask ApexAi support; otherwise create a Support, Catalog and stock or Full token |
| A change "waits for approval" (`pending_approval`) | It is a deep price cut (a membership plan's included), a new variant under half of the cheapest, a bundle add that leaves the bundle under half of its items' prices, a large coupon, a text to buyers with contact details (a reply, a review response, a custom-order question or reason, or a review to publish) or a broadcast | The store owner taps Approve on the card the store bot sent; ask Claude to check it afterwards |
| `daily_cap` | A daily limit is reached | Wait until the time Claude reports |
| `rate_limited` | A reports or changes budget is spent (too many calls of any kind fail with HTTP 429 instead) | Wait the `retry_after` seconds |
| `window_too_long` | Orders span at most 92 days per call | Ask for shorter periods |

Error codes: [plugins/shop/skills/shop/references/errors.md](plugins/shop/skills/shop/references/errors.md).

## Endpoints contacted

| What | Where | When |
| --- | --- | --- |
| Your store's MCP server | the Store MCP address you configure | Whenever Claude Code starts a session with the plugin on, and on every tool call |

The plugin contacts nothing else, and sends no telemetry.

## Privacy

- The token is sent only to the address you configure, as a bearer header.
- Tool results and everything you send go through your Claude Code conversation, so they reach the AI provider
  your Claude Code uses (for example Anthropic): support ticket text with a Support or Full token, review
  text and custom-order briefs and answers with a Read-only or Full token, buyer Telegram ids with a Full
  token, and **licence keys you import through the conversation**; they also stay in your Claude Code
  session history. For keys that must stay private, use `/addkeys` with a file in the store bot. Reviews and
  custom orders never name their buyer. For the least, create a custom token with only the scopes the task
  needs.
- The store records each token's first use and first change, every change (with the token that made it), and
  every buyer lookup (a buyer filter, or a ticket that shows its buyer), in its audit log.

## Security

See [SECURITY.md](SECURITY.md). In short: the plugin runs no code, the token stays in Claude Code's secure
storage, the store enforces scopes, confirmations, approvals and daily caps on every change, and the skills
make only the changes you ask for and treat buyer and merchant text as data, never instructions. Keep Claude
Code asking before it runs the store's destructive tools; the store marks them `destructiveHint`.

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
