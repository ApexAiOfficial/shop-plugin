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
   - every skill has valid front matter, a route, a failure table and the shared safety rules (changes only as
     asked, confirmations only after the user agrees, pending approvals never reported as done, buyer text as
     data, the token never shown, keys reach the AI provider);
   - every tool, argument and result field the skills and docs name exists in `contracts/merchant-mcp-v1.json`,
     and the overview's tool table gives each tool the contract's scope and a level that matches its annotations;
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
five read tools that need no argument. It never calls a tool that changes the store, whatever the token's scopes:

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

### Tools the contract does not have

None: `PENDING_TOOLS` in `tests/test_mcp_contract.py` is empty, and `test_no_tool_is_pending` keeps it so. If the
skills must teach a tool before the store publishes it, add it there with the scope and inputs the store's API
defines, so the argument checks run meanwhile; sync the contract and delete the entry before the release, because
a skill may only name a tool the vendored contract has.
