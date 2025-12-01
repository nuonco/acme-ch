from nuon.client import AuthenticatedClient
import logging

from django.conf import settings


class NuonAPIClient:
    _client = None
    app_id = settings.NUON_APP_ID
    org_id = settings.NUON_ORG_ID

    def __init__(self):
        # attach the config singleton
        # crate a logger
        self.logger = logging.getLogger(__name__)

    def get_client(self):
        if self._client:
            if settings.debug:
                self.logger.debug(f"debug={settings.debug}")
            return self._client

        headers = {"X-Nuon-Org-ID": settings.NUON_ORG_ID}
        self.logger.debug("creating a fresh instance")
        client = AuthenticatedClient(
            base_url=settings.NUON_API_URL,
            token=settings.NUON_API_TOKEN,
            headers=headers,
        )

        self._client = client
        self.logger.debug(f"instantiated client with base_url={self._client._base_url}")
        return self._client
