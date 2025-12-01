from django.db import models
from ksuid import Ksuid


def generate_ksuid() -> str:
    return str(Ksuid())


class BaseModel(models.Model):
    id = models.CharField(
        max_length=30, primary_key=True, default=generate_ksuid, editable=False
    )
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    # Meta
    prefix = "def"

    class Meta:
        abstract = True

    @property
    def identifier(self):
        return f"{self.prefix}{self.id}"
