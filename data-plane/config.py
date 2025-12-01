"""Configuration management for ACME ClickHouse Data Plane CLI."""

import os
from dataclasses import dataclass
from typing import Optional


class ConfigError(Exception):
    """Raised when configuration is invalid or incomplete."""

    pass


@dataclass(frozen=True)
class Config:
    """Configuration for the ACME ClickHouse Data Plane agent.

    Attributes:
        api_url: Base URL for the ACME ClickHouse API
        api_token: Authentication token for the API
        org_id: Organization ID for this agent
        in_cluster: Whether running inside a Kubernetes cluster
    """

    api_url: str
    api_token: str
    org_id: str
    in_cluster: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Required environment variables:
            - ACME_CH_API_URL: API base URL
            - ACME_CH_API_TOKEN: API authentication token
            - ACME_CH_ORG_ID: Organization ID

        Optional environment variables:
            - IN_CLUSTER: Set to "true" when running inside Kubernetes cluster (default: false)

        Returns:
            Config instance with loaded values

        Raises:
            ConfigError: If any required environment variable is missing or invalid
        """
        api_url = os.getenv("ACME_CH_API_URL")
        api_token = os.getenv("ACME_CH_API_TOKEN")
        org_id = os.getenv("ACME_CH_ORG_ID")
        in_cluster = os.getenv("IN_CLUSTER", "false").lower() in ("true", "1", "yes")

        missing = []
        if not api_url:
            missing.append("ACME_CH_API_URL")
        if not api_token:
            missing.append("ACME_CH_API_TOKEN")
        if not org_id:
            missing.append("ACME_CH_ORG_ID")

        if missing:
            raise ConfigError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        # Strip trailing slashes from API URL for consistency
        api_url = api_url.rstrip("/")

        return cls(
            api_url=api_url,
            api_token=api_token,
            org_id=org_id,
            in_cluster=in_cluster,
        )

    def get_org_url(self) -> str:
        """Get the full URL for the organization endpoint."""
        return f"{self.api_url}/api/orgs/{self.org_id}"

    def get_org_install_url(self) -> str:
        """Get the full URL for the organization install endpoint."""
        return f"{self.api_url}/api/orgs/{self.org_id}/install"

    def get_org_install_state_url(self) -> str:
        """Get the full URL for the organization install state endpoint."""
        return f"{self.api_url}/api/orgs/{self.org_id}/install-state"

    def get_clusters_url(self) -> str:
        """Get the full URL for the ClickHouse clusters endpoint."""
        return f"{self.api_url}/api/orgs/{self.org_id}/ch-clusters"

    def get_auth_headers(self) -> dict[str, str]:
        """Get HTTP headers with authentication token."""
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }
        return headers


# Global config instance (lazily initialized)
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance.

    Loads configuration from environment on first call.
    Subsequent calls return the cached instance.

    Returns:
        Config instance

    Raises:
        ConfigError: If configuration cannot be loaded
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reload_config() -> Config:
    """Force reload configuration from environment.

    Useful for testing or when environment variables change.

    Returns:
        Newly loaded Config instance

    Raises:
        ConfigError: If configuration cannot be loaded
    """
    global _config
    _config = Config.from_env()
    return _config
