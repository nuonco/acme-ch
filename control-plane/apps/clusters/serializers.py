from rest_framework import serializers
from .models import CHCluster, CHClusterStatus


class CHClusterStatusSerializer(serializers.Serializer):
    """Serializer for CHClusterStatus dataclass."""

    ingress = serializers.JSONField(required=False, allow_null=True)
    chi = serializers.JSONField(required=False, allow_null=True)
    chk = serializers.JSONField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=CHClusterStatus.STATUS_CHOICES, default=CHClusterStatus.STATUS_PENDING
    )
    errors = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )
    created_at = serializers.CharField(required=False, read_only=True)


class CHClusterSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    cluster_type_display = serializers.CharField(
        source="get_cluster_type_display", read_only=True
    )
    ingress_type_display = serializers.CharField(
        source="get_ingress_type_display", read_only=True
    )

    class Meta:
        model = CHCluster
        fields = [
            "id",
            "identifier",
            "name",
            "slug",
            "cluster_type",
            "cluster_type_display",
            "ingress_type",
            "ingress_type_display",
            "organization",
            "organization_name",
            "created_on",
            "updated_on",
        ]
        read_only_fields = ["id", "identifier", "created_on", "updated_on"]
