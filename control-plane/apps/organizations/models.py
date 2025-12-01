from django.db import models
from django.conf import settings
from django.utils.text import slugify
from common.models import BaseModel
from common.validators import rfc1123_validator
from organizations.nuon import NuonInstallMixin


class OrganizationAgentStatus:
    """
    Struct that represents the state of the data-plane agent.
    This agent checks in. When it checks in, the status of the Organization.agent_status (string field) is updated and the entire payload is stored in `Organization.status_history`.

    status: one of ready, pending, error.
    reported_at: datetime of incoming request
    cluster_count: the count of the cluster's it's aware of
    """

    pass


class Organization(BaseModel, NuonInstallMixin):
    prefix = "org"
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        unique=True, db_index=True, validators=[rfc1123_validator], blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_organizations",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="OrganizationMember"
    )

    REGION_US_EAST_1 = "us-east-1"
    REGION_US_EAST_2 = "us-east-2"
    REGION_US_WEST_1 = "us-west-1"
    REGION_US_WEST_2 = "us-west-2"

    REGION_CHOICES = [
        (REGION_US_EAST_1, "US East (N. Virginia)"),
        (REGION_US_EAST_2, "US East (Ohio)"),
        (REGION_US_WEST_1, "US West (N. California)"),
        (REGION_US_WEST_2, "US West (Oregon)"),
    ]

    region = models.CharField(
        max_length=20, choices=REGION_CHOICES, default=REGION_US_EAST_1
    )
    deploy_headlamp = models.BooleanField(default=False)
    deploy_tailscale = models.BooleanField(default=False)

    # Nuon fields
    nuon_install_id = models.CharField(max_length=255, blank=True, null=True)
    nuon_install = models.JSONField(blank=True, null=True)
    nuon_install_state = models.JSONField(blank=True, null=True)
    nuon_install_stack = models.JSONField(blank=True, null=True)
    nuon_workflows = models.JSONField(blank=True, null=True)

    # agent
    # agent_status (enum string)
    # agent_status_history JSONField which is an array of the 20 most recent statuses
    # status_history should keep only the 20 most recent statuses.

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def nuon_provision_workflow(self):
        """
        Return the first workflow with type "provision" from nuon_workflows.
        """
        if not self.nuon_workflows:
            return None

        for workflow in self.nuon_workflows:
            if workflow.get("type") == "provision":
                return workflow
        return None

    @property
    def nuon_reprovision_workflow(self):
        """
        Return the most recent workflow with type "reprovision" from nuon_workflows.
        Workflows are sorted by created_at timestamp in descending order.
        """
        if not self.nuon_workflows:
            return None

        reprovision_workflows = [
            workflow
            for workflow in self.nuon_workflows
            if workflow.get("type") == "reprovision"
        ]

        if not reprovision_workflows:
            return None

        # Sort by created_at in descending order (most recent first)
        sorted_workflows = sorted(
            reprovision_workflows, key=lambda w: w.get("created_at", ""), reverse=True
        )

        return sorted_workflows[0] if sorted_workflows else None

    @property
    def nuon_latest_install_stack_version(self):
        """
        Return the most recent install stack version from nuon_install_stack.
        Sorts by version number in descending order to get the latest.
        """
        if not self.nuon_install_stack:
            return None

        versions = self.nuon_install_stack.get("versions")
        if not versions or not isinstance(versions, list) or len(versions) == 0:
            return None

        # Sort by version number (descending) to get the latest
        sorted_versions = sorted(
            versions, key=lambda v: int(v.get("version", 0)), reverse=True
        )

        return sorted_versions[0] if sorted_versions else None

    @property
    def nuon_active_workflow(self):
        """
        Return the active workflow (most recent reprovision workflow, or provision workflow if no reprovision exists).
        """
        reprovision = self.nuon_reprovision_workflow
        if reprovision:
            return reprovision
        return self.nuon_provision_workflow

    def has_await_install_stack_in_progress(self):
        """
        Check if the active workflow has an 'await-install-stack' step that is in-progress.
        """
        workflow = self.nuon_active_workflow
        if not workflow or not workflow.get("id"):
            return False

        steps = self.get_workflow_steps(workflow["id"])
        if not steps:
            return False

        for step in steps:
            if (
                step.get("step_target_type") == "install_stack_versions"
                and step.get("status", {}).get("status") == "in-progress"
            ):
                return True

        return False

    def has_active_workflow_cancelled(self):
        """
        Check if the active workflow has been cancelled.
        """
        workflow = self.nuon_active_workflow
        if not workflow:
            return False

        return workflow.get("status", {}).get("status") == "cancelled"

    def has_active_workflow_errored(self):
        """
        Check if the active workflow has errored.
        """
        workflow = self.nuon_active_workflow
        if not workflow:
            return False

        status = workflow.get("status", {}).get("status")
        return status in ["failed", "error"]


class OrganizationMember(BaseModel):
    prefix = "mem"

    ROLE_MANAGER = "manager"
    ROLE_OPERATOR = "operator"
    ROLE_SA = "service-account"
    ROLE_CHOICES = [
        (ROLE_MANAGER, "Manager"),
        (ROLE_OPERATOR, "Operator"),
        (ROLE_SA, "Service Account"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_OPERATOR)

    class Meta:
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.user} in {self.organization} as {self.role}"
