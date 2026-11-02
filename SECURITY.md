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
- **Every tool only reads.** The store's MCP server offers read-only tools; nothing the plugin can do changes the
  store, messages a buyer or moves Stars.
- **Buyer and merchant text is untrusted.** Every skill tells the agent to treat item text, ticket subjects and
  messages, and refund reasons as data, never as instructions, and not to let them choose the next tool call, URL,
  file or setting.
- **Tokens stay out of the conversation.** The skills never ask for a token in chat and never print one. If a token
  is pasted into a chat, revoke it in `/apitoken` and create a new one.

## What the store enforces

These are properties of the store, which ApexAi operates, not of this plugin: tokens are scoped and expire, any
admin can revoke one at once, the store lists only the tools a token's scopes allow, it never returns licence-key
text, product files or full charge ids, and it records each token's first use and every buyer lookup.

## Scope

This repository covers the plugin: its manifests, MCP configuration, skills, contract copy and maintainer tools.
Shop Bot itself is a proprietary service that ApexAi operates; report a vulnerability in it the same way, by email
to support@apexaiofficial.com.
