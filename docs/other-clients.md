# Codex and other MCP clients

The store's MCP server works with any MCP client that speaks Streamable HTTP and can send a bearer token. You need
the two values from `/apitoken` in your store bot: the MCP address (ending in `/api/merchant/v1/mcp`) and a token.

Keep the token in an environment variable rather than in a configuration file:

```bash
read -rs SHOP_API_TOKEN && export SHOP_API_TOKEN   # paste the token; it is not echoed
```

## Codex

Add the server to `~/.codex/config.toml` (replace the address with yours):

```toml
[mcp_servers.shop]
url = "https://shop.example/api/merchant/v1/mcp"
bearer_token_env_var = "SHOP_API_TOKEN"
```

Start Codex from the shell where `SHOP_API_TOKEN` is set, and check with `/mcp`. The skills in
`plugins/shop/skills/` are plain Agent Skills: copy the folders you want into `~/.codex/skills/` to give Codex the
same guidance. They name the tools without a host's prefix (`get_store`).

## Claude Desktop and claude.ai

Their remote connectors sign in with OAuth, which Shop Bot stores do not offer yet. Use Claude Code with this
plugin, or Codex, meanwhile.

## Any other client

A generic configuration, for clients that read the common `mcpServers` format:

```json
{
  "mcpServers": {
    "shop": {
      "type": "http",
      "url": "https://shop.example/api/merchant/v1/mcp",
      "headers": { "Authorization": "Bearer ${SHOP_API_TOKEN}" }
    }
  }
}
```

The server is stateless and answers JSON (no event stream). It supports MCP protocol revisions 2025-11-25, 2025-06-18
and 2025-03-26, one JSON-RPC message per request (no batches). Tools and their schemas:
[contracts/merchant-mcp-v1.json](../contracts/merchant-mcp-v1.json).

## Several stores

Give each store its own server entry, with its own address and its own token variable (for example `shop_main` with
`SHOP_MAIN_TOKEN` and `shop_eu` with `SHOP_EU_TOKEN`).
