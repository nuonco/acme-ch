# Role Delegation

If you want to deploy this for testing and you'd like to enable role delegation, you'll need:

1. A role to delegate to
2. A role for this app that is allowed to update the policy for the role from step 1.

For each org:install, if vendor role delegation is enabled, the following policy will be created:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "${INSTALL_ROLE_ARN}"
    }
  ]
}
```

using the python equivalent of:

```bash
aws iam put-role-policy \
  --role-name "$AWS_DELEGATED_ROLE" \
  --policy-name "{{.nuon.install.id}}-assume-role" \
  --policy-document "$POLICY_DOCUMENT"
```

## Scripts

To generate a vendor role for delegation:

- ./scripts/vendor-role.sh

To generate a role for this applicaton:

- ./scripts/app-role.sh $VENDOR_ROLE_ARN
