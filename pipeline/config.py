# pipeline/config.py
"""Deployment parameters. No logic lives here."""

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/"
    "opensky-network/protocol/openid-connect/token"
)
STATES_URL = "https://opensky-network.org/api/states/all"

# Edwards AFB / Antelope Valley
BBOX = {
    "lamin": 34.0,
    "lomin": -119.0,
    "lamax": 35.7,
    "lomax": -117.0,
}

REQUEST_TIMEOUT = 30  # seconds; requests has no default