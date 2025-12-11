data "aws_caller_identity" "current" {}

locals {
  prefix                 = var.nuon_id
  enabled                = var.vendor_role_arn != ""
  cluster_access_enabled = local.enabled && var.vendor_role_cluster_access

  # EKS cluster log group follows convention: /aws/eks/<cluster-name>/cluster
  eks_log_group_name = "/aws/eks/${var.eks_cluster_name}/cluster"
  eks_log_group_arn  = "arn:aws:logs:${var.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.eks_log_group_name}"
}

resource "aws_iam_role" "delegated" {
  count = local.enabled ? 1 : 0

  name        = "${local.prefix}-vendor-delegated"
  description = "Role allowing vendor cross-account access to this install's resources"
  tags        = var.tags

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { AWS = var.vendor_role_arn }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "logs_access" {
  count = local.enabled ? 1 : 0

  role       = aws_iam_role.delegated[0].name
  policy_arn = aws_iam_policy.cloudwatch_logs_access[0].arn
}

resource "aws_iam_role_policy_attachment" "eks_access" {
  count = local.enabled ? 1 : 0

  role       = aws_iam_role.delegated[0].name
  policy_arn = aws_iam_policy.eks_cluster_access[0].arn
}
