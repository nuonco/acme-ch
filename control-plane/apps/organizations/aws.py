import json
import boto3
from django.conf import settings


class AWSInstallMixin:
    """
    Mixin for the Organization

    All this does is ensure the acme-sh vendor role has an assume policy for the install's role_delegation role, if it is enabled.
    """

    def get_iam_client(self):
        return boto3.client(
            "iam",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    def get_delegated_role_arn(self):
        """
        Returns the ARN of the install's delegated role based on the org ID.
        """
        if not self.nuon_install_id:
            return None
        # The delegated role ARN follows: arn:aws:iam::<account>:role/<install_id>-delegation
        # This should come from the install's outputs/state
        state = self.nuon_install_state or {}
        outputs = state.get("outputs", {})
        return outputs.get("role_delegation_arn")

    def ensure_assumable(self):
        """
        Ensure the settings.AWS_DELEGATED_ROLE can assume the install's delegated role.

        If enable_delegation is False, removes the trust policy.
        If enable_delegation is True, adds the trust policy.
        """
        if not settings.AWS_DELEGATED_ROLE:
            return

        delegated_role_arn = self.get_delegated_role_arn()
        if not delegated_role_arn:
            return

        # Extract role name from ARN
        role_name = delegated_role_arn.split("/")[-1]

        iam = self.get_iam_client()

        try:
            response = iam.get_role(RoleName=role_name)
            current_policy = response["Role"]["AssumeRolePolicyDocument"]
        except iam.exceptions.NoSuchEntityException:
            return

        statements = current_policy.get("Statement", [])

        # Find existing statement for our delegated role
        vendor_principal = settings.AWS_DELEGATED_ROLE
        existing_statement_idx = None
        for idx, stmt in enumerate(statements):
            principal = stmt.get("Principal", {})
            if isinstance(principal, dict):
                aws_principal = principal.get("AWS", [])
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]
                if vendor_principal in aws_principal:
                    existing_statement_idx = idx
                    break

        if not self.enable_delegation:
            # Remove the trust policy if it exists
            if existing_statement_idx is not None:
                statements.pop(existing_statement_idx)
                current_policy["Statement"] = statements
                iam.update_assume_role_policy(
                    RoleName=role_name,
                    PolicyDocument=json.dumps(current_policy),
                )
            return

        # Add the trust policy if it doesn't exist
        if existing_statement_idx is None:
            new_statement = {
                "Effect": "Allow",
                "Principal": {"AWS": vendor_principal},
                "Action": "sts:AssumeRole",
            }
            statements.append(new_statement)
            current_policy["Statement"] = statements
            iam.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(current_policy),
            )
