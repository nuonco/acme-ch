"""Service for interacting with ACME Control Plane API."""

from typing import Any

from client import ACMEClient, APIError
from config import Config


class APIServiceError(Exception):
    """Raised when API service operation fails."""

    pass


class APIService:
    """Service layer for Control Plane API operations.

    Wraps the ACMEClient with additional error handling and data formatting.
    """

    def __init__(self, config: Config | None = None):
        """Initialize the API service.

        Args:
            config: Configuration instance. If None, uses default config.
        """
        self.config = config
        self._client: ACMEClient | None = None

    def _get_client(self) -> ACMEClient:
        """Get or create API client."""
        if self._client is None:
            self._client = ACMEClient(config=self.config)
        return self._client

    def get_org(self) -> dict[str, Any]:
        """Get organization details.

        Returns:
            Organization data dictionary

        Raises:
            APIServiceError: If request fails
        """
        try:
            client = self._get_client()
            return client.get_org()
        except APIError as e:
            raise APIServiceError(f"Failed to get organization: {e.message}") from e

    def get_install(self) -> dict[str, Any]:
        """Get organization install details.

        Returns:
            Install data dictionary

        Raises:
            APIServiceError: If request fails
        """
        try:
            client = self._get_client()
            return client.get_org_install()
        except APIError as e:
            raise APIServiceError(
                f"Failed to get organization install: {e.message}"
            ) from e

    def get_install_state(self) -> dict[str, Any]:
        """Get organization install state including Karpenter outputs.

        Returns:
            Install state data dictionary with Karpenter configuration

        Raises:
            APIServiceError: If request fails
        """
        try:
            client = self._get_client()
            return client.get_org_install_state()
        except APIError as e:
            raise APIServiceError(
                f"Failed to get organization install state: {e.message}"
            ) from e

    def get_clusters(self, cluster_id: str | None = None) -> list[dict[str, Any]]:
        """Get clusters for the organization.

        Args:
            cluster_id: Optional specific cluster ID to fetch

        Returns:
            List of cluster dictionaries (or single-item list if cluster_id provided)

        Raises:
            APIServiceError: If request fails
        """
        try:
            client = self._get_client()

            if cluster_id:
                cluster = client.get_cluster(cluster_id)
                return [cluster]
            else:
                return client.get_clusters()

        except APIError as e:
            context = f"cluster {cluster_id}" if cluster_id else "clusters"
            raise APIServiceError(f"Failed to get {context}: {e.message}") from e

    def update_cluster_status(
        self,
        cluster_id: str,
        status: str,
        ingress: dict[str, Any] | None = None,
        chi: dict[str, Any] | None = None,
        chk: dict[str, Any] | None = None,
        errors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Update cluster status in the control plane.

        Args:
            cluster_id: ID of the cluster to update
            status: Status value (ready, pending, error)
            ingress: Optional ingress resource data
            chi: Optional CHI resource data
            chk: Optional CHK resource data
            errors: Optional list of error messages

        Returns:
            Response data from the API

        Raises:
            APIServiceError: If request fails
        """
        try:
            client = self._get_client()
            return client.update_cluster_status(
                cluster_id=cluster_id,
                status=status,
                ingress=ingress,
                chi=chi,
                chk=chk,
                errors=errors,
            )
        except APIError as e:
            raise APIServiceError(
                f"Failed to update cluster {cluster_id} status: {e.message}"
            ) from e

    def close(self):
        """Close the underlying API client."""
        if self._client:
            self._client.close()
            self._client = None
