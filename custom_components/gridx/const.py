"""Constants for the gridX integration."""

from typing import Final

DOMAIN: Final = "gridx"

# Auth0 (E.ON Home)
AUTH0_TOKEN_URL: Final = "https://gridx.eu.auth0.com/oauth/token"
AUTH0_CLIENT_ID: Final = "mG0Phmo7DmnvAqO7p6B0WOYBODppY3cc"
AUTH0_AUDIENCE: Final = "my.gridx"
AUTH0_REALM: Final = "eon-home-authentication-db"
AUTH0_SCOPE: Final = "email openid offline_access"
AUTH0_GRANT_TYPE: Final = "http://auth0.com/oauth/grant-type/password-realm"

# gridX API
API_BASE_URL: Final = "https://api.gridx.de"
API_GATEWAYS_URL: Final = f"{API_BASE_URL}/gateways"
API_LIVE_URL: Final = f"{API_BASE_URL}/systems/{{}}/live"

# Polling
DEFAULT_SCAN_INTERVAL: Final = 60
ERROR_SCAN_INTERVAL_BASE: Final = 120
ERROR_SCAN_INTERVAL_MAX: Final = 900

# Auth cooldown
AUTH_COOLDOWN_SECONDS: Final = 60

# SG Ready states
SG_READY_STATES: Final = ["AUTO", "BOOST", "OFF", "BLOCK"]
