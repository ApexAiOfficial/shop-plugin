# Shop tool errors

A refused call comes back as a tool result with `isError` and a JSON body
`{"error": "<code>", "message": "..."}`. Messages never repeat the value that was refused.

| Code | Meaning | Do |
| --- | --- | --- |
| `invalid_arguments` | An argument has the wrong type or range, is unknown, or a required one is missing | Fix the call from the message (it names the argument and the rule) |
| `insufficient_scope` | The token lacks a scope this call needs (`list_orders` with `buyer` needs `customers:read`) | Tell the user which scope; the owner can create a token with that scope (Support for tickets, Full for buyer ids) with `/apitoken new <name>` |
| `not_found` | No item, order or ticket with that id | Check the id with a list tool |
| `bad_cursor` | The cursor came from another list, or was edited | Start the list again without `cursor` |
| `bad_window` | `since` or `until` is not a valid time, or the window starts after it ends | Send RFC 3339 times, `since` before `until` |
| `window_too_long` | `list_orders` covers at most 92 days | Split the period into windows of 92 days or less |
| `rate_limited` | A per-token budget is spent; `retry_after` says how many seconds to wait | Wait, then retry once |
| `result_too_large` | The answer would be over 100,000 characters | Ask for fewer rows (`limit`) or page with `cursor` |
| `conflict` | The store refused the read in its current state | Report the message |

Problems before any tool runs (the plugin shows no shop tools, or the host reports the server as failed):

| Symptom | Cause | Do |
| --- | --- | --- |
| No shop tools at all | The plugin is not configured, or the store refused the connection | Load the setup skill |
| HTTP 401 `unauthorized` | Unknown or mistyped token | Configure the token again |
| HTTP 401 `token_expired`, `token_revoked`, `token_inactive` | The token expired, was revoked, or its creator no longer owns the store | The owner creates a new token |
| HTTP 404 or 405 | Wrong address, or the store's API is not switched on | Check the MCP address `/apitoken` prints; ask ApexAi support if `/apitoken` says the API is unavailable |
| HTTP 429 | Too many connections from this address or failed tokens | Wait a minute |
| A tool the user expects is missing | The token's scopes do not include it | See the scope column in the overview skill |
