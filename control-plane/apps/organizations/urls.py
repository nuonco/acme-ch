from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from clusters.views import CHClusterViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', views.OrganizationViewSet, basename='organization')

# Nested routes for ch-clusters under organizations
ch_cluster_list = CHClusterViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

ch_cluster_detail = CHClusterViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

ch_cluster_update_status = CHClusterViewSet.as_view({
    'post': 'update_status'
})

urlpatterns = [
    path('', include(router.urls)),
    path('<str:org_id>/ch-clusters', ch_cluster_list, name='organization-ch-clusters-list'),
    path('<str:org_id>/ch-clusters/<str:id>', ch_cluster_detail, name='organization-ch-clusters-detail'),
    path('<str:org_id>/ch-clusters/<str:id>/update-status', ch_cluster_update_status, name='organization-ch-clusters-update-status'),
]
