# EKS Access Entry - allows the delegated role to authenticate to the cluster via kubectl
# Only created when vendor_role_cluster_access is true
resource "aws_eks_access_entry" "delegated" {
  count = local.cluster_access_enabled ? 1 : 0

  cluster_name  = var.eks_cluster_name
  principal_arn = aws_iam_role.delegated[0].arn
  type          = "STANDARD"

  tags = var.tags
}

# EKS Access Policy Association - grants Edit permissions for Karpenter scaling via kubectl
resource "aws_eks_access_policy_association" "delegated_view" {
  count = local.cluster_access_enabled ? 1 : 0

  cluster_name  = var.eks_cluster_name
  principal_arn = aws_eks_access_entry.delegated[0].principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminViewPolicy"

  access_scope {
    type = "cluster"
  }
}
