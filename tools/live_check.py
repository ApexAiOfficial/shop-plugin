"""Check a real store's MCP server against the vendored contract, read-only.

    export SHOP_MCP_URL=https://<your store>/api/merchant/v1/mcp
    read -rs SHOP_API_TOKEN && export SHOP_API_TOKEN     # paste the token; it is not echoed
    python tools/live_check.py

It runs ``initialize`` and ``tools/list``, checks that every listed tool is in contracts/merchant-mcp-v1.json
with the same definition, then calls the listed read tools that need no argument and reports whether they
answered. It never calls a tool that changes the store, even with a write token: a tool in NO_ARGUMENT_TOOLS
is called only when the store lists it exactly as the contract defines it and marks it read-only. The token
travels only in the Authorization header and is never printed; answers are summarized, never shown.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "merchant-mcp-v1.json"
NO_ARGUMENT_TOOLS = ("get_store", "needs_attention", "list_stock", "list_categories", "list_payments")


class Store:
    """A minimal MCP client: one JSON-RPC message per POST, JSON answers."""

    def __init__(self, url: str, token: str) -> None:
        self.url, self._token, self._next = url, token, 0

    def rpc(self, method: str, params: dict | None = None) -> dict:
        self._next += 1
        message = {"jsonrpc": "2.0", "id": self._next, "method": method, "params": params or {}}
        request = urllib.request.Request(
            self.url,
            data=json.dumps(message).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-06-18",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                answer = json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"{method}: HTTP {exc.code} {exc.read()[:200].decode(errors='replace')}") from None
        if "error" in answer:
            raise SystemExit(f"{method}: JSON-RPC error {answer['error']}")
        return answer["result"]


def tools_to_call(contract: dict[str, dict], listed: dict[str, dict]) -> tuple[list[str], list[str]]:
    """(the NO_ARGUMENT_TOOLS to call, problems). A tool is called only when the store lists it with exactly the
    contract's definition and the listing itself marks it read-only; anything else is reported, never called."""
    calls: list[str] = []
    problems: list[str] = []
    for name in NO_ARGUMENT_TOOLS:
        tool = listed.get(name)
        if tool is None:
            continue
        if contract.get(name) != tool:
            problems.append(f"{name}: differs from the contract, not called")
        elif tool.get("annotations", {}).get("readOnlyHint") is not True:
            problems.append(f"{name}: not read-only, not called")
        else:
            calls.append(name)
    return calls, problems


def main() -> int:
    """Exit 0 when the store's tools match the contract and every no-argument tool answers."""
    url, token = os.environ.get("SHOP_MCP_URL", ""), os.environ.get("SHOP_API_TOKEN", "")
    if not url or not token:
        print("Set SHOP_MCP_URL and SHOP_API_TOKEN (see the docstring).", file=sys.stderr)
        return 2
    contract = {tool["name"]: tool for tool in json.loads(CONTRACT.read_text(encoding="utf-8"))["tools"]}
    store = Store(url, token)
    hello = store.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "shop-plugin-live-check", "version": "0.1.0"}})
    print(f"server {hello['serverInfo']['name']} {hello['serverInfo'].get('version', '')}, protocol {hello['protocolVersion']}")
    listed = store.rpc("tools/list")["tools"]
    problems = [f"{tool['name']}: not in the contract or changed" for tool in listed if contract.get(tool["name"]) != tool]
    print(f"{len(listed)} tools listed for this token; {len(listed) - len(problems)} match the contract")
    calls, refused = tools_to_call(contract, {tool["name"]: tool for tool in listed})
    # A changed no-argument tool is already reported above; add only the refusals that say more.
    problems += [p for p in refused if not p.endswith("differs from the contract, not called")]
    for name in calls:
        result = store.rpc("tools/call", {"name": name, "arguments": {}})
        verdict = "error " + json.loads(result["content"][0]["text"]).get("error", "?") if result.get("isError") else "ok"
        print(f"  {name}: {verdict}")
        if result.get("isError"):
            problems.append(f"{name}: {verdict}")
    for problem in problems:
        print(f"PROBLEM {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
