# Shop tool errors

A refused call comes back as a tool result with `isError` and a JSON body
`{"error": "<code>", "message": "..."}`. Messages never repeat the value that was refused. A refused change
changed nothing, and some refusals carry more: `current` (the item now), `preview` (a fresh effect and
confirmation), `reasons` (why an approval is needed) or `retry_after` (seconds to wait).

## Any tool

| Code | Meaning | Do |
| --- | --- | --- |
| `invalid_arguments` | An argument has the wrong type or range, is unknown, or a required one is missing | Fix the call from the message (it names the argument and the rule) |
| `insufficient_scope` | The token lacks a scope this call needs (`list_orders` with `buyer` needs `customers:read`; any price needs `pricing:write`) | Tell the user which scope; the owner can create a token with a preset that has it (`/apitoken new <name>`) |
| `not_found` | No item, category, variant, bundle, coupon, order, ticket or approval with that id | Check the id with a list tool |
| `bad_cursor` | The cursor came from another list, or was edited | Start the list again without `cursor` |
| `bad_window` | `since` or `until` is not a valid time, or the window starts after it ends | Send RFC 3339 times, `since` before `until` |
| `window_too_long` | `list_orders` covers at most 92 days | Split the period into windows of 92 days or less |
| `rate_limited` | A per-token reports or changes budget is spent; `retry_after` says how many seconds to wait (too many calls of any kind answer HTTP 429 instead, below) | Wait, then retry once |
| `result_too_large` | The answer would be over 100,000 characters | Ask for fewer rows (`limit`) or page with `cursor` |
| `internal_error` | The store failed unexpectedly | Retry once: a change that went through is not made twice (a create, reply, restore, key commit or confirmed call answers its first result; an edit answers `noop`). Never retry `request_product_file` on your own: each call sends the owner another prompt |

## Changes

| Code | Meaning | Do |
| --- | --- | --- |
| `nothing_to_change` | The call set no field to change | Send the field the user wants changed |
| `not_ready` | The item cannot be published; the message is its publish blocker (no file or keys to deliver, say) | Report the blocker and offer the fix; fix it and publish only if the user asks |
| `not_empty` | The category still holds items | Move or delete them first, or hide the category |
| `no_keys` | The key text held no key | One key per line; nothing was staged |
| `too_many_keys` | More than 1,000 keys in one stage | Split into batches of 1,000 or fewer |
| `nothing_to_stock` | A first key import in which every key was a duplicate or too long | Check the keys; nothing was staged |
| `ticket_closed` | The ticket is closed and takes no reply | Tell the user; the buyer can open a new ticket |
| `invalid_request` | The store refused the change; the message is what the store bot would tell the owner, and may name a Telegram command | Report the message; do not resend the same change |
| `forbidden` | The store does not let this token make that change | Report the message |
| `approval_required` | The change needs the owner's approval, which this store takes only in Telegram so far; `reasons` says why | Tell the user; the owner makes the change in Telegram. Never split it into smaller changes |
| `writes_disabled` | Changes through the API are off for this store | Only read; ApexAi support can say why |
| `conflict` | A change: the item or variant changed since you read its `version`, and `current` holds the item now. A read: the store refused it in its current state | If none of the fields you send changed in `current`, send once more with the new `version` (a variant's from its row in `get_item`); otherwise show the user before and now, and ask. On a second `conflict`, stop and ask. For a read, report the message |
| `changed` | The store changed between the preview and the confirmation; nothing was applied, and `preview` holds a fresh effect and confirmation | Show the new effect; confirm only if the user agrees again |
| `confirmation_invalid` | The confirmation or key stage expired, was already used, belongs to another token, or the arguments differ | Call again without `confirmation` (or stage again) for a fresh preview; show the new effect, and confirm only after the user agrees to it (again, even if they agreed before) |
| `already_exists` | A coupon with this code and other terms exists | Ask: change it with `update_coupon`, or use another code |
| `confirm_key_delivery` | The item does not deliver licence keys yet; the stage is still valid | Ask the user; commit again with `enable_key_delivery` true |
| `open_bot_chat_first` | The owner has no private chat with the store bot, so it cannot ask them for the file | The owner opens a private chat with the bot, then try again |
| `idempotency_in_progress` | The same change is still running | Wait `retry_after` seconds, then retry once |
| `idempotency_key_reused` | An `Idempotency-Key` sent again with other arguments (REST and SDK clients only) | Use a new key for a new change |
| `store_suspended` | The store is suspended: publishing, creating or widening coupons, and broadcasts wait | Tell the user; other changes still work |
| `daily_cap` | A daily limit is reached (see the overview's Limits); `retry_after` says when it frees | Tell the user when; never retry before |
| `busy` | The store is busy with other changes to the same thing | Wait `retry_after` seconds, then retry once |
| `telegram_unavailable` | Telegram did not answer the store | Tell the user; try once more later only if they ask |

## Approval outcomes

`get_approval(approval_id)` reports a change waiting for the owner's Approve. Only `done` means applied.

| `status` | Meaning | Do |
| --- | --- | --- |
| `pending` | Waiting for the owner, until `expires_at` | Remind the user; check again once the owner has decided |
| `done` | The owner approved and the change was applied; `result` holds it | Report the change |
| `rejected` | The owner declined, or the token was revoked | Report it; do not resend unless the user asks |
| `expired` | Nobody decided within 15 minutes | Ask the user whether to request it again |
| `changed` | The store changed before Approve; nothing was applied | Read the current state, and request again only if still wanted |
| `failed` | It could not be applied; `error` says why (`owner_unreachable`, `token_inactive`, or a code above) | Report the error |

## Before any tool runs

Problems before any tool runs (the plugin shows no shop tools, or the host reports the server as failed):

| Symptom | Cause | Do |
| --- | --- | --- |
| No shop tools at all | The plugin is not configured, or the store refused the connection | Load the setup skill |
| HTTP 401 `unauthorized` | Unknown or mistyped token | Configure the token again |
| HTTP 401 `token_expired`, `token_revoked`, `token_inactive` (also as a refused change) | The token expired, was revoked, or its creator no longer owns the store | The owner creates a new token |
| HTTP 404 or 405 | Wrong address, or the store's API is not switched on | Check the MCP address `/apitoken` prints; ask ApexAi support if `/apitoken` says the API is unavailable |
| HTTP 429 | Too many calls through this token (about 5 a second), or too many connections from this address or failed tokens | Wait a second or two and make calls more slowly; after failed tokens, wait a minute |
| A tool the user expects is missing | The token's scopes do not include it, it is a write tool on a token without write scopes, or the store does not offer that change yet | See the scope column in the overview skill; if `get_store` lists the scope, a new token does not help |
| No change tool at all, though `get_store` lists `:write` scopes | Changes through the API are off for this store | Only reads work; ApexAi support can say why. A new token does not help |
