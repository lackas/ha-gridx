"""Tests for the gridX config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.gridx.api import (
    GridxApiError,
    GridxAuthenticationError,
    GridxConnectionError,
)
from custom_components.gridx.config_flow import GridxConfigFlow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_hass(existing_entry=None):
    """Create a minimal mock hass object for config flow testing."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=existing_entry)
    hass.config_entries.async_update_entry = MagicMock()
    hass.config_entries.async_reload = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


def make_flow(hass=None, context=None):
    """Instantiate a GridxConfigFlow and inject mock hass."""
    flow = GridxConfigFlow()
    flow.hass = hass or make_hass()
    flow.context = context or {}
    # Provide stub implementations of ConfigFlow helper methods used in tests.
    flow._abort_if_unique_id_configured = MagicMock()
    flow.async_set_unique_id = AsyncMock()
    flow.async_create_entry = MagicMock(
        side_effect=lambda title, data: {
            "type": "create_entry",
            "title": title,
            "data": data,
        }
    )
    flow.async_show_form = MagicMock(
        side_effect=lambda **kwargs: {"type": "form", **kwargs}
    )
    flow.async_abort = MagicMock(
        side_effect=lambda reason: {"type": "abort", "reason": reason}
    )
    return flow


# ---------------------------------------------------------------------------
# User flow tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_flow_shows_form_initially():
    """Calling async_step_user with no input returns a form."""
    flow = make_flow()

    with patch(
        "custom_components.gridx.config_flow.async_get_clientsession",
        return_value=MagicMock(),
    ):
        result = await flow.async_step_user(None)

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result.get("errors", {}) == {}


@pytest.mark.asyncio
async def test_user_flow_success():
    """Valid credentials → CREATE_ENTRY with correct data."""
    flow = make_flow()

    mock_api = MagicMock()
    mock_api.authenticate = AsyncMock()
    mock_api.async_get_gateways = AsyncMock(return_value=["system-id-001"])

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            return_value=mock_api,
        ),
    ):
        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "secret"}
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "gridX Energy Management"
    assert result["data"] == {
        "email": "user@example.com",
        "password": "secret",
        "system_ids": ["system-id-001"],
    }
    flow.async_set_unique_id.assert_awaited_once_with("system-id-001")
    flow._abort_if_unique_id_configured.assert_called_once()


@pytest.mark.asyncio
async def test_user_flow_invalid_auth_then_success():
    """Auth error → form with error → retry with valid creds → CREATE_ENTRY."""
    flow = make_flow()

    mock_api_bad = MagicMock()
    mock_api_bad.authenticate = AsyncMock(
        side_effect=GridxAuthenticationError("bad creds")
    )
    mock_api_bad.async_get_gateways = AsyncMock()

    mock_api_ok = MagicMock()
    mock_api_ok.authenticate = AsyncMock()
    mock_api_ok.async_get_gateways = AsyncMock(return_value=["system-id-001"])

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            side_effect=[mock_api_bad, mock_api_ok],
        ),
    ):
        # First attempt: bad credentials
        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "wrong"}
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}

        # Second attempt: good credentials
        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "correct"}
        )

    assert result["type"] == "create_entry"
    assert result["data"]["email"] == "user@example.com"
    assert result["data"]["password"] == "correct"


@pytest.mark.asyncio
async def test_user_flow_cannot_connect_then_success():
    """Connection error → form with error → retry → CREATE_ENTRY."""
    flow = make_flow()

    mock_api_bad = MagicMock()
    mock_api_bad.authenticate = AsyncMock(side_effect=GridxConnectionError("timeout"))

    mock_api_ok = MagicMock()
    mock_api_ok.authenticate = AsyncMock()
    mock_api_ok.async_get_gateways = AsyncMock(return_value=["system-id-001"])

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            side_effect=[mock_api_bad, mock_api_ok],
        ),
    ):
        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "secret"}
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}

        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "secret"}
        )

    assert result["type"] == "create_entry"


@pytest.mark.asyncio
async def test_user_flow_api_error_then_success():
    """API error → form with error → retry → CREATE_ENTRY."""
    flow = make_flow()

    mock_api_bad = MagicMock()
    mock_api_bad.authenticate = AsyncMock(side_effect=GridxApiError("server error"))

    mock_api_ok = MagicMock()
    mock_api_ok.authenticate = AsyncMock()
    mock_api_ok.async_get_gateways = AsyncMock(return_value=["system-id-001"])

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            side_effect=[mock_api_bad, mock_api_ok],
        ),
    ):
        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "secret"}
        )
        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}

        result = await flow.async_step_user(
            {"email": "user@example.com", "password": "secret"}
        )

    assert result["type"] == "create_entry"


# ---------------------------------------------------------------------------
# Reauth flow tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reauth_flow_shows_form():
    """async_step_reauth delegates to reauth_confirm and shows form."""
    existing_entry = MagicMock()
    existing_entry.data = {
        "email": "user@example.com",
        "password": "old-secret",
        "system_ids": ["system-id-001"],
    }
    existing_entry.entry_id = "entry-abc"

    hass = make_hass(existing_entry=existing_entry)
    flow = make_flow(hass=hass, context={"entry_id": "entry-abc"})

    result = await flow.async_step_reauth(existing_entry.data)

    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"


@pytest.mark.asyncio
async def test_reauth_flow_success():
    """Valid new password → entry updated → abort with reauth_successful."""
    existing_entry = MagicMock()
    existing_entry.data = {
        "email": "user@example.com",
        "password": "old-secret",
        "system_ids": ["system-id-001"],
    }
    existing_entry.entry_id = "entry-abc"

    hass = make_hass(existing_entry=existing_entry)
    flow = make_flow(hass=hass, context={"entry_id": "entry-abc"})

    mock_api = MagicMock()
    mock_api.authenticate = AsyncMock()

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            return_value=mock_api,
        ),
    ):
        result = await flow.async_step_reauth_confirm({"password": "new-secret"})

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"

    # Entry should have been updated with the new password
    hass.config_entries.async_update_entry.assert_called_once()
    call_kwargs = hass.config_entries.async_update_entry.call_args
    updated_data = call_kwargs[1]["data"]
    assert updated_data["password"] == "new-secret"
    assert updated_data["email"] == "user@example.com"

    # Entry should have been reloaded
    hass.config_entries.async_reload.assert_awaited_once_with("entry-abc")


@pytest.mark.asyncio
async def test_reauth_flow_invalid_auth_then_success():
    """Bad password during reauth → form error → retry → reauth_successful."""
    existing_entry = MagicMock()
    existing_entry.data = {
        "email": "user@example.com",
        "password": "old-secret",
        "system_ids": ["system-id-001"],
    }
    existing_entry.entry_id = "entry-abc"

    hass = make_hass(existing_entry=existing_entry)
    flow = make_flow(hass=hass, context={"entry_id": "entry-abc"})

    mock_api_bad = MagicMock()
    mock_api_bad.authenticate = AsyncMock(
        side_effect=GridxAuthenticationError("bad creds")
    )

    mock_api_ok = MagicMock()
    mock_api_ok.authenticate = AsyncMock()

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            side_effect=[mock_api_bad, mock_api_ok],
        ),
    ):
        result = await flow.async_step_reauth_confirm({"password": "wrong"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}

        result = await flow.async_step_reauth_confirm({"password": "correct"})

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"


@pytest.mark.asyncio
async def test_reauth_flow_api_error_then_success():
    """API error during reauth → form error → retry → reauth_successful."""
    existing_entry = MagicMock()
    existing_entry.data = {
        "email": "user@example.com",
        "password": "old-secret",
        "system_ids": ["system-id-001"],
    }
    existing_entry.entry_id = "entry-abc"

    hass = make_hass(existing_entry=existing_entry)
    flow = make_flow(hass=hass, context={"entry_id": "entry-abc"})

    mock_api_bad = MagicMock()
    mock_api_bad.authenticate = AsyncMock(side_effect=GridxApiError("server error"))

    mock_api_ok = MagicMock()
    mock_api_ok.authenticate = AsyncMock()

    with (
        patch(
            "custom_components.gridx.config_flow.async_get_clientsession",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.gridx.config_flow.GridxApi",
            side_effect=[mock_api_bad, mock_api_ok],
        ),
    ):
        result = await flow.async_step_reauth_confirm({"password": "temporary"})
        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}

        result = await flow.async_step_reauth_confirm({"password": "correct"})

    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
