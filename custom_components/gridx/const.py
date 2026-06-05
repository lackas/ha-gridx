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
API_HISTORICAL_URL: Final = f"{API_BASE_URL}/systems/{{}}/historical"

# Polling
DEFAULT_SCAN_INTERVAL: Final = 60
ERROR_SCAN_INTERVAL_BASE: Final = 120
ERROR_SCAN_INTERVAL_MAX: Final = 900

# Auth cooldown
AUTH_COOLDOWN_SECONDS: Final = 60

# Transient connection retries (DNS timeout, connection refused, etc.)
# Auth0 hostnames have CNAME chains (gridx.eu.auth0.com → pivot.prod.auth0edge.com
# → cdn.cloudflare.net) with 2s TTLs on intermediate hops, making DNS lookups
# more brittle than for single A-record hosts. Retry transient connection
# errors with exponential backoff before giving up to the coordinator.
# HTTP-level errors (4xx, 5xx) are NOT retried here.
CONNECTION_RETRIES: Final = 3
CONNECTION_RETRY_DELAY: Final = 1.0  # seconds, doubles each retry

# hass.data keys
COORDINATOR_LIVE: Final = "live_coordinator"
COORDINATOR_HISTORICAL: Final = "historical_coordinator"

# SG Ready states (from gridX OpenAPI spec)
SG_READY_STATES: Final = ["UNKNOWN", "OFF", "AUTO", "RECOMMEND_ON", "ON"]
