"""Constants for ACME ClickHouse Data Plane."""

# Cluster Types
TYPE_SINGLE_NODE = "single_node"
TYPE_CLUSTER = "cluster"
TYPE_KEEPER = "keeper"

TYPE_CHOICES = [
    (TYPE_SINGLE_NODE, "Single Node"),
    (TYPE_CLUSTER, "Cluster"),
    (TYPE_KEEPER, "Keeper"),
]

# Ingress Types
INGRESS_NONE = "none"
INGRESS_PUBLIC = "public"
INGRESS_TAILNET = "tailnet"

INGRESS_CHOICES = [
    (INGRESS_NONE, "No Ingress: accessible only from within cluster"),
    (INGRESS_PUBLIC, "Public Ingress: accessible from the internet"),
    (INGRESS_TAILNET, "Tailnet Ingress: accessible only via the tailnet"),
]
