# Shop Bot

Run your Shop Bot store in plain language from Claude Code: sales reports and what needs attention, then
catalog and price changes, coupons, licence-key imports, support replies and download restores. The plugin
connects to your store's own MCP server with an API token you create in Telegram. The token's preset decides
what Claude may change; destructive changes take a confirmed second call, and big ones wait until you tap
Approve in Telegram.

## Configure

1. In a private chat with your store bot, send `/apitoken new Claude` and pick a preset: Read-only (changes
   nothing), Support (tickets and download restores), Catalog and stock (items, prices, categories and
   keys) or Full (everything, coupons and broadcasts included). Copy the token and the MCP address the bot
   shows.
2. Run `/plugin configure shop@shop-plugin`, enter the address and the token, then `/reload-plugins`.
3. Ask "Check my shop connection."

Never paste the token into the chat. The token is kept in Claude Code's secure storage and sent only to the
address you configured. Licence keys you import through the chat reach the AI provider: use `/addkeys` with
a file in the store bot for keys that must stay private.

## Skills

`shop` (overview), `setup`, `store-health`, `sales`, `catalog`, `coupons`, `stock`, `orders` and `support`.

Full documentation, privacy and troubleshooting: https://github.com/ApexAiOfficial/shop-plugin
