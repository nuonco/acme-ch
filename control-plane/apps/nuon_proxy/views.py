from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging

from nuon.api.installs import create_workflow_step_approval_response
from nuon.models.service_create_workflow_step_approval_response_request import (
    ServiceCreateWorkflowStepApprovalResponseRequest,
)
from common.nuon_client import NuonAPIClient

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class ApproveStepView(View):
    """
    Proxy view to approve a workflow step using the Nuon API.

    POST /api/nuon-proxy/approve-step/
    Body: {
        "workflow_id": "wfl...",
        "step_id": "stp...",
        "approval_id": "apr...",
        "approved": true/false,
        "comment": "optional comment"
    }
    """

    def post(self, request, *args, **kwargs):
        try:
            import json

            data = json.loads(request.body)

            workflow_id = data.get("workflow_id")
            step_id = data.get("step_id")
            approval_id = data.get("approval_id")
            approved = data.get("approved")
            comment = data.get("comment", "")

            # Validate required fields
            if not all([workflow_id, step_id, approval_id, approved is not None]):
                return JsonResponse(
                    {
                        "error": "Missing required fields: workflow_id, step_id, approval_id, approved"
                    },
                    status=400,
                )

            # Create request body
            body = ServiceCreateWorkflowStepApprovalResponseRequest(
                approved=approved,
                comment=comment,
            )

            # Call Nuon API
            nc = NuonAPIClient()
            with nc.get_client() as client:
                response = create_workflow_step_approval_response.sync(
                    client=client,
                    workflow_id=workflow_id,
                    step_id=step_id,
                    approval_id=approval_id,
                    body=body,
                )

            # Handle response
            if response is None:
                return JsonResponse({"error": "No response from Nuon API"}, status=500)

            # Check if response is an error
            if hasattr(response, "message"):
                return JsonResponse(
                    {"error": response.message}, status=response.status_code or 500
                )

            # Success - convert response to dict
            response_dict = response.to_dict() if hasattr(response, "to_dict") else {}

            logger.info(
                f"Successfully approved workflow step: workflow_id={workflow_id}, step_id={step_id}"
            )

            return JsonResponse({"success": True, "data": response_dict}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            logger.error(f"Error approving workflow step: {e}")
            return JsonResponse({"error": str(e)}, status=500)
