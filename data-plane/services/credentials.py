"""Utilities for generating cluster credentials."""

import secrets
from dataclasses import dataclass


@dataclass
class ClusterCredentials:
    """Credentials for a ClickHouse cluster."""

    username: str
    password: str


def generate_credentials() -> ClusterCredentials:
    """Generate random credentials for a new cluster.

    Generates:
    - Username: user{16-char hex string}
    - Password: 24-char hex string

    Equivalent to:
    - Username: f"user{openssl rand -hex 8}"
    - Password: openssl rand -hex 12

    Returns:
        ClusterCredentials with generated username and password
    """
    # Generate random strings using secrets module (cryptographically secure)
    # secrets.token_hex(n) generates n random bytes and returns as 2n hex chars
    username_suffix = secrets.token_hex(8)  # 16 hex chars
    password = secrets.token_hex(12)  # 24 hex chars

    username = f"user{username_suffix}"

    return ClusterCredentials(username=username, password=password)
