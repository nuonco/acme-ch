from django import forms
from .models import Organization


class OrganizationForm(forms.ModelForm):
    DISABLED_REGIONS = [
        Organization.REGION_US_WEST_1,
    ]

    class Meta:
        model = Organization
        fields = [
            "name",
            "region",
            "deploy_headlamp",
            "deploy_tailscale",
            "enable_delegation",
            "enable_cluster_access",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["region"].choices = [
            choice
            for choice in Organization.REGION_CHOICES
            if choice[0] not in self.DISABLED_REGIONS
        ]

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if Organization.objects.filter(name=name).exists():
            raise forms.ValidationError(
                "An organization with this name already exists."
            )
        return name
