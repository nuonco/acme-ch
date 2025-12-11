from django.urls import path

from . import views

urlpatterns = [
    path("", views.Index.as_view(), name="index"),
    path("getting-started/create-org", views.CreateOrg.as_view(), name="create-org"),
    path("orgs/<slug:slug>", views.OrganizationDetail.as_view(), name="org-detail"),
    path(
        "orgs/<slug:slug>/ch-clusters",
        views.OrganizationCHClusterList.as_view(),
        name="org-ch-clusters",
    ),
    path(
        "orgs/<slug:slug>/ch-clusters/create",
        views.CreateCHCluster.as_view(),
        name="create-ch-cluster",
    ),
    path(
        "orgs/<slug:slug>/ch-clusters/<slug:cluster_slug>/query",
        views.CHClusterQuery.as_view(),
        name="ch-cluster-query",
    ),
    path("ch-clusters", views.Clusters.as_view(), name="ch-clusters"),
    # HTMX partials
    path(
        "p/orgs/<slug:slug>/install-status",
        views.OrgDetailInstallStatusPartial.as_view(),
        name="org-detail-install-status",
    ),
    path(
        "p/orgs/<slug:slug>/install-stack",
        views.OrgDetailInstallStackPartial.as_view(),
        name="org-detail-install-stack",
    ),
    path(
        "p/orgs/<slug:slug>/runner",
        views.OrgDetailRunnerPartial.as_view(),
        name="org-detail-runner",
    ),
    path(
        "p/orgs/<slug:slug>/sandbox",
        views.OrgDetailSandboxPartial.as_view(),
        name="org-detail-sandbox",
    ),
    path(
        "p/orgs/<slug:slug>/components",
        views.OrgDetailComponentsPartial.as_view(),
        name="org-detail-components",
    ),
    path(
        "p/orgs/<slug:slug>/workflow-steps",
        views.OrgDetailWorkflowStepsPartial.as_view(),
        name="org-detail-workflow-steps",
    ),
    path(
        "p/orgs/<slug:slug>/cta",
        views.OrgDetailCTAPartial.as_view(),
        name="org-detail-cta",
    ),
]
