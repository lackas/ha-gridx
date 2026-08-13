"""Tests for scripts/update_providers.py (the SPA provider extractor)."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[3] / "scripts" / "update_providers.py"
_spec = importlib.util.spec_from_file_location("update_providers", SCRIPT)
update_providers = importlib.util.module_from_spec(_spec)
# @dataclass resolves its module from sys.modules, so register before exec
sys.modules[_spec.name] = update_providers
_spec.loader.exec_module(update_providers)


def oem_block(realm: str, client_id: str, audience: str, scope: str) -> str:
    """One minified Auth0 config block as the SPA bundle emits it."""
    return (
        f'{{audience:"{audience}",clientDomain:"https://gridx.eu.auth0.com",'
        f'clientID:"{client_id}",realm:"{realm}",tokenScope:"{scope}"}}'
    )


SCOPE = "email openid offline_access"
CURRENT_AUDIENCE = "https://api.gridx.de"
LEGACY_AUDIENCE = "my.gridx"


class TestParseOemBlocks:
    def test_parses_current_audience(self):
        """gridX swapped audience to https://api.gridx.de in August 2026."""
        bundle = (
            'x={companyName:"E.ON"},'
            + oem_block(
                "eon-home-authentication-db",
                "mG0Phmo7DmnvAqO7p6B0WOYBODppY3cc",
                CURRENT_AUDIENCE,
                SCOPE,
            )
            + ",y=1"
        )

        blocks = update_providers.parse_oem_blocks(bundle)

        assert len(blocks) == 1
        assert blocks[0].realm == "eon-home-authentication-db"
        assert blocks[0].client_id == "mG0Phmo7DmnvAqO7p6B0WOYBODppY3cc"
        assert blocks[0].key == "eon_home"

    def test_parses_legacy_audience(self):
        """Older bundles used my.gridx; both shapes must parse."""
        bundle = oem_block("lew-authentication-db", "abc123", LEGACY_AUDIENCE, SCOPE)

        blocks = update_providers.parse_oem_blocks(bundle)

        assert [b.client_id for b in blocks] == ["abc123"]

    def test_excludes_poc_realms(self):
        bundle = oem_block(
            "gridx-poc-1-authentication-db", "abc123", CURRENT_AUDIENCE, SCOPE
        ) + oem_block("lew-authentication-db", "def456", CURRENT_AUDIENCE, SCOPE)

        blocks = update_providers.parse_oem_blocks(bundle)

        assert [b.realm for b in blocks] == ["lew-authentication-db"]

    def test_dedupes_and_sorts(self):
        bundle = (
            oem_block("zero-1-authentication-db", "zzz", CURRENT_AUDIENCE, SCOPE)
            + oem_block("lew-authentication-db", "aaa", CURRENT_AUDIENCE, SCOPE)
            + oem_block("lew-authentication-db", "aaa", CURRENT_AUDIENCE, SCOPE)
        )

        blocks = update_providers.parse_oem_blocks(bundle)

        assert [b.key for b in blocks] == ["lew", "zero_1"]

    def test_raises_when_no_blocks(self):
        with pytest.raises(RuntimeError, match="no Auth0 OEM blocks"):
            update_providers.parse_oem_blocks("var a=1;")


class TestLabels:
    def test_curated_label_wins(self):
        blocks = update_providers.parse_oem_blocks(
            oem_block("egs-authentication-db", "aaa", CURRENT_AUDIENCE, SCOPE)
        )

        assert blocks[0].label == "EGS"

    def test_falls_back_to_title_cased_key(self):
        blocks = update_providers.parse_oem_blocks(
            oem_block("new-oem-authentication-db", "aaa", CURRENT_AUDIENCE, SCOPE)
        )

        assert blocks[0].key == "new_oem"
        assert blocks[0].label == "New Oem"
