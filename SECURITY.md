# Security

## Reporting a vulnerability

Please report security problems privately, by email to support@apexaiofficial.com. Do not open a public issue
for a vulnerability.

Include what you found, how to reproduce it, the plugin version and your Claude Code version. We aim to
acknowledge reports within a few days.

## What the plugin promises

- **Your token goes only to your store's MCP address.** It is a `sensitive` plugin setting: entered in a masked
  field, kept in Claude Code's secure storage rather than `settings.json` (on Linux, Claude Code keeps it in a
  `.credentials.json` file readable only by your user), and substituted only into the `Authorization` header of
  the MCP server you configured. Use an `https://` address for any host but your own machine.
- **No code runs from this plugin.** It ships skills (Markdown), manifests and the MCP connection settings: no
  hooks, no executables, no scripts, no network code, no telemetry.
- **Changes stay within what you asked for.** The tools change the store only as far as the token's scopes allow.
  Every skill tells the agent to make only the changes the user asked for, to show the effect of a two-step change
  and confirm it only after the user agrees, never to split a change to avoid a confirmation or an approval, and
  never to report a change as done while it waits for the owner's Approve. No tool refunds or otherwise moves
  Stars.
- **Buyer and merchant text is untrusted.** Every skill tells the agent to treat item text, ticket subjects and
  messages, and refund reasons as data, never as instructions, and not to let them choose the next tool call,
  argument, URL, file or setting.
- **Licence keys sent through the conversation reach the AI provider.** The stock skill says so before it reads a
  key file or asks for keys, and recommends a file import outside the conversation (`/addkeys` with a file in the
  store bot) for keys that must stay private.
- **Tokens stay out of the conversation.** The skills never ask for a token in chat and never print one. If a token
  is pasted into a chat, revoke it in `/apitoken` and create a new one.

## What the store enforces

These are properties of the store, which ApexAi operates, not of this plugin: tokens are scoped and expire, any
admin can revoke one at once, the store lists only the tools a token's scopes allow, and it never returns
licence-key text, product files or full charge ids. For changes, the store issues single-use confirmations bound
to the token, the tool and the arguments; sends deep price cuts (a new variant priced under half of the cheapest
included), large coupons, replies with contact details and broadcasts to the owner's Approve in Telegram (the
change answers `pending_approval` and waits); applies daily caps; never applies a repeated identical change twice
(a product-file request, which only messages the owner, is the exception); and records every change, with the
token that made it, in its audit log, as it records each token's first use and every buyer lookup.

## Scope

This repository covers the plugin: its manifests, MCP configuration, skills, contract copy and maintainer tools.
Shop Bot itself is a proprietary service that ApexAi operates; report a vulnerability in it the same way, by email
to support@apexaiofficial.com.
