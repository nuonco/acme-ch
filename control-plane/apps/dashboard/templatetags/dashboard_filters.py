from django import template

register = template.Library()


@register.filter
def humanize_nanoseconds(nanoseconds):
    """
    Convert nanoseconds to a human-readable duration.

    Examples:
        - 1500000000 ns -> "1.5s"
        - 500000000 ns -> "500ms"
        - 1200000 ns -> "1.2ms"
        - 500000 ns -> "500μs"
    """
    if not nanoseconds:
        return "-"

    try:
        ns = float(nanoseconds)
    except (ValueError, TypeError):
        return str(nanoseconds)

    # Convert to appropriate unit
    if ns >= 1_000_000_000:  # >= 1 second
        seconds = ns / 1_000_000_000
        if seconds >= 60:
            minutes = seconds / 60
            if minutes >= 60:
                hours = minutes / 60
                return f"{hours:.1f}h"
            return f"{minutes:.1f}m"
        return f"{seconds:.1f}s"
    elif ns >= 1_000_000:  # >= 1 millisecond
        milliseconds = ns / 1_000_000
        return f"{milliseconds:.0f}ms"
    elif ns >= 1_000:  # >= 1 microsecond
        microseconds = ns / 1_000
        return f"{microseconds:.0f}μs"
    else:
        return f"{ns:.0f}ns"


@register.filter
def add_tailscale_params(quick_link_url, deploy_tailscale):
    """
    Add Tailscale OAuth parameters to quick_link_url when deploy_tailscale is False.

    Uses naive string appending because the AWS CloudFormation URL contains
    nested URLs as query parameters (e.g., templateURL=https://...), which
    breaks standard URL parsing.

    Args:
        quick_link_url (str): The AWS CloudFormation quick link URL
        deploy_tailscale (bool): Whether Tailscale deployment is enabled

    Returns:
        str: The URL with placeholder parameters if deploy_tailscale is False,
             otherwise the original URL unchanged (user provides secrets manually)

    Examples:
        {{ version.quick_link_url|add_tailscale_params:object.deploy_tailscale }}
    """
    # Return original URL if it's empty or None
    if not quick_link_url:
        return quick_link_url

    # Return original URL if Tailscale is enabled (secrets will be provided by user)
    if deploy_tailscale:
        return quick_link_url

    # When Tailscale is disabled, add placeholder parameters
    # Determine separator based on whether URL already has query params
    separator = '&' if '?' in quick_link_url else '?'

    # Append Tailscale parameters with placeholder values
    params = (
        f"param_TailscaleOauthClientIdParam=dne"
        f"&param_TailscaleOauthClientSecretParam=dne"
    )

    return f"{quick_link_url}{separator}{params}"
