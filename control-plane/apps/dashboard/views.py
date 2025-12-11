from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView, ListView, CreateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime

from organizations.models import Organization, OrganizationMember
from organizations.forms import OrganizationForm
from clusters.models import CHCluster


class Index(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def dispatch(self, request, *args, **kwargs):
        # Check authentication first (LoginRequiredMixin should handle this, but be explicit)
        if not request.user.is_authenticated:
            return redirect(reverse("login"))

        if not request.user.organizationmember_set.exists():
            return redirect(reverse("create-org"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organizations"] = Organization.objects.filter(
            members=self.request.user
        )
        return context


class CreateOrg(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "create-org.html"

    def get_context_data(self, **kwargs):
        from django.conf import settings

        context = super().get_context_data(**kwargs)
        context["delegated_role_name"] = settings.AWS_DELEGATED_ROLE
        return context

    def form_valid(self, form):
        # Set the creator
        form.instance.created_by = self.request.user
        # Save the organization
        response = super().form_valid(form)

        # Add the creator as a Manager of the organization
        OrganizationMember.objects.create(
            organization=self.object,
            user=self.request.user,
            role=OrganizationMember.ROLE_MANAGER,
        )

        return response

    def get_success_url(self):
        return reverse("org-detail", kwargs={"slug": self.object.slug})


class OrganizationDetail(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from clusters.models import CHCluster

        # Get cluster count for this organization
        cluster_count = CHCluster.objects.filter(organization=self.object).count()
        context["cluster_count"] = cluster_count

        return context


class Clusters(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/clusters.html"


# HTMX Partials
# Convention: Always use *Partial suffix for HTMX-only views and group them together
# These views return HTML fragments for HTMX to swap into the page


class OrgDetailInstallStatusPartial(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/partials/install_status.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)


class OrgDetailInstallStackPartial(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/partials/install_stack.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)


class OrgDetailRunnerPartial(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/partials/runner.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)


class OrgDetailSandboxPartial(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/partials/sandbox.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)


class OrgDetailComponentsPartial(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/partials/components.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)


class OrgDetailWorkflowStepsPartial(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = "orgs/partials/workflow_steps.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        # Only return organizations where the current user is a member
        return Organization.objects.filter(members=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.get_object()

        # Get the active workflow
        workflow = org.nuon_active_workflow

        if workflow and workflow.get("id"):
            # Fetch workflow steps
            steps = org.get_workflow_steps(workflow["id"])
            context["workflow_steps"] = steps
            context["workflow"] = workflow

            # Calculate progress
            completed_steps = 0
            total_steps = 0
            steps_needing_approval = []
            all_steps_completed = False
            if steps:
                total_steps = len(steps)
                all_steps_completed = True
                for step in steps:
                    # Count completed/success/approved steps
                    status = step.get("status", {}).get("status", "")
                    if status in ["completed", "success", "approved"]:
                        completed_steps += 1
                    else:
                        all_steps_completed = False

                    # Filter steps that need approval
                    approval = step.get("approval")
                    if approval:
                        responses = approval.get("responses", [])
                        if not responses:
                            steps_needing_approval.append(step)

            # Calculate progress percentage
            context["workflow_progress_percent"] = (
                int((completed_steps / total_steps * 100)) if total_steps > 0 else 0
            )
            context["workflow_completed_steps"] = completed_steps
            context["workflow_total_steps"] = total_steps
            context["has_pending_approvals"] = len(steps_needing_approval) > 0
            context["all_steps_completed"] = all_steps_completed
        else:
            context["workflow_steps"] = None
            context["workflow"] = None
            context["has_pending_approvals"] = False
            context["all_steps_completed"] = False

        # Add approve URLs for the template
        from django.urls import reverse

        context["approve_step_url"] = reverse(
            "organization-approve-step", kwargs={"id": org.id}
        )
        context["approve_all_url"] = reverse(
            "organization-approve-all", kwargs={"id": org.id}
        )

        return context


class OrgDetailCTAPartial(LoginRequiredMixin, DetailView):
    """HTMX partial view for unified CTA component."""

    model = Organization
    template_name = "orgs/partials/cta.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Organization.objects.filter(members=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org = self.get_object()

        # Determine CTA state from org data only
        cta_state, state_data = self._determine_cta_state(org)
        context["cta_state"] = cta_state
        context["poll_interval"] = self._get_poll_interval(cta_state, state_data)
        context.update(state_data)

        return context

    def _determine_cta_state(self, org):
        """Determine CTA state purely from Organization model data.

        Returns: (state_name, state_data_dict)
        """
        version = org.nuon_latest_install_stack_version

        # Check for rate limiting first
        cache_key = f"reprovision_cooldown_{org.id}"
        last_reprovision = cache.get(cache_key)
        if last_reprovision:
            retry_after = self._calculate_retry_after(last_reprovision)
            if retry_after > 0:
                return "RATE_LIMITED", {"retry_after": retry_after}

        # Check INSTALL_STACK_AWAITING_USER_RUN state
        if (
            version
            and version.get("composite_status", {}).get("status") == "awaiting-user-run"
            and version.get("quick_link_url")
            and org.has_await_install_stack_in_progress()
        ):
            return "INSTALL_STACK_AWAITING_USER_RUN", {
                "version": version,
                "quick_link_url": version.get("quick_link_url"),
                "template_url": version.get("template_url"),
            }

        # Check REPROVISION_WAITING state (derived from workflow)
        workflow = org.nuon_active_workflow
        if workflow and self._is_workflow_starting(workflow):
            return "REPROVISION_WAITING", {}

        # Check REPROVISION_NEEDED state
        if (
            (version and version.get("composite_status", {}).get("status") == "expired")
            or org.has_active_workflow_cancelled()
            or org.has_active_workflow_errored()
        ):
            reason = self._get_reprovision_reason(org)
            return "REPROVISION_NEEDED", {"reason": reason}

        # Default: no CTA needed
        return "NO_CTA", {}

    def _is_workflow_starting(self, workflow):
        """Check if workflow is in early stages (queued, pending, starting)."""
        if not workflow:
            return False
        status = workflow.get("status", {}).get("status", "")

        # Check if workflow started recently (within last 2 minutes)
        created_at = workflow.get("created_at")
        if created_at and status in ["queued", "pending", "starting", "running"]:
            try:
                # Parse ISO format timestamp
                if isinstance(created_at, str):
                    workflow_time = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                else:
                    workflow_time = created_at

                # Make timezone aware if needed
                if timezone.is_naive(workflow_time):
                    workflow_time = timezone.make_aware(workflow_time)

                # Check if workflow is recent (within 2 minutes)
                time_diff = (timezone.now() - workflow_time).total_seconds()
                if time_diff < 120:  # 2 minutes
                    return True
            except (ValueError, TypeError):
                # If we can't parse the timestamp, just check status
                pass

        return status in ["queued", "pending", "starting"]

    def _get_reprovision_reason(self, org):
        """Determine why reprovision is needed."""
        if org.has_active_workflow_errored():
            return "WORKFLOW_FAILED"
        elif org.has_active_workflow_cancelled():
            return "WORKFLOW_CANCELLED"
        return "INSTALL_EXPIRED"

    def _calculate_retry_after(self, last_reprovision_time):
        """Calculate seconds until rate limit expires."""
        elapsed = (timezone.now() - last_reprovision_time).total_seconds()
        rate_limit = 300  # 5 minutes
        return max(0, int(rate_limit - elapsed))

    def _get_poll_interval(self, state, state_data):
        """Return polling interval in seconds based on state."""
        intervals = {
            "NO_CTA": 5,
            "INSTALL_STACK_AWAITING_USER_RUN": 5,
            "REPROVISION_NEEDED": 5,
            "REPROVISION_WAITING": 60,  # Slower during waiting
            "RATE_LIMITED": state_data.get("retry_after", 5),  # Precise timing
        }
        return intervals.get(state, 5)


class OrganizationCHClusterList(LoginRequiredMixin, ListView):
    model = CHCluster
    template_name = "orgs/clusters/list.html"
    context_object_name = "clusters"

    def get_queryset(self):
        # Get the organization by slug
        self.organization = get_object_or_404(
            Organization, slug=self.kwargs["slug"], members=self.request.user
        )
        # Return clusters for this organization
        return CHCluster.objects.filter(organization=self.organization).order_by(
            "-created_on"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        return context


class CHClusterQuery(LoginRequiredMixin, DetailView):
    model = CHCluster
    template_name = "orgs/clusters/query.html"
    slug_field = "slug"
    slug_url_kwarg = "cluster_slug"
    context_object_name = "cluster"

    def get_queryset(self):
        self.organization = get_object_or_404(
            Organization, slug=self.kwargs["slug"], members=self.request.user
        )
        return CHCluster.objects.filter(organization=self.organization)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        return context


class CreateCHCluster(LoginRequiredMixin, CreateView):
    model = CHCluster
    fields = ["name", "cluster_type", "ingress_type"]
    template_name = "orgs/clusters/create.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the organization and check if user is a member
        self.organization = get_object_or_404(
            Organization, slug=self.kwargs["slug"], members=self.request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        from django.utils.text import slugify

        # Set the organization
        form.instance.organization = self.organization
        # Auto-generate slug from name if not provided
        if not form.instance.slug:
            form.instance.slug = slugify(form.instance.name)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["organization"] = self.organization
        return context

    def get_success_url(self):
        return reverse("org-ch-clusters", kwargs={"slug": self.organization.slug})
