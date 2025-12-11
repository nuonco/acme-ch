from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
import json
from .models import Organization, OrganizationMember
from .tasks import reprovision_nuon_install, nuon_refresh


class OrganizationMemberInline(admin.TabularInline):
    model = OrganizationMember
    extra = 1
    fields = ["user", "role"]
    autocomplete_fields = ["user"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    inlines = [OrganizationMemberInline]
    readonly_fields = [
        "id",
        "created_on",
        "updated_on",
        "name",
        "slug",
        "region",
        "created_by",
        "deploy_headlamp",
        "deploy_tailscale",
        "nuon_install_id",
        "reprovision_button",
        "nuon_install_display",
        "nuon_install_state_display",
        "nuon_install_stack_display",
        "nuon_workflows_display",
    ]

    def reprovision_button(self, obj):
        """Display a button to trigger reprovision"""
        if obj.nuon_install_id:
            url = reverse("admin:organization_reprovision", args=[obj.pk])
            return mark_safe(
                f'<a href="{url}" class="button" style="padding: 10px 15px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px; display: inline-block;">Reprovision</a>'
            )
        return "-"

    reprovision_button.short_description = "Actions"

    def nuon_install_display(self, obj):
        """Display nuon_install as pretty JSON"""
        if obj.nuon_install:
            pretty_json = json.dumps(obj.nuon_install, indent=2, sort_keys=True)
            return mark_safe(
                f'<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow: auto; max-height: 600px; border: 1px solid #333; font-size: 13px; line-height: 1.5;">{pretty_json}</pre>'
            )
        return "-"

    nuon_install_display.short_description = "Nuon Install"

    def nuon_install_state_display(self, obj):
        """Display nuon_install_state as pretty JSON"""
        if obj.nuon_install_state:
            pretty_json = json.dumps(obj.nuon_install_state, indent=2, sort_keys=True)
            return mark_safe(
                f'<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow: auto; max-height: 600px; border: 1px solid #333; font-size: 13px; line-height: 1.5;">{pretty_json}</pre>'
            )
        return "-"

    nuon_install_state_display.short_description = "Nuon Install State"

    def nuon_install_stack_display(self, obj):
        """Display nuon_install_stack as pretty JSON"""
        if obj.nuon_install_stack:
            pretty_json = json.dumps(obj.nuon_install_stack, indent=2, sort_keys=True)
            return mark_safe(
                f'<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow: auto; max-height: 600px; border: 1px solid #333; font-size: 13px; line-height: 1.5;">{pretty_json}</pre>'
            )
        return "-"

    nuon_install_stack_display.short_description = "Nuon Install Stack"

    def nuon_workflows_display(self, obj):
        """Display nuon_workflows as pretty JSON"""
        if obj.nuon_workflows:
            pretty_json = json.dumps(obj.nuon_workflows, indent=2, sort_keys=True)
            return mark_safe(
                f'<pre style="background-color: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 6px; overflow: auto; max-height: 600px; border: 1px solid #333; font-size: 13px; line-height: 1.5;">{pretty_json}</pre>'
            )
        return "-"

    nuon_workflows_display.short_description = "Nuon Workflows"
    list_display = ["id", "name", "slug", "region", "created_by", "created_on"]
    search_fields = ["name", "slug", "id", "created_by__email"]

    fieldsets = [
        (
            "Topmatter",
            {"fields": (("id", "created_on", "updated_on"),)},
        ),
        (
            "Organization Details",
            {"fields": ("name", "slug", "region", "created_by")},
        ),
        (
            "Configuration",
            {"fields": ("deploy_headlamp", "deploy_tailscale")},
        ),
        (
            "Nuon",
            {
                "fields": (
                    "nuon_install_id",
                    "reprovision_button",
                    "nuon_install_display",
                    "nuon_install_state_display",
                    "nuon_install_stack_display",
                    "nuon_workflows_display",
                ),
                "classes": ("collapse",),
            },
        ),
    ]

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/reprovision/",
                self.admin_site.admin_view(self.reprovision_view),
                name="organization_reprovision",
            ),
        ]
        return custom_urls + urls

    def reprovision_view(self, request, object_id):
        """Handle reprovision action"""
        obj = self.get_object(request, object_id)
        if obj is None:
            self.message_user(request, "Organization not found.", level=messages.ERROR)
            return redirect("admin:organizations_organization_changelist")

        # Trigger reprovision task followed by refresh
        reprovision_nuon_install.delay(obj.id)
        nuon_refresh.delay(obj.id)

        self.message_user(
            request,
            f"Reprovision and refresh tasks triggered for {obj.name}",
            level=messages.SUCCESS,
        )
        return redirect("admin:organizations_organization_change", object_id)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False
