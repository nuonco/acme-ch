from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from organizations.models import Organization
from .models import CHCluster
from .serializers import CHClusterSerializer, CHClusterStatusSerializer


class CHClusterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing clusters within an organization.

    Clusters are accessed as a nested resource under organizations:
    `/api/orgs/{org_id}/clusters`

    ## Filtering

    You can filter clusters by type using the `type` query parameter:
    - `?type=single_node`
    - `?type=cluster`
    - `?type=keeper`
    """

    serializer_class = CHClusterSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        """
        Get clusters for the specified organization.
        Filter by user membership and optionally by cluster_type.
        """
        # Get the organization and verify user is a member
        org_id = self.kwargs.get("org_id")
        organization = get_object_or_404(
            Organization, id=org_id, members=self.request.user
        )

        queryset = CHCluster.objects.filter(organization=organization).order_by(
            "-created_on"
        )

        # Filter by cluster type if provided
        cluster_type = self.request.query_params.get("type", None)
        if cluster_type is not None:
            queryset = queryset.filter(cluster_type=cluster_type)

        return queryset

    def perform_create(self, serializer):
        """
        Create a cluster for the specified organization.
        """
        org_id = self.kwargs.get("org_id")
        organization = get_object_or_404(
            Organization, id=org_id, members=self.request.user
        )
        serializer.save(organization=organization)

    @action(detail=True, methods=["post"], url_path="update-status")
    def update_status(self, request, org_id=None, id=None):
        """
        Update the cluster status.

        POST /api/orgs/{org_id}/clusters/{id}/update-status/

        Request body should contain ClusterStatus fields:
        {
            "status": "ready|pending|error",
            "ingress": {...},  # optional
            "chi": {...},      # optional
            "chk": {...},      # optional
            "errors": [...]    # optional
        }
        """
        cluster = self.get_object()
        serializer = CHClusterStatusSerializer(data=request.data)

        if serializer.is_valid():
            # Update the cluster status
            cluster.update_status(
                status=serializer.validated_data.get("status"),
                ingress=serializer.validated_data.get("ingress"),
                chi=serializer.validated_data.get("chi"),
                chk=serializer.validated_data.get("chk"),
                errors=serializer.validated_data.get("errors"),
            )

            return Response(
                {
                    "message": "Cluster status updated successfully",
                    "status": cluster.status,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
