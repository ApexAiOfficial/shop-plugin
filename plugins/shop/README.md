# Shop Bot

Ask about your Shop Bot store in plain language from Claude Code: sales reports, what needs attention, catalog
and licence-key stock, orders and Stars payments, and support tickets. The plugin connects to your store's own
MCP server with an API token you create in Telegram, and every one of its 12 tools only reads.

## Configure

1. In a private chat with your store bot, send `/apitoken new Claude` and pick Read-only or Operations (adds
   support tickets and buyer ids). Copy the token and the MCP address the bot shows.
2. Run `/plugin configure shop@shop-plugin`, enter the address and the token, then `/reload-plugins`.
3. Ask "Check my shop connection."

Never paste the token into the chat. The token is kept in Claude Code's secure storage and sent only to the
address you configured.

## Skills

`shop` (overview), `setup`, `store-health`, `sales`, `catalog`, `orders` and `support`.

Full documentation, privacy and troubleshooting: https://github.com/ApexAiOfficial/shop-plugin
