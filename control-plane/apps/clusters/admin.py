from django.contrib import admin
from django.utils.html import format_html
from .models import CHCluster
import json


@admin.register(CHCluster)
class CHClusterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "identifier",
        "organization",
        "cluster_type",
        "ingress_type",
        "status_display",
        "created_on",
    )
    list_filter = ("cluster_type", "ingress_type", "created_on")
    search_fields = ("name", "identifier", "slug", "organization__name")
    readonly_fields = (
        "identifier",
        "name",
        "slug",
        "cluster_type",
        "ingress_type",
        "status_display",
        "status_json",
        "created_on",
        "updated_on",
    )

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("organization", "name", "slug", "identifier")},
        ),
        ("Configuration", {"fields": ("cluster_type", "ingress_type")}),
        ("Status", {"fields": ("status_display", "status_json")}),
        (
            "Timestamps",
            {"fields": ("created_on", "updated_on"), "classes": ("collapse",)},
        ),
    )

    def status_display(self, obj):
        """Display the cluster status in a readable format."""
        cluster_status = obj.cluster_status
        status = cluster_status.status

        if status == "ready":
            return f"✅ {status.upper()}"
        elif status == "pending":
            return f"⏳ {status.upper()}"
        elif status == "error":
            return f"❌ {status.upper()}"
        return status.upper()

    status_display.short_description = "Status"

    def status_json(self, obj):
        """Display the status JSON in a pretty-printed format."""
        if not obj.status:
            return "-"

        pretty_json = json.dumps(obj.status, indent=2, sort_keys=True)
        return format_html('<pre style="margin: 0;">{}</pre>', pretty_json)

    status_json.short_description = "Status (JSON)"
