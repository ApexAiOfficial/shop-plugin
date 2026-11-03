"""Shared paths and parsers for the plugin's tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "shop"
SKILLS_DIR = PLUGIN / "skills"
SKILLS = sorted(path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md"))
EXPECTED_SKILLS = ["catalog", "coupons", "custom-orders", "memberships", "orders", "reviews", "sales", "setup", "shop",
                   "stock", "store-health", "support"]
CONTRACT = ROOT / "contracts" / "merchant-mcp-v1.json"

#: Every Markdown file a user or an agent reads: the skills and their references, the READMEs and the docs.
SKILL_FILES = sorted(SKILLS_DIR.glob("**/*.md"))
DOC_FILES = sorted([ROOT / "README.md", PLUGIN / "README.md", *(ROOT / "docs").glob("*.md")])


def load_json(path: Path) -> dict:
    """A JSON file as a dict."""
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """(the ``key: value`` front matter of a Markdown file, its body)."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---\n(.*)\Z", text, re.S)
    assert match, f"{path} has no front matter"
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        assert sep and re.fullmatch(r"[a-z][a-z0-9_-]*", key), f"{path}: unexpected front matter line {line!r}"
        meta[key] = value.strip()
    return meta, match.group(2)


def without_code_blocks(text: str) -> str:
    """TEXT with fenced code blocks removed."""
    return re.sub(r"^```.*?^```[ \t]*$", "", text, flags=re.S | re.M)


def contract() -> dict:
    """The vendored MCP contract."""
    return load_json(CONTRACT)


def tools() -> dict[str, dict]:
    """The contract's tools, by name."""
    return {tool["name"]: tool for tool in contract()["tools"]}
