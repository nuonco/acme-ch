additional_namespaces = [
  "clickhouse",
  "tailscale",
  "acme-ch",
]

additional_tags = {
  "app.nuon.co/name" = "acme-ch-data-plane"
  "org.acme.sh/id" = "{{ .nuon.inputs.inputs.cluster_id }}"
  acme = "true"
}


maintenance_role_eks_access_entry_policy_associations = {
  eks_admin = {
    policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSAdminPolicy"
    access_scope = {
      type = "cluster"
    }
  }
  eks_view = {
    policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
    access_scope = {
      type = "cluster"
    }
  }
}
