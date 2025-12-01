from django.db import models
from django.utils import timezone
from common.models import BaseModel
from common.validators import rfc1123_validator
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class CHClusterStatus:
    """
    A struct to hold data about the cluster.
    ingress: k8s ingress as a json payload
    chi: CHI altinity/operator CRD as a json payload
    chk: CHK altinity/operator CRD as a json payload
    status: one of ready, pending, error.
    errors: optional list of error messages
    created_at: UTC timestamp when the status was created
    """

    STATUS_READY = "ready"
    STATUS_PENDING = "pending"
    STATUS_ERROR = "error"

    STATUS_CHOICES = [STATUS_READY, STATUS_PENDING, STATUS_ERROR]

    ingress: Optional[Dict[str, Any]] = None
    chi: Optional[Dict[str, Any]] = None
    chk: Optional[Dict[str, Any]] = None
    status: str = STATUS_PENDING
    errors: Optional[List[str]] = None
    created_at: str = field(default_factory=lambda: timezone.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert ClusterStatus to a dictionary for JSON storage."""
        return {
            "ingress": self.ingress,
            "chi": self.chi,
            "chk": self.chk,
            "status": self.status,
            "errors": self.errors,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "CHClusterStatus":
        """Create ClusterStatus instance from a dictionary."""
        if not data:
            return cls()
        return cls(
            ingress=data.get("ingress"),
            chi=data.get("chi"),
            chk=data.get("chk"),
            status=data.get("status", cls.STATUS_PENDING),
            errors=data.get("errors"),
            created_at=data.get("created_at", timezone.now().isoformat()),
        )

    def is_ready(self) -> bool:
        """Check if the cluster is ready."""
        return self.status == self.STATUS_READY

    def is_pending(self) -> bool:
        """Check if the cluster is pending."""
        return self.status == self.STATUS_PENDING

    def is_error(self) -> bool:
        """Check if the cluster has an error."""
        return self.status == self.STATUS_ERROR

    def get_ingress_hostname(self) -> Optional[str]:
        """
        Get the load balancer hostname from the ingress status.

        Returns the hostname from:
        1. status.loadBalancer.ingress[0].hostname (first priority)
        2. metadata.annotations["external-dns.alpha.kubernetes.io/hostname"] (fallback)

        Returns None if ingress is not present or hostname is not found.
        """
        if not self.ingress:
            return None

        try:
            # First try to get hostname from load balancer ingress list
            load_balancer = self.ingress.get("status", {}).get("loadBalancer", {})
            ingress_list = load_balancer.get("ingress", [])

            if ingress_list and len(ingress_list) > 0:
                hostname = ingress_list[0].get("hostname")
                if hostname:
                    return hostname

            # Fallback to external-dns annotation if present
            annotations = self.ingress.get("metadata", {}).get("annotations", {})
            external_dns_hostname = annotations.get("external-dns.alpha.kubernetes.io/hostname")
            if external_dns_hostname:
                return external_dns_hostname

        except (AttributeError, TypeError):
            return None

        return None


class CHCluster(BaseModel):
    prefix = "cls"

    TYPE_SINGLE_NODE = "single_node"
    TYPE_CLUSTER = "cluster"
    TYPE_KEEPER = "keeper"

    TYPE_CHOICES = [
        (TYPE_SINGLE_NODE, "Single Node"),
        (TYPE_CLUSTER, "Cluster"),
        (TYPE_KEEPER, "Keeper"),
    ]

    INGRESS_NONE = "none"
    INGRESS_PUBLIC = "public"
    INGRESS_TAILNET = "tailnet"

    INGRESS_CHOICES = [
        (INGRESS_NONE, "No Ingress: accessible only from within cluster"),
        (INGRESS_PUBLIC, "Public Ingress: accessible from the internet"),
        (INGRESS_TAILNET, "Tailnet Ingress: accessible only via the tailnet"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="ch_clusters"
    )
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(validators=[rfc1123_validator])
    cluster_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_SINGLE_NODE
    )
    ingress_type = models.CharField(
        max_length=20, choices=INGRESS_CHOICES, default=INGRESS_NONE
    )
    status = models.JSONField(blank=True, null=True, default=dict)
    status_history = models.JSONField(blank=True, null=True, default=list)

    class Meta:
        unique_together = ("organization", "slug")

    def __str__(self):
        return f"{self.name} ({self.identifier})"

    @property
    def cluster_status(self) -> CHClusterStatus:
        """
        Get the cluster status as a CHClusterStatus object.
        """
        return CHClusterStatus.from_dict(self.status)

    def update_status(
        self,
        status: Optional[str] = None,
        ingress: Optional[Dict[str, Any]] = None,
        chi: Optional[Dict[str, Any]] = None,
        chk: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        """
        Update the cluster status fields and add to status history.
        Maintains only the 20 most recent status entries in history.
        """
        current_status = self.cluster_status

        if status is not None:
            current_status.status = status
        if ingress is not None:
            current_status.ingress = ingress
        if chi is not None:
            current_status.chi = chi
        if chk is not None:
            current_status.chk = chk
        if errors is not None:
            current_status.errors = errors

        # Update current status
        self.status = current_status.to_dict()

        # Add to status history
        if self.status_history is None:
            self.status_history = []

        self.status_history.append(self.status)

        # Keep only the 20 most recent entries
        if len(self.status_history) > 20:
            self.status_history = self.status_history[-20:]

        self.save(update_fields=["status", "status_history"])
