from django.contrib import admin
from django.contrib.auth import get_user_model

User = get_user_model()


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "is_active", "is_staff", "is_superuser", "created_on"]
    list_filter = ["is_active", "is_staff", "is_superuser", "created_on"]
    search_fields = ["email", "id"]
    readonly_fields = ["id", "created_on", "updated_on", "last_login", "password"]
    fieldsets = [
        (
            "User Information",
            {"fields": ("id", "email", "password")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser")},
        ),
        (
            "Timestamps",
            {"fields": ("created_on", "updated_on", "last_login")},
        ),
    ]

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
