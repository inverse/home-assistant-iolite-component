from unittest.mock import Mock, patch

import pytest
import voluptuous
from homeassistant import data_entry_flow
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from custom_components.iolite import DOMAIN


@pytest.mark.asyncio
async def test_flow_show_form(hass: HomeAssistant) -> None:
    """Test that the setup form is served."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
@patch("custom_components.iolite.config_flow.validate_and_persist_auth")
async def test_flow_invalid_scan_interval_range(
    _validate_and_persist_auth: Mock, hass: HomeAssistant
) -> None:
    """Test that the scan interval range is invalid."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    with pytest.raises(voluptuous.error.MultipleInvalid):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_SCAN_INTERVAL: 10}
        )

    with pytest.raises(voluptuous.error.MultipleInvalid):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_SCAN_INTERVAL: 125}
        )
