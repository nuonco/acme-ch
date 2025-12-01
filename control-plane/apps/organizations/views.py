import logging
from datetime import timedelta
from django.core.cache import cache
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Organization, OrganizationMember
from .serializers import OrganizationSerializer
from .tasks import nuon_refresh, reprovision_nuon_install

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    # Organization ViewSet

    ViewSet for viewing and managing organizations.

    ## Endpoints

    ### List Organizations
    `GET /api/orgs`

    Returns all organizations where the authenticated user is a member.

    ### Retrieve Organization
    `GET /api/orgs/{id}`

    Returns details for a specific organization.

    ### Trigger Action
    `POST /api/orgs/{id}/trigger_action`

    Trigger an asynchronous action for the organization.

    **Request Body:**
    ```json
    {
        "action": "refresh"
    }
    ```

    **Available Actions:**
    - `refresh` - Refresh organization data from Nuon API
    - `reprovision` - Reprovision the Nuon install

    ### Get Nuon Install
    `GET /api/orgs/{id}/install`

    Returns the Nuon install for the organization.

    ### Get Install Stack
    `GET /api/orgs/{id}/install-stack`

    Returns the Nuon install stack for the organization.

    ### Get Workflows
    `GET /api/orgs/{id}/workflows`

    Returns the Nuon workflows for the organization.

    ### Get Install State
    `GET /api/orgs/{id}/install-state`

    Returns the Nuon install state for the organization.
    """

    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    available_actions = {
        "refresh": {
            "task": nuon_refresh,
            "rate_limit": timedelta(seconds=5),
            "rate_limit_message": "Refresh can only be triggered once every 5 seconds",
        },
        "reprovision": {
            "task": reprovision_nuon_install,
            "rate_limit": timedelta(minutes=5),
            "rate_limit_message": "Reprovision can only be triggered once every 5 minutes",
        },
    }

    def get_queryset(self):
        """
        Return only organizations where the user is a member.
        """
        return Organization.objects.filter(members=self.request.user).distinct()

    @action(detail=True, methods=["post"])
    def trigger_action(self, request, id=None):
        """
        Trigger an action for the organization.

        POST /api/orgs/{id}/trigger_action
        Body: {
            "action": "refresh"
        }
        """
        org = self.get_object()
        action_name = request.data.get("action")

        if not action_name:
            return Response(
                {"error": "Missing required field: action"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action_name not in self.available_actions:
            return Response(
                {
                    "error": f"Invalid action: {action_name}. Available actions: {list(self.available_actions.keys())}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get action configuration
        action_config = self.available_actions[action_name]
        action_task = action_config["task"]
        rate_limit = action_config["rate_limit"]
        rate_limit_message = action_config["rate_limit_message"]

        # Check rate limit
        cache_key = f"action_rate_limit:{org.id}:{action_name}"
        last_execution = cache.get(cache_key)

        if last_execution:
            time_since_last = timezone.now() - last_execution
            if time_since_last < rate_limit:
                seconds_remaining = int((rate_limit - time_since_last).total_seconds())

                # Check if this is an htmx request for reprovision action
                if action_name == "reprovision" and request.headers.get("HX-Request"):
                    from django.template.loader import render_to_string
                    from django.http import HttpResponse

                    html = render_to_string(
                        "orgs/partials/reprovision_rate_limit.html",
                        {
                            "org": org,
                            "error_message": rate_limit_message,
                            "retry_after": seconds_remaining,
                        },
                    )
                    return HttpResponse(html, content_type="text/html")

                return Response(
                    {"error": rate_limit_message, "retry_after": seconds_remaining},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(seconds_remaining)},
                )

        # Execute the action asynchronously
        result = action_task.delay(org.id)

        # Update rate limit cache
        cache.set(
            cache_key, timezone.now(), timeout=int(rate_limit.total_seconds()) + 60
        )

        logger.info(
            f"User {request.user.email} triggered action '{action_name}' for org {org.slug}"
        )

        # Check if this is an htmx request for reprovision action
        if action_name == "reprovision" and request.headers.get("HX-Request"):
            from django.template.loader import render_to_string
            from django.http import HttpResponse

            html = render_to_string(
                "orgs/partials/reprovision_waiting.html", {"org": org}
            )
            return HttpResponse(html, content_type="text/html")

        return Response(
            {
                "success": True,
                "action": action_name,
                "task_id": result.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="install")
    def nuon_install(self, request, id=None):
        """
        Get Nuon install for the organization.

        GET /api/orgs/{id}/install
        """
        org = self.get_object()
        return Response({"nuon_install": org.nuon_install})

    @action(detail=True, methods=["get"], url_path="install-stack")
    def nuon_install_stack(self, request, id=None):
        """
        Get Nuon install stack for the organization.

        GET /api/orgs/{id}/install-stack
        """
        org = self.get_object()
        return Response({"nuon_install_stack": org.nuon_install_stack})

    @action(detail=True, methods=["get"], url_path="workflows")
    def nuon_workflows(self, request, id=None):
        """
        Get Nuon workflows for the organization.

        GET /api/orgs/{id}/workflows
        """
        org = self.get_object()
        return Response(org.nuon_workflows)

    @action(detail=True, methods=["get"], url_path="install-state")
    def nuon_install_state(self, request, id=None):
        """
        Get Nuon install state for the organization.

        GET /api/orgs/{id}/install-state
        """
        org = self.get_object()
        return Response(org.nuon_install_state)

    @action(detail=True, methods=["post"], url_path="approve-step")
    def approve_step(self, request, id=None):
        """
        Approve a workflow step.

        POST /api/orgs/{id}/approve-step

        Body parameters:
        - workflow_id (required): The workflow ID
        - step_id (required): The workflow step ID
        - approval_id (required): The approval ID
        - response_type (optional): The approval response type, defaults to "approve"
        """
        from organizations.tasks import create_workflow_step_approval

        org = self.get_object()

        # Get required parameters
        workflow_id = request.data.get("workflow_id")
        step_id = request.data.get("step_id")
        approval_id = request.data.get("approval_id")

        # Validate required parameters
        if not workflow_id:
            return Response(
                {"error": "workflow_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not step_id:
            return Response(
                {"error": "step_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not approval_id:
            return Response(
                {"error": "approval_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get optional parameters
        response_type = request.data.get("response_type", "approve")
        note = f"approved by acme-ch user:{request.user.email}."

        # Trigger the task asynchronously
        result = create_workflow_step_approval.delay(
            organization_id=org.id,
            workflow_id=workflow_id,
            step_id=step_id,
            approval_id=approval_id,
            response_type=response_type,
            note=note,
        )

        logger.info(
            f"User {request.user.email} triggered workflow step approval for org {org.slug}, "
            f"workflow {workflow_id}, step {step_id}, approval {approval_id}"
        )

        return Response(
            {
                "success": True,
                "workflow_id": workflow_id,
                "step_id": step_id,
                "approval_id": approval_id,
                "response_type": response_type,
                "task_id": result.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="approve-all")
    def approve_all(self, request, id=None):
        """
        Approve all pending steps in a workflow.

        POST /api/orgs/{id}/approve-all

        Body parameters:
        - workflow_id (required): The workflow ID
        """
        from organizations.tasks import workflow_approve_all

        org = self.get_object()

        # Get required parameter
        workflow_id = request.data.get("workflow_id")

        # Validate required parameter
        if not workflow_id:
            return Response(
                {"error": "workflow_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Trigger the task asynchronously
        result = workflow_approve_all.delay(
            organization_id=org.id, workflow_id=workflow_id
        )

        logger.info(
            f"User {request.user.email} triggered approve all for org {org.slug}, "
            f"workflow {workflow_id}"
        )

        return Response(
            {
                "success": True,
                "workflow_id": workflow_id,
                "task_id": result.id,
            },
            status=status.HTTP_200_OK,
        )
