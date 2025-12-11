#!/usr/bin/env bash

set -e
set -o pipefail
set -u

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] VENDOR_ROLE_ARN [ROLE_NAME]

! For demonstration purposes only !

Create an IAM role for this application that can attach policies to the vendor role.

This role should be assumed by the control-plane application to manage
policy attachments for role delegation.

Arguments:
  VENDOR_ROLE_ARN  ARN of the vendor role to manage (required)
  ROLE_NAME        Name for the app role (default: acme-ch-app-role)

Options:
  -h, --help       Show this help message and exit

Environment Variables:
  AWS_REGION       AWS region (default: us-west-2)

Examples:
  $(basename "$0") arn:aws:iam::123456789012:role/acme-ch-vendor-role
  $(basename "$0") arn:aws:iam::123456789012:role/acme-ch-vendor-role my-app-role
EOF
  exit 0
}

[[ "${1:-}" =~ ^(-h|--help)$ ]] && usage

if [[ $# -lt 1 ]]; then
  echo "Error: VENDOR_ROLE_ARN is required" >&2
  usage
fi

AWS_PAGER=""
VENDOR_ROLE_ARN="$1"
ROLE_NAME="${2:-acme-ch-app-role}"
REGION="${AWS_REGION:-us-west-2}"

VENDOR_ROLE_NAME=$(echo "$VENDOR_ROLE_ARN" | sed 's/.*:role\///')

echo "Creating app role: $ROLE_NAME"
echo "With permission to attach policies to: $VENDOR_ROLE_ARN"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

PERMISSIONS_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:PutRolePolicy",
        "iam:DeleteRolePolicy"
      ],
      "Resource": "${VENDOR_ROLE_ARN}"
    }
  ]
}
EOF
)

aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --description "App role for managing vendor role policy attachments" \
  --tags Key=Purpose,Value=acme-ch-app-delegation

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "manage-vendor-role-policy" \
  --policy-document "$PERMISSIONS_POLICY"

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)

echo ""
echo "App role created successfully!"
echo "Role ARN: $ROLE_ARN"
echo ""
echo "This role can attach/delete inline policies on: $VENDOR_ROLE_ARN"
