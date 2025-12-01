from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

# RFC 1123 hostname validation
# - contain only alphanumeric characters and hyphens
# - cannot start or end with a hyphen
# - max length 63 characters
rfc1123_validator = RegexValidator(
    regex=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$",
    message=_(
        "Slug must be a valid RFC 1123 hostname (lowercase alphanumeric characters and hyphens, starting and ending with an alphanumeric character)."
    ),
)
