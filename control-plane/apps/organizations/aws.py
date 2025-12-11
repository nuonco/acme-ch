import json
import boto3
from django.conf import settings


class AWSInstallMixin:
    """
    Mixin for the Organization

    All this does is ensure the acme-sh vendor role has an assume policy for the install's role_delegation role, if it is enabled.
    """

    def get_iam_client(self):
        sts = boto3.client(
            "sts",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        assumed = sts.assume_role(
            RoleArn=settings.AWS_IAM_ROLE,
            RoleSessionName="acme-ch-control-plane",
        )
        credentials = assumed["Credentials"]
        return boto3.client(
            "iam",
            aws_access_key_id=credentials["AccessKeyId"],
            aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"],
        )

    def get_delegated_role_arn(self):
        """
        Returns the ARN of the install's delegated role based on the org ID.
        """
        if not self.nuon_install_id:
            return None
        state = self.nuon_install_state or {}
        components = state.get("components", {})
        role_delegation = components.get("role_delegation", {})
        outputs = role_delegation.get("outputs", {})
        return outputs.get("delegated_role_arn")

    def ensure_assumable(self):
        """
        Ensure the settings.AWS_DELEGATED_ROLE can assume the install's delegated role.

        If enable_delegation is False, removes the trust policy.
        If enable_delegation is True, adds the trust policy.

        The role we have control over is settings.AWS_DELEGATED_ROLE.
        This role has been given permission to assume the role from self.get_delegated_role_arn().

        This method adds a policy on AWS_DELEGATED_ROLE.
        """
        if not settings.AWS_DELEGATED_ROLE:
            return

        delegated_role_arn = self.get_delegated_role_arn()
        if not delegated_role_arn:
            return

        vendor_role_name = settings.AWS_DELEGATED_ROLE.split("/")[-1]
        policy_name = f"assume-{self.nuon_install_id}"

        iam = self.get_iam_client()

        if not self.enable_delegation:
            try:
                iam.delete_role_policy(
                    RoleName=vendor_role_name,
                    PolicyName=policy_name,
                )
            except iam.exceptions.NoSuchEntityException:
                pass
            return

        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": delegated_role_arn,
                }
            ],
        }

        iam.put_role_policy(
            RoleName=vendor_role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document),
        )
