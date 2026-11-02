"""The marketplace and manifest agree, and the token reaches the host only as a sensitive setting."""

from __future__ import annotations

import re

from conftest import PLUGIN, ROOT, load_json, without_code_blocks

MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
MANIFEST = PLUGIN / ".claude-plugin" / "plugin.json"
MCP = PLUGIN / ".mcp.json"


def test_the_marketplace_is_shop_plugin_and_points_at_the_plugin() -> None:
    marketplace = load_json(MARKETPLACE)
    assert marketplace["name"] == "shop-plugin"
    assert marketplace["owner"] == {"name": "ApexAiOfficial", "email": "support@apexaiofficial.com"}
    [entry] = marketplace["plugins"]
    assert entry["name"] == "shop"
    assert (ROOT / entry["source"]).resolve() == PLUGIN.resolve()
    assert entry["description"] == load_json(MANIFEST)["description"]


def test_the_manifest() -> None:
    manifest = load_json(MANIFEST)
    assert manifest["name"] == "shop" and re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"])
    assert manifest["license"] == "Apache-2.0"
    assert manifest["author"] == {"name": "ApexAiOfficial", "email": "support@apexaiofficial.com",
                                  "url": "https://github.com/ApexAiOfficial"}
    assert manifest["homepage"] == manifest["repository"] == "https://github.com/ApexAiOfficial/shop-plugin"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {manifest['version']} " in changelog or f"## Unreleased: {manifest['version']}" in changelog


def test_user_config_holds_the_token_as_a_required_secret_and_the_address_without_a_default() -> None:
    config = load_json(MANIFEST)["userConfig"]
    assert set(config) == {"mcp_url", "api_token"}
    token = config["api_token"]
    assert token["type"] == "string" and token["sensitive"] is True and token["required"] is True
    assert "default" not in token
    address = config["mcp_url"]
    assert address["required"] is True and not address.get("sensitive") and "default" not in address
    assert "/api/merchant/v1/mcp" in address["description"]
    for option in config.values():
        assert option["title"] and option["description"]


def test_mcp_takes_url_and_bearer_only_from_user_config() -> None:
    servers = load_json(MCP)["mcpServers"]
    assert servers == {"shop": {"type": "http", "url": "${user_config.mcp_url}",
                                "headers": {"Authorization": "Bearer ${user_config.api_token}"}}}
    text = MCP.read_text(encoding="utf-8")
    # No environment variable, no default and no literal credential: only the declared settings.
    assert set(re.findall(r"\$\{([^}]*)\}", text)) == {"user_config.mcp_url", "user_config.api_token"}


def test_nothing_the_host_would_run() -> None:
    """No hooks, bin, commands, agents or scripts: the plugin is skills and connection settings."""
    for path in ("hooks", "bin", "commands", "agents", "scripts", ".app.json"):
        assert not (PLUGIN / path).exists(), path
    assert "hooks" not in load_json(MANIFEST)
    for file in PLUGIN.rglob("*"):
        if file.is_file():
            assert file.suffix in {".md", ".json", ""}, file
            assert file.stat().st_size < 256 * 1024, file


def test_license_and_notice_ship_inside_the_plugin() -> None:
    for name in ("LICENSE", "NOTICE"):
        assert (PLUGIN / name).read_bytes() == (ROOT / name).read_bytes()
    assert "Apache License" in (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Copyright 2026 ApexAiOfficial" in (ROOT / "NOTICE").read_text(encoding="utf-8")


def test_readmes_are_long_enough_for_the_directory() -> None:
    """Anthropic's directory needs a README of at least 40 words in the plugin folder, outside code blocks."""
    for readme in (ROOT / "README.md", PLUGIN / "README.md"):
        words = re.findall(r"\w+", without_code_blocks(readme.read_text(encoding="utf-8")))
        assert len(words) >= 40, readme


def test_root_readme_documents_install_endpoints_privacy_and_support() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for needle in ("claude plugin marketplace add ApexAiOfficial/shop-plugin",
                   "claude plugin install shop@shop-plugin",
                   "/plugin configure shop@shop-plugin",
                   "## Endpoints contacted", "## Privacy", "## Support", "support@apexaiofficial.com"):
        assert needle in readme, needle
