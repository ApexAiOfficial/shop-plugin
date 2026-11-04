# Tokens, limits and retries

The detail behind the overview's Tools and Limits sections.

## Token presets

The store owner creates a token in Telegram (`/apitoken` in a private chat with the store bot) from a
preset, or switches each scope on or off for a custom one.

| Preset | Scopes |
| --- | --- |
| Read-only | Every read except `customers:read` and `support:read`: catalog, stock, orders, reports, coupons, reviews and custom orders. Changes nothing |
| Support | `catalog:read`, `orders:read`, `support:read`, `support:write` and `fulfillment:write`: no buyer ids, coupons, catalog changes, reviews or custom orders |
| Catalog and stock | Read-only plus `catalog:write`, `pricing:write` and `inventory:write` (items, prices, membership plans, version labels, keys) |
| Full | Every scope, including `customers:read` (buyer Telegram ids, and `list_orders` with `buyer`), `coupons:write`, `broadcasts:write`, `reviews:write` and `custom_orders:write` |

- Without `customers:read`, buyer ids come back as `null`. Reviews and custom orders never name their buyer,
  whatever the scopes.
- A stored token is never widened. A token created before the store took changes through the API has no
  write scope. A Full, Read-only or Catalog and stock token created before reviews and custom orders has none
  of their scopes (`/apitoken` says so), but it does get the membership plan and version label tools, which
  need only catalog scopes. For anything it lacks, the owner creates a new token.
- A change the store does not offer yet is not listed for any token. When changes through the API are off for
  the store, no change tool is listed at all, whatever the scopes: only reads work, and a new token does not
  help (ApexAi support can say why).

## Pages

Lists return `next_cursor`; pass it back as `cursor` for the next page (with a cursor, `list_orders` keeps
the first page's filters). `list_orders` returns 25 orders a page and spans at most 92 days, and
`list_payments` 20 receipts. `list_items`, `list_coupons`, `list_reviews` and `list_custom_orders` take a
`limit` up to 50; the other lists up to 100. `list_reviews` pages the moderation queue oldest first and the
other views newest first; `list_custom_orders` pages oldest first.

## Budgets

- About 5 calls a second per token (bursts of 20): past that, the store answers HTTP 429 before any tool
  runs, so the host reports the call as failed; wait a second or two and make calls more slowly.
- Whole-window reads (`sales_summary`, and `list_orders` with `summary`) also spend a reports budget of one
  a second (bursts of 5), and changes a write budget of one a second (bursts of 10). Past those a tool
  answers `rate_limited` with `retry_after` seconds: wait that long, never retry in a loop.

## Daily caps

Rolling 24 hours. Past a cap the tool answers `daily_cap` with `retry_after`: tell the user when it frees,
and never retry before.

| Cap | Limit |
| --- | --- |
| Changes | 500 per token |
| Coupon changes | 20 per token |
| Review moderations (`publish_review`, `withhold_review`, `respond_review`) | 50 per token |
| Texts to buyers: ticket replies, custom-order questions and rejections together | 50 per token |
| Replies to one ticket | 10, across tokens |
| Responses to one review | 5, across tokens |
| Questions to one custom order's buyer | 3, across tokens |
| Download restores of one order | 3, across tokens |
| Approval requests | 30 per token, 5 pending at a time |
| Broadcasts | 3 per store, the bot's own included |

## Suspension

While the store is suspended, publishing, switching a membership plan on, creating or widening a coupon,
and broadcasts answer `store_suspended`; other changes still work.

## Retries

- A create (a category, item, variant or bundle), a reply or a download restore repeated with identical
  arguments within 10 minutes is not made twice: it answers the first result with `replayed` true. A change
  that waits for approval answers the same approval. Tell the user the first result stands, and ask how a
  second one should differ; never change their text or numbers yourself to get past it.
- A confirmed call or a key commit sent again answers its first result (`replayed` true); an edit repeated
  with the same values answers `noop` (the same review response, the same version label, the same plan
  price).
- `request_product_file` is neither: every call sends the owner a new prompt, so never repeat it unless the
  user asks.
- A refused call is not stored: fix the cause and call again.

## Never returned, and not through the API

- **Never returned:** licence-key text, product files, full Telegram charge ids, the buyer or order behind a
  review, the buyer of a custom-order request, the token itself.
- **Not through the API:** refunds, resolving payments, invoices, messages to one buyer (other than a ticket
  reply, or a custom-order question or rejection), custom-order quotes, product photos and file uploads
  (`request_product_file` asks the owner for the file), AI settings. The owner does these in Telegram, with
  the store bot's admin commands or its admin app.
