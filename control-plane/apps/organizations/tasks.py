from celery import shared_task
import logging

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from organizations.models import Organization

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def debug_task():
    logger.info("Debug task executed")


@shared_task
def create_nuon_install(organization_id):
    try:
        org = Organization.objects.get(id=organization_id)
        org.nuon_create_install()
    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
    except Exception as e:
        logger.error(f"Error creating nuon install for org {organization_id}: {e}")
        raise e


@shared_task
def nuon_refresh(organization_id):
    try:
        org = Organization.objects.get(id=organization_id)
        org.nuon_refresh()
    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
    except Exception as e:
        logger.error(f"Error creating nuon install for org {organization_id}: {e}")
        raise e


@shared_task
def refresh_all_orgs():
    """
    Periodic task that refreshes all organizations.
    Runs every minute to keep organization data up to date.
    """
    logger.info("starting refresh_all_orgs task")

    for org in Organization.objects.all():
        try:
            org.nuon_refresh()
        except Exception as e:
            logger.error(f"Error refreshing org {org.id}: {e}")

    logger.info("completed refresh_all_orgs task")


@shared_task
def reprovision_nuon_install(organization_id):
    try:
        org = Organization.objects.get(id=organization_id)
        org.nuon_reprovision_install()
    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
    except Exception as e:
        logger.error(f"Error reprovisioning nuon install for org {organization_id}: {e}")
        raise e


@shared_task
def fetch_install_state(organization_id):
    """
    Fetch and update the install state for an organization.
    """
    try:
        org = Organization.objects.get(id=organization_id)
        org.get_install_state()
        logger.info(f"Successfully fetched install state for org {organization_id}")
    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
    except Exception as e:
        logger.error(f"Error fetching install state for org {organization_id}: {e}")
        raise e


@shared_task
def create_service_account_user(organization_id):
    """
    Create a service account user for the organization and generate an API token.
    The user email format is: {organization.identifier}-sa@acme-ch.com
    """
    try:
        org = Organization.objects.get(id=organization_id)
        email = f"{org.identifier}-sa@acme-ch.com"

        # Create the user (service account)
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
                "is_staff": False,
            }
        )

        if created:
            logger.info(f"Created service account user: {email} for org {org.id}")
        else:
            logger.info(f"Service account user already exists: {email} for org {org.id}")

        # Create or get API token for the user
        token, token_created = Token.objects.get_or_create(user=user)

        if token_created:
            logger.info(f"Created API token for user: {email}")
        else:
            logger.info(f"API token already exists for user: {email}")

        return {"user_id": user.id, "email": email, "token": token.key}

    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
    except Exception as e:
        logger.error(f"Error creating user for org {organization_id}: {e}")
        raise e


@shared_task
def create_workflow_step_approval(organization_id, workflow_id, step_id, approval_id, response_type, note=None):
    """
    Create a response for a workflow step approval.

    Args:
        organization_id (int): The organization ID
        workflow_id (str): The workflow ID
        step_id (str): The workflow step ID
        approval_id (str): The approval ID
        response_type (str): The approval response type (e.g., "approve", "deny")
        note (str, optional): Optional note for the approval response

    Returns:
        dict: Response data or None on error
    """
    try:
        org = Organization.objects.get(id=organization_id)
        response = org.create_workflow_step_approval(
            workflow_id=workflow_id,
            step_id=step_id,
            approval_id=approval_id,
            response_type=response_type,
            note=note
        )

        if response:
            logger.info(
                f"Created workflow step approval for org {organization_id}, "
                f"workflow {workflow_id}, step {step_id}, approval {approval_id}"
            )
            return response.to_dict() if hasattr(response, 'to_dict') else response
        else:
            logger.error(
                f"Failed to create workflow step approval for org {organization_id}, "
                f"workflow {workflow_id}, step {step_id}"
            )
            return None

    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
        return None
    except Exception as e:
        logger.error(
            f"Error creating workflow step approval for org {organization_id}, "
            f"workflow {workflow_id}: {e}"
        )
        raise e


@shared_task
def workflow_approve_all(organization_id, workflow_id):
    """
    Approve all pending workflow steps that have approvals with empty responses.

    Args:
        organization_id (int): The organization ID
        workflow_id (str): The workflow ID

    Returns:
        dict: Summary of approvals processed
    """
    try:
        org = Organization.objects.get(id=organization_id)

        # Fetch workflow steps
        steps = org.get_workflow_steps(workflow_id)

        if not steps:
            logger.warning(
                f"No workflow steps found for org {organization_id}, workflow {workflow_id}"
            )
            return {"approved_count": 0, "message": "No workflow steps found"}

        approved_count = 0
        failed_count = 0

        # Iterate through steps and approve those with pending approvals
        for step in steps:
            step_id = step.get("id")
            approval = step.get("approval")

            # Check if step has an approval object
            if not approval:
                continue

            # Check if the approval has an empty or null response
            response = approval.get("response")
            if response is not None and response != {}:
                # Already has a response, skip
                continue

            # This approval needs to be processed
            approval_id = approval.get("id")

            if not approval_id or not step_id:
                logger.warning(
                    f"Missing approval_id or step_id for workflow {workflow_id}, step: {step}"
                )
                failed_count += 1
                continue

            try:
                # Create the approval response
                result = org.create_workflow_step_approval(
                    workflow_id=workflow_id,
                    step_id=step_id,
                    approval_id=approval_id,
                    response_type="approve",
                    note="approved by approve all action"
                )

                if result:
                    approved_count += 1
                    logger.info(
                        f"Approved step {step_id} for org {organization_id}, "
                        f"workflow {workflow_id}, approval {approval_id}"
                    )
                else:
                    failed_count += 1
                    logger.error(
                        f"Failed to approve step {step_id} for org {organization_id}, "
                        f"workflow {workflow_id}"
                    )
            except Exception as step_error:
                failed_count += 1
                logger.error(
                    f"Error approving step {step_id} for org {organization_id}, "
                    f"workflow {workflow_id}: {step_error}"
                )

        logger.info(
            f"Completed approve all for org {organization_id}, workflow {workflow_id}. "
            f"Approved: {approved_count}, Failed: {failed_count}"
        )

        return {
            "approved_count": approved_count,
            "failed_count": failed_count,
            "message": f"Processed {approved_count} approvals successfully"
        }

    except Organization.DoesNotExist:
        logger.error(f"Organization with id {organization_id} does not exist")
        return {"error": "Organization not found", "approved_count": 0}
    except Exception as e:
        logger.error(
            f"Error in workflow_approve_all for org {organization_id}, "
            f"workflow {workflow_id}: {e}"
        )
        raise e
