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
