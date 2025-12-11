"""API client for ACME ClickHouse Control Plane."""

from typing import Any

import httpx

from config import Config, get_config


class APIError(Exception):
    """Raised when API request fails."""

    def __init__(self, status_code: int, message: str, response_data: Any = None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"API Error {status_code}: {message}")


class ACMEClient:
    """Client for interacting with the ACME ClickHouse Control Plane API.

    This client provides methods to fetch organization, state, and cluster
    information from the control plane API.

    Example:
        client = ACMEClient()
        org = client.get_org()
        state = client.get_org_state()
        clusters = client.get_clusters()
    """

    def __init__(self, config: Config | None = None, timeout: float = 30.0):
        """Initialize the API client.

        Args:
            config: Configuration instance. If None, uses get_config()
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.config = config or get_config()
        self.timeout = timeout
        self._client: httpx.Client | None = None

    def __enter__(self) -> "ACMEClient":
        """Context manager entry."""
        self._client = httpx.Client(
            headers=self.config.get_auth_headers(),
            timeout=self.timeout,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client:
            self._client.close()
            self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                headers=self.config.get_auth_headers(),
                timeout=self.timeout,
            )
        return self._client

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle HTTP response and raise appropriate errors.

        Args:
            response: HTTP response object

        Returns:
            Parsed JSON response

        Raises:
            APIError: If request failed
        """
        try:
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                message = error_data.get("detail") or error_data.get("error") or str(e)
            except Exception:
                message = str(e)

            raise APIError(
                status_code=e.response.status_code,
                message=message,
                response_data=error_data if "error_data" in locals() else None,
            ) from e
        except httpx.RequestError as e:
            raise APIError(
                status_code=0,
                message=f"Request failed: {str(e)}",
            ) from e

    def get_org(self) -> dict[str, Any]:
        """Get organization details.

        Returns:
            Dictionary containing organization data

        Raises:
            APIError: If request fails
        """
        url = self.config.get_org_url()
        client = self._get_client()
        response = client.get(url)
        return self._handle_response(response)

    def get_org_install(self) -> dict[str, Any]:
        """Get organization install details.

        Returns:
            Dictionary containing organization install data

        Raises:
            APIError: If request fails
        """
        url = self.config.get_org_install_url()
        client = self._get_client()
        response = client.get(url)
        return self._handle_response(response)

    def get_org_install_state(self) -> dict[str, Any]:
        """Get organization install state including Karpenter outputs.

        Returns:
            Dictionary containing organization install state data

        Raises:
            APIError: If request fails
        """
        url = self.config.get_org_install_state_url()
        client = self._get_client()
        response = client.get(url)
        return self._handle_response(response)

    def get_clusters(self) -> list[dict[str, Any]]:
        """Get list of clusters for the organization.

        Returns:
            List of cluster dictionaries

        Raises:
            APIError: If request fails
        """
        url = self.config.get_clusters_url()
        client = self._get_client()
        response = client.get(url)
        data = self._handle_response(response)

        # Handle both list response and paginated response
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "results" in data:
            return data["results"]
        else:
            return [data]

    def get_cluster(self, cluster_id: str) -> dict[str, Any]:
        """Get details for a specific cluster.

        Args:
            cluster_id: ID of the cluster to retrieve

        Returns:
            Dictionary containing cluster data

        Raises:
            APIError: If request fails
        """
        url = f"{self.config.get_clusters_url()}/{cluster_id}"
        client = self._get_client()
        response = client.get(url)
        return self._handle_response(response)

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
            APIError: If request fails
        """
        url = f"{self.config.get_clusters_url()}/{cluster_id}/update-status"
        client = self._get_client()

        payload = {"status": status}
        if ingress is not None:
            payload["ingress"] = ingress
        if chi is not None:
            payload["chi"] = chi
        if chk is not None:
            payload["chk"] = chk
        if errors is not None:
            payload["errors"] = errors

        response = client.post(url, json=payload)
        return self._handle_response(response)

    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


def create_client(config: Config | None = None) -> ACMEClient:
    """Create a new API client instance.

    Args:
        config: Configuration instance. If None, uses get_config()

    Returns:
        Configured ACMEClient instance
    """
    return ACMEClient(config=config)
