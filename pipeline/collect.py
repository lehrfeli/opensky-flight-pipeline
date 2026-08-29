import os
import requests
from datetime import datetime, timezone, timedelta

from pipeline.config import TOKEN_URL, STATES_URL, BBOX, REQUEST_TIMEOUT


class TokenManager:
    """Holds an OAuth2 access token and refreshes it when it goes stale.
    Source: https://github.com/openskynetwork/opensky-api/blob/master/python/opensky_api.py
    or https://openskynetwork.github.io/opensky-api/rest.html"""

    def __init__(self):
        self.client_id = os.environ["OPENSKY_CLIENT_ID"]
        self.client_secret = os.environ["OPENSKY_CLIENT_SECRET"]
        self.token = None
        self.expires_at = None

    def get_token(self):
        if self.token is None or datetime.now(timezone.utc) >= self.expires_at:
            self._refresh()
        return self.token

    def _refresh(self):
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        self.token = payload["access_token"]
        self.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=payload["expires_in"] - 30
        )


def fetch_states(token_manager, bbox=BBOX):
    token = token_manager.get_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        STATES_URL,
        headers=headers,
        params=bbox,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()