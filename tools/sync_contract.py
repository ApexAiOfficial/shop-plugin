"""Copy Shop Bot's published MCP tool contract into contracts/, and record its size and digest.

    python tools/sync_contract.py path/to/merchant-mcp-v1.json           # copy and update MANIFEST.json
    python tools/sync_contract.py --check path/to/merchant-mcp-v1.json   # exit 1 if contracts/ differs

The contract is the ``tools/list`` a full-scope token sees, with each tool's scope. The skills are tested
against it (tests/test_mcp_contract.py), so a tool the store renames or drops fails the tests here first.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "merchant-mcp-v1.json"
TARGET = ROOT / "contracts" / NAME
MANIFEST = ROOT / "contracts" / "MANIFEST.json"


def _load(path: Path) -> bytes:
    data = path.read_bytes()
    document = json.loads(data)
    if not isinstance(document.get("tools"), list) or not document["tools"]:
        raise SystemExit(f"{path}: not an MCP tool contract (no tools)")
    return data


def main(argv: list[str] | None = None) -> int:
    """Copy the contract, or compare it with ``--check``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help=f"a copy of {NAME}")
    parser.add_argument("--check", action="store_true", help="compare only")
    args = parser.parse_args(argv)
    data = _load(args.source)
    if args.check:
        same = TARGET.exists() and TARGET.read_bytes() == data
        print("contract up to date" if same else f"contracts/{NAME} differs from {args.source}")
        return 0 if same else 1
    TARGET.write_bytes(data)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["api_revision"] = json.loads(data)["api_revision"]
    manifest["synced"] = datetime.date.today().isoformat()
    manifest["files"] = {NAME: {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"contracts/{NAME}: {len(json.loads(data)['tools'])} tools, revision {manifest['api_revision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
