"""A stand-in MCP endpoint on loopback that records whether each request carried the expected bearer token.

    python tools/mcp_probe.py --port 18766 --key "$PROBE_KEY" --log probe.jsonl &
    ... point Claude Code at http://127.0.0.1:18766/api/merchant/v1/mcp and let it connect ...
    python tools/mcp_probe.py --check probe.jsonl          # exit 1 unless every request was authenticated

It answers ``initialize`` and ``tools/list`` like a stateless Streamable HTTP server (one tool, no work done),
refuses a request without the expected key with 401, and logs only the JSON-RPC method and whether the
``Authorization`` header matched: never the header itself. It proves that a host sends the configured token to
the configured address, without a store or any model call.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def _handler(expected: str, log: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        """POST-only, stateless JSON responses, like a store's MCP endpoint."""

        def log_message(self, *args: object) -> None:      # keep stderr quiet
            return

        def _record(self, method: str, rpc: str | None) -> bool:
            sent = self.headers.get("Authorization")
            verdict = "expected" if sent == expected else ("missing" if sent is None else "other")
            with log.open("a", encoding="utf-8") as out:
                out.write(json.dumps({"http": method, "rpc": rpc, "auth": verdict}) + "\n")
            return verdict == "expected"

        def do_GET(self) -> None:                             # noqa: N802 (http.server naming)
            self._record("GET", None)
            self.send_response(405)
            self.send_header("Allow", "POST")
            self.end_headers()

        def do_POST(self) -> None:                            # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if not self._record("POST", body.get("method")):
                self.send_response(401)
                self.send_header("WWW-Authenticate", "Bearer")
                self.end_headers()
                return
            if "id" not in body:                              # a notification
                self.send_response(202)
                self.end_headers()
                return
            if body.get("method") == "initialize":
                result = {"protocolVersion": body.get("params", {}).get("protocolVersion", "2025-06-18"),
                          "capabilities": {"tools": {"listChanged": False}},
                          "serverInfo": {"name": "shop-probe", "version": "0"}}
            elif body.get("method") == "tools/list":
                result = {"tools": [{"name": "get_store", "description": "Probe only.",
                                     "inputSchema": {"type": "object", "properties": {}}}]}
            else:
                result = {}
            data = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


def check(log: Path) -> int:
    """0 when the log shows an authenticated initialize and tools/list and no unauthenticated request."""
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    methods = {entry["rpc"] for entry in entries if entry["auth"] == "expected"}
    refused = [entry for entry in entries if entry["auth"] != "expected"]
    print(f"{len(entries)} requests; authenticated methods: {sorted(m for m in methods if m)}; refused: {len(refused)}")
    return 0 if {"initialize", "tools/list"} <= methods and not refused else 1


def main(argv: list[str] | None = None) -> int:
    """Serve the probe, or check a probe log."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=18766)
    parser.add_argument("--key", help="the bearer token the host must send")
    parser.add_argument("--log", type=Path, help="where to append one line per request")
    parser.add_argument("--check", type=Path, metavar="LOG", help="verify a probe log instead of serving")
    args = parser.parse_args(argv)
    if args.check:
        return check(args.check)
    if not (args.key and args.log):
        parser.error("--key and --log are required to serve")
    HTTPServer(("127.0.0.1", args.port), _handler(f"Bearer {args.key}", args.log)).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
