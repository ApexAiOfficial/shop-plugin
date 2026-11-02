# Testing

## What CI checks

`.github/workflows/validate.yml` runs on GitHub-hosted runners only:

1. **Claude Code:** `claude plugin validate --strict` on the marketplace and the plugin; the plugin installs from
   the checkout into an isolated Claude Code home; `claude plugin list --json` shows the MCP server built from
   `userConfig` only; without a token the server is not registered.
2. **The token reaches the address:** the plugin is configured with a probe token and the address of
   `tools/mcp_probe.py`, a stand-in MCP endpoint on loopback. Claude Code must connect, and the probe's log must show an
   authenticated `initialize` and `tools/list` and no request without the token. The probe logs whether the
   header matched, never the header.
3. **Tests:** `python -m pytest tests`:
   - the manifests agree and keep the token a required, sensitive setting;
   - every skill has valid front matter, a route, a failure table and the shared safety rules;
   - every tool, argument and result field the skills and docs name exists in `contracts/merchant-mcp-v1.json`;
   - nothing private, no secrets, only documentation and reserved example hosts, hosted runners only.

## Run them locally

```bash
python -m pip install "pytest>=8"
python -m pytest tests
claude plugin validate --strict .
claude plugin validate --strict ./plugins/shop
```

## Check a real store

`tools/live_check.py` connects to a store with a token, compares the store's tool list with the contract, and calls
each tool that needs no argument (all of them only read):

```bash
export SHOP_MCP_URL=https://shop.example/api/merchant/v1/mcp
read -rs SHOP_API_TOKEN && export SHOP_API_TOKEN
python tools/live_check.py
```

It prints which tools match and which answered, never the token or the answers.

## Update the contract

When the store's tools change, its operators publish a new `merchant-mcp-v1.json`. Copy it in and run the tests:

```bash
python tools/sync_contract.py path/to/merchant-mcp-v1.json
python -m pytest tests
```

A tool, argument or result field the skills use that the new contract drops fails the tests here.
