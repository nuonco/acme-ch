"""Service for rendering Jinja2 templates for Kubernetes resources.

Renders templates for ClickHouse cluster resources (CHI/CHK CRDs, namespaces,
services, etc.) managed by Altinity ClickHouse Operator.
"""

import base64
import os
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, TemplateNotFound

from constants import (
    TYPE_SINGLE_NODE,
    TYPE_CLUSTER,
    TYPE_KEEPER,
    INGRESS_NONE,
    INGRESS_PUBLIC,
    INGRESS_TAILNET,
)
from services.credentials import ClusterCredentials


class TemplateServiceError(Exception):
    """Raised when template rendering fails."""

    pass


class TemplateService:
    """Service for rendering Jinja2 templates to Kubernetes manifests.

    Handles template loading and rendering for CHI, CHK, and other K8s resources.
    """

    def __init__(self, templates_dir: str | Path | None = None):
        """Initialize the template service.

        Args:
            templates_dir: Path to templates directory.
                          If None, uses ./templates relative to project root.
        """
        if templates_dir is None:
            # Default to templates/ in project root
            project_root = Path(__file__).parent.parent
            templates_dir = project_root / "templates"

        self.templates_dir = Path(templates_dir)
        if not self.templates_dir.exists():
            raise TemplateServiceError(
                f"Templates directory not found: {self.templates_dir}"
            )

        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # K8s YAML doesn't need autoescaping
            keep_trailing_newline=True,
        )

        # Add custom filters
        self.env.filters["b64encode"] = lambda s: base64.b64encode(s.encode()).decode()

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of template file (relative to templates_dir)
            context: Dictionary of variables to pass to template

        Returns:
            Rendered template as string

        Raises:
            TemplateServiceError: If template not found or rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound as e:
            raise TemplateServiceError(f"Template not found: {template_name}") from e
        except Exception as e:
            raise TemplateServiceError(
                f"Failed to render template {template_name}: {str(e)}"
            ) from e

    def render_namespace(self, cluster: dict[str, Any]) -> str:
        """Render namespace manifest for a ClickHouse cluster.

        Each ClickHouse cluster gets its own namespace.

        Args:
            cluster: ClickHouse cluster data dictionary

        Returns:
            Rendered namespace YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {"cluster": cluster}
        return self.render_template("0-namespace.yaml", context)

    def render_service(self, cluster: dict[str, Any]) -> str:
        """Render service manifest for a ClickHouse cluster.

        Args:
            cluster: ClickHouse cluster data dictionary

        Returns:
            Rendered service YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {"cluster": cluster}
        return self.render_template("4-service.yaml", context)

    def render_ec2_nodeclass(
        self, cluster: dict[str, Any], org: dict[str, Any], karpenter: dict[str, Any], region: str
    ) -> str:
        """Render EC2NodeClass manifest for a ClickHouse cluster.

        Creates dedicated Karpenter node class for this ClickHouse cluster.

        Args:
            cluster: ClickHouse cluster data dictionary
            org: Organization data dictionary
            karpenter: Karpenter configuration from state
            region: AWS region

        Returns:
            Rendered EC2NodeClass YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {"cluster": cluster, "org": org, "karpenter": karpenter, "region": region}
        return self.render_template("1-ec2nc.yaml", context)

    def render_nodepool(
        self, cluster: dict[str, Any], org: dict[str, Any], karpenter: dict[str, Any], region: str
    ) -> str:
        """Render NodePool manifest for a ClickHouse cluster.

        Creates dedicated Karpenter nodepool for this ClickHouse cluster.

        Args:
            cluster: ClickHouse cluster data dictionary
            org: Organization data dictionary
            karpenter: Karpenter configuration from state
            region: AWS region

        Returns:
            Rendered NodePool YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {"cluster": cluster, "org": org, "karpenter": karpenter, "region": region}
        return self.render_template("2-nodepool.yaml", context)

    def render_ingress(
        self,
        cluster: dict[str, Any],
        ingress_type: str,
        public_domain_name: str,
        certificate_arn: str,
    ) -> str:
        """Render ingress manifest for a ClickHouse cluster based on ingress type.

        Args:
            cluster: ClickHouse cluster data dictionary
            ingress_type: Type of ingress (public, tailnet, or none)
            public_domain_name: Public domain name for ingress
            certificate_arn: Certificate ARN for ingress

        Returns:
            Rendered ingress YAML

        Raises:
            TemplateServiceError: If rendering fails or unknown ingress type
        """
        context = {
            "cluster": cluster,
            "public_domain_name": public_domain_name,
            "certificate_arn": certificate_arn,
        }

        if ingress_type == INGRESS_PUBLIC:
            return self.render_template("5-ingress-public.yaml", context)
        elif ingress_type == INGRESS_TAILNET:
            return self.render_template("5-ingress-tailscale.yaml", context)
        else:
            raise TemplateServiceError(
                f"Unknown ingress type: {ingress_type}. "
                f"Expected {INGRESS_PUBLIC} or {INGRESS_TAILNET}"
            )

    def render_secret(
        self, cluster: dict[str, Any], credentials: ClusterCredentials
    ) -> str:
        """Render secret manifest for ClickHouse cluster credentials.

        Args:
            cluster: ClickHouse cluster data dictionary
            credentials: Generated credentials

        Returns:
            Rendered Secret YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {
            "cluster": cluster,
            "credentials": {
                "username": credentials.username,
                "password": credentials.password,
            },
        }

        # Use shared secret template at root level
        return self.render_template("3-secret.yaml", context)

    def render_chi_single_node(
        self,
        cluster: dict[str, Any],
        org: dict[str, Any],
        karpenter: dict[str, Any],
        keeper: dict[str, Any],
        server: dict[str, Any],
        region: str,
        credentials: ClusterCredentials | None = None,
    ) -> str:
        """Render single-node ClickHouse cluster manifest (CHI CRD).

        Args:
            cluster: ClickHouse cluster data dictionary
            org: Organization data dictionary
            karpenter: Karpenter configuration from state
            keeper: ClickHouse Keeper image outputs
            server: ClickHouse Server image outputs
            region: AWS region
            credentials: Optional cluster credentials

        Returns:
            Rendered CHI YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {
            "cluster": cluster,
            "org": org,
            "karpenter": karpenter,
            "keeper": keeper,
            "server": server,
            "region": region,
        }
        if credentials:
            context["credentials"] = {
                "username": credentials.username,
                "password": credentials.password,
            }
        # Assuming template exists or will be created at this path
        return self.render_template("chi-single-node/chi.j2.yaml", context)

    def render_chi_cluster(
        self,
        cluster: dict[str, Any],
        org: dict[str, Any],
        karpenter: dict[str, Any],
        keeper: dict[str, Any],
        server: dict[str, Any],
        region: str,
        credentials: ClusterCredentials | None = None,
    ) -> str:
        """Render multi-node ClickHouse cluster manifest (CHI CRD) with keeper.

        Args:
            cluster: ClickHouse cluster data dictionary
            org: Organization data dictionary
            karpenter: Karpenter configuration from state
            keeper: ClickHouse Keeper image outputs
            server: ClickHouse Server image outputs
            region: AWS region
            credentials: Optional cluster credentials

        Returns:
            Rendered CHI YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {
            "cluster": cluster,
            "org": org,
            "karpenter": karpenter,
            "keeper": keeper,
            "server": server,
            "region": region,
        }
        if credentials:
            context["credentials"] = {
                "username": credentials.username,
                "password": credentials.password,
            }
        return self.render_template("chi-cluster/chi-cluster.j2.yaml", context)

    def render_chk_cluster(
        self,
        cluster: dict[str, Any],
        org: dict[str, Any],
        karpenter: dict[str, Any],
        keeper: dict[str, Any],
        server: dict[str, Any],
        region: str,
    ) -> str:
        """Render ClickHouse Keeper cluster manifest (CHK CRD).

        Args:
            cluster: ClickHouse cluster data dictionary
            org: Organization data dictionary
            karpenter: Karpenter configuration from state
            keeper: ClickHouse Keeper image outputs
            server: ClickHouse Server image outputs
            region: AWS region

        Returns:
            Rendered CHK YAML

        Raises:
            TemplateServiceError: If rendering fails
        """
        context = {
            "cluster": cluster,
            "org": org,
            "karpenter": karpenter,
            "keeper": keeper,
            "server": server,
            "region": region,
        }
        return self.render_template("chi-cluster/chk-cluster.j2.yaml", context)

    def render_cluster_manifests(
        self,
        cluster: dict[str, Any],
        org: dict[str, Any],
        karpenter: dict[str, Any],
        keeper: dict[str, Any],
        server: dict[str, Any],
        public_domain_name: str,
        certificate_arn: str,
        region: str,
        credentials: ClusterCredentials | None = None,
    ) -> list[str]:
        """Render all K8s manifests needed for a ClickHouse cluster.

        Determines ClickHouse cluster type and renders appropriate templates
        (CHI/CHK CRDs, namespace, services, etc.).

        Args:
            cluster: ClickHouse cluster data dictionary (must have 'cluster_type' field)
            org: Organization data dictionary
            karpenter: Karpenter configuration from state
            keeper: ClickHouse Keeper image outputs
            server: ClickHouse Server image outputs
            public_domain_name: Public domain name for ingress
            certificate_arn: Certificate ARN for ingress
            region: AWS region
            credentials: Optional credentials (required for CHI types if creating new ClickHouse cluster)

        Returns:
            List of rendered manifest strings

        Raises:
            TemplateServiceError: If ClickHouse cluster type unknown or rendering fails
        """
        manifests = []

        # 1. Namespace
        manifests.append(self.render_namespace(cluster))

        # 2. EC2NodeClass
        manifests.append(self.render_ec2_nodeclass(cluster, org, karpenter, region))

        # 3. NodePool
        manifests.append(self.render_nodepool(cluster, org, karpenter, region))

        # 4. Secret (conditional - only if credentials provided)
        # 5. CHI resources
        # 6. CHK resources (conditional)
        cluster_type = cluster.get("cluster_type", "")

        if cluster_type == TYPE_SINGLE_NODE:
            if credentials:
                # Render secret only if credentials provided (new cluster)
                manifests.append(self.render_secret(cluster, credentials))
            manifests.append(
                self.render_chi_single_node(
                    cluster, org, karpenter, keeper, server, region, credentials
                )
            )
        elif cluster_type == TYPE_KEEPER:
            manifests.append(
                self.render_chk_cluster(cluster, org, karpenter, keeper, server, region)
            )
        elif cluster_type == TYPE_CLUSTER:
            # Multi-node cluster with keeper
            if credentials:
                # Render secret only if credentials provided (new cluster)
                manifests.append(self.render_secret(cluster, credentials))
            manifests.append(
                self.render_chi_cluster(
                    cluster, org, karpenter, keeper, server, region, credentials
                )
            )
            manifests.append(
                self.render_chk_cluster(cluster, org, karpenter, keeper, server, region)
            )
        else:
            raise TemplateServiceError(
                f"Unknown cluster type: {cluster_type}. "
                f"Expected {TYPE_SINGLE_NODE}, {TYPE_KEEPER}, or {TYPE_CLUSTER}"
            )

        # 7. Service
        manifests.append(self.render_service(cluster))

        # 8. Ingress (conditional - only if ingress_type is public or tailnet)
        ingress_type = cluster.get("ingress_type", None)
        if ingress_type in (INGRESS_PUBLIC, INGRESS_TAILNET):
            manifests.append(
                self.render_ingress(cluster, ingress_type, public_domain_name, certificate_arn)
            )

        return manifests
