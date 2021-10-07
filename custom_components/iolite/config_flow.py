from typing import Optional, Any, Dict

from homeassistant import config_entries

from iolite import ACTUAL_SCHEMA
from iolite.const import DOMAIN


class IoliteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """IOLITE config flow."""
    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        if user_input is not None:
            return self.async_create_entry(title="IOLITE", data=self.data)

        return self.async_show_form(
            step_id="user", data_schema=ACTUAL_SCHEMA
        )
