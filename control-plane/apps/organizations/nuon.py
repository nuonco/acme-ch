from django.conf import settings
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token

from nuon.api.installs import get_install
from nuon.api.installs import get_install_state

from nuon.api.installs import create_install_v2
from nuon.api.installs import get_install_stack_by_install_id
from nuon.api.installs import get_workflows
from nuon.api.installs import get_workflow_steps
from nuon.api.installs import reprovision_install
from nuon.api.installs import create_workflow_step_approval_response
from nuon.models.stderr_err_response import StderrErrResponse
from nuon.models.service_create_install_v2_request import ServiceCreateInstallV2Request
from nuon.models.service_create_install_v2_request_inputs import (
    ServiceCreateInstallV2RequestInputs,
)

from nuon.models.service_create_install_v2_request_aws_account import (
    ServiceCreateInstallV2RequestAwsAccount,
)
from nuon.models.service_reprovision_install_request import (
    ServiceReprovisionInstallRequest,
)
from nuon.models.service_create_workflow_step_approval_response_request import (
    ServiceCreateWorkflowStepApprovalResponseRequest,
)

from common.nuon_client import NuonAPIClient


class NuonInstallMixin:
    """
    Mixin that knows how to fetch nuon data for any model that inherits. expects the model to have a field `nuon_install_id`.

    model: https://github.com/nuonco/nuon-python/blob/main/nuon/models/app_install.py
    """

    def get_client(self):
        return NuonAPIClient().get_client()

    def nuon_create_install(self):
        """
        create the install from nuon using self.install_id as the install id
        """
        if self.nuon_install_id:
            # TODO: add a log here that the install has already been created
            return

        # Load the first user that's a member of this org with the "Operator" group
        operator_group = Group.objects.filter(name="Operator").first()
        operator_user = None
        api_token = ""

        if operator_group:
            operator_user = self.members.filter(groups=operator_group).first()
            if operator_user:
                token, created = Token.objects.get_or_create(user=operator_user)
                api_token = token.key

        inputs = ServiceCreateInstallV2RequestInputs.from_dict(
            dict(
                cluster_name=self.slug,
                cluster_id=self.id,
                deploy_headlamp=str(self.deploy_headlamp),
                acme_ch_api_url=settings.WEB_SERVICE_DOMAIN,
                acme_ch_org_id=self.id,
                acme_ch_api_token=api_token,
            )
        )
        aws_account = ServiceCreateInstallV2RequestAwsAccount(region=self.region)
        nc = NuonAPIClient()
        with nc.get_client() as client:
            body = ServiceCreateInstallV2Request(
                name=self.name,
                aws_account=aws_account,
                inputs=inputs,
                app_id=nc.app_id,
            )

            response = create_install_v2.sync(client=client, body=body)

        if isinstance(response, StderrErrResponse):
            print(response)
            return

        self.nuon_install_id = response.id
        self.save(update_fields=["nuon_install_id"])
        return response

    def get_nuon_install(self):
        """
        fetch the install from nuon using self.install_id as the install id
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            install = get_install.sync(client=client, install_id=self.nuon_install_id)
        data = install.to_dict()
        self.nuon_install = data
        self.save(update_fields=["nuon_install"])
        return data

    def get_provision_workflow(self):
        """
        fetch the provision workflow thee install.
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            install = get_install.sync(client=client, install_id=self.nuon_install_id)
        data = install.to_dict()
        self.nuon_install = data
        self.save(update_fields=["nuon_install"])
        return data

    def get_nuon_install_state(self):
        """
        Fetch the install state from nuon using self.nuon_install_id as the install id.
        Extracts and stores the state information from the install.
        """
        # wrapped in try until action outputs fix lands
        try:
            nc = NuonAPIClient()
            with nc.get_client() as client:
                state = get_install_state.sync(
                    client=client, install_id=self.nuon_install_id
                )

            # Handle error responses
            if isinstance(state, StderrErrResponse):
                print(state)
                return None

            # Handle None response
            if not state:
                return None

            data = state.to_dict()
            self.nuon_install_state = data
            self.save(update_fields=["nuon_install_state"])
            return data
        except Exception as e:
            print(f"Error fetching install state: {e}")
            return None

    def get_install_stack(self):
        """
        fetch the install stack from nuon using self.nuon_install_id as the install id
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            stack = get_install_stack_by_install_id.sync(
                client=client, install_id=self.nuon_install_id
            )
        if not stack:
            return
        data = stack.to_dict()
        self.nuon_install_stack = data
        self.save(update_fields=["nuon_install_stack"])

    def get_workflows(self):
        """
        fetch workflows for the install from nuon using self.nuon_install_id as the install id
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            workflows = get_workflows.sync(
                client=client, install_id=self.nuon_install_id
            )
        if not workflows:
            return

        # Convert list of workflow objects to list of dicts
        data = [workflow.to_dict() for workflow in workflows]
        self.nuon_workflows = data
        self.save(update_fields=["nuon_workflows"])

    def nuon_refresh(self):
        self.get_nuon_install()
        self.get_install_stack()
        self.get_nuon_install_state()
        self.get_workflows()

    def get_workflow_steps(self, workflow_id):
        """
        Fetch workflow steps for a given workflow_id.
        Returns the list of workflow steps as dicts without saving to the model.
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            steps = get_workflow_steps.sync(client=client, workflow_id=workflow_id)

        if isinstance(steps, StderrErrResponse):
            print(steps)
            return None

        if not steps:
            return None

        # Convert list of workflow step objects to list of dicts
        return [step.to_dict() for step in steps]

    def nuon_reprovision_install(self):
        """
        Reprovision the install using self.nuon_install_id as the install id
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            body = ServiceReprovisionInstallRequest()
            response = reprovision_install.sync(
                client=client, install_id=self.nuon_install_id, body=body
            )

        if isinstance(response, StderrErrResponse):
            print(response)
            return

        return response

    def create_workflow_step_approval(
        self, workflow_id, step_id, approval_id, response_type, note=None
    ):
        """
        Create a response for a workflow step approval.

        Args:
            workflow_id (str): The workflow ID
            step_id (str): The workflow step ID
            approval_id (str): The approval ID
            response_type (str): The approval response type (e.g., "approve", "deny")
            note (str, optional): Optional note for the approval response

        Returns:
            ServiceCreateWorkflowStepApprovalResponseResponse or None on error
        """
        nc = NuonAPIClient()
        with nc.get_client() as client:
            body_kwargs = {"response_type": response_type}
            if note is not None:
                body_kwargs["note"] = note

            body = ServiceCreateWorkflowStepApprovalResponseRequest.from_dict(
                body_kwargs
            )
            response = create_workflow_step_approval_response.sync(
                client=client,
                workflow_id=workflow_id,
                step_id=step_id,
                approval_id=approval_id,
                body=body,
            )

        if isinstance(response, StderrErrResponse):
            print(response)
            return None

        return response
