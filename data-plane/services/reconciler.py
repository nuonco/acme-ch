"""Core reconciliation logic for ACME ClickHouse clusters.

Note: "Cluster" in this context refers to ClickHouse clusters managed by
Altinity ClickHouse Operator CRDs (CHI/CHK), not Kubernetes clusters.
All clusters run within the same Kubernetes cluster.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml

from constants import TYPE_SINGLE_NODE, TYPE_CLUSTER, TYPE_KEEPER
from services.api_service import APIService, APIServiceError
from services.k8s_service import K8sService, K8sServiceError
from services.template_service import TemplateService, TemplateServiceError


class ReconcileAction(Enum):
    """Action to take during reconciliation."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NOOP = "noop"


class ReconcileStatus(Enum):
    """Status of reconciliation operation."""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ManifestResult:
    """Result of applying a single manifest."""

    kind: str
    name: str
    namespace: str | None
    action: str  # created, updated, failed
    error: Exception | None = None


@dataclass
class ReconcileResult:
    """Result of a ClickHouse cluster reconciliation."""

    cluster_id: str
    cluster_name: str
    status: ReconcileStatus
    action: ReconcileAction
    message: str
    error: Exception | None = None
    manifest_results: list[ManifestResult] = field(default_factory=list)


class ReconcilerError(Exception):
    """Raised when reconciliation fails."""

    pass


class Reconciler:
    """Core reconciliation logic for ClickHouse clusters.

    Orchestrates the reconciliation process:
    1. Fetch org, state, and ClickHouse clusters from control plane API
    2. For each ClickHouse cluster, determine desired state
    3. Compare with actual K8s resources (CHI/CHK CRDs, namespaces, etc.)
    4. Apply necessary changes (create/update/delete K8s manifests)

    Note: This reconciles ClickHouse clusters (CHI/CHK resources) within
    a single Kubernetes cluster, not multiple K8s clusters.
    """

    def __init__(
        self,
        api_service: APIService | None = None,
        k8s_service: K8sService | None = None,
        template_service: TemplateService | None = None,
        dry_run: bool = False,
    ):
        """Initialize the reconciler.

        Args:
            api_service: API service instance (creates default if None)
            k8s_service: K8s service instance (creates default if None)
            template_service: Template service instance (creates default if None)
            dry_run: If True, don't apply changes to K8s
        """
        from config import get_config

        self.api_service = api_service or APIService()
        config = get_config()
        self.k8s_service = k8s_service or K8sService(in_cluster=config.in_cluster)
        self.template_service = template_service or TemplateService()
        self.dry_run = dry_run

    def reconcile_all_clusters(
        self,
        cluster_id: str | None = None,
        fail_fast: bool = False,
    ) -> list[ReconcileResult]:
        """Reconcile all ClickHouse clusters for the organization.

        Fetches ClickHouse cluster definitions from control plane and reconciles
        each as K8s resources (CHI/CHK CRDs) within the current K8s cluster.

        Args:
            cluster_id: Optional specific ClickHouse cluster ID to reconcile
            fail_fast: If True, stop on first error

        Returns:
            List of reconciliation results

        Raises:
            ReconcilerError: If fail_fast=True and an error occurs
        """
        results = []

        try:
            # Step 1: Get org data
            org = self.api_service.get_org()

            # Step 2: Get org install state (includes Karpenter, keeper, and server config)
            state = self.api_service.get_install_state()

            # Extract karpenter from sandbox.outputs.karpenter
            karpenter = state.get("sandbox", {}).get("outputs", {}).get("karpenter", {})

            # Extract public_domain_name from sandbox.outputs.nuon_dns.public_domain.name
            public_domain_name = (
                state.get("sandbox", {})
                .get("outputs", {})
                .get("nuon_dns", {})
                .get("public_domain", {})
                .get("name", "")
            )

            # Extract keeper, server, and certificate from components
            components = state.get("components", {})
            keeper = components.get("img_clickhouse_keeper", {}).get("outputs", {})
            server = components.get("img_clickhouse_server", {}).get("outputs", {})
            certificate_arn = (
                components.get("certificate", {}).get("outputs", {}).get("arn", "")
            )

            # Extract region from install_stack.outputs.region
            region = state.get("install_stack", {}).get("outputs", {}).get("region")
            if not region:
                raise ReconcilerError(
                    "Region not found in install_stack.outputs.region. "
                    "Cannot proceed with template rendering without a valid AWS region."
                )

            # Step 3: Get ClickHouse clusters
            clusters = self.api_service.get_clusters(cluster_id=cluster_id)

            if not clusters:
                return [
                    ReconcileResult(
                        cluster_id="",
                        cluster_name="",
                        status=ReconcileStatus.SKIPPED,
                        action=ReconcileAction.NOOP,
                        message="No ClickHouse clusters found",
                    )
                ]

            # Step 4: Reconcile each ClickHouse cluster
            for cluster in clusters:
                result = self._reconcile_cluster(
                    cluster,
                    org,
                    karpenter,
                    keeper,
                    server,
                    public_domain_name,
                    certificate_arn,
                    region,
                )
                results.append(result)

                if fail_fast and result.status == ReconcileStatus.FAILED:
                    raise ReconcilerError(
                        f"Reconciliation failed for cluster {cluster.get('id')}: {result.message}"
                    )

        except (APIServiceError, TemplateServiceError, K8sServiceError) as e:
            error_result = ReconcileResult(
                cluster_id="",
                cluster_name="",
                status=ReconcileStatus.FAILED,
                action=ReconcileAction.NOOP,
                message=f"Failed to fetch data from API: {str(e)}",
                error=e,
            )
            results.append(error_result)

            if fail_fast:
                raise ReconcilerError(str(e)) from e

        return results

    def _reconcile_cluster(
        self,
        cluster: dict[str, Any],
        org: dict[str, Any],
        karpenter: dict[str, Any],
        keeper: dict[str, Any],
        server: dict[str, Any],
        public_domain_name: str,
        certificate_arn: str,
        region: str,
    ) -> ReconcileResult:
        """Reconcile a single ClickHouse cluster.

        Creates or updates K8s resources (namespace, CHI/CHK CRDs, services, etc.)
        for a single ClickHouse cluster definition.

        Args:
            cluster: ClickHouse cluster data from control plane API
            org: Organization data
            karpenter: Karpenter configuration
            keeper: ClickHouse Keeper image outputs
            server: ClickHouse Server image outputs
            public_domain_name: Public domain name for ingress
            certificate_arn: Certificate ARN for ingress
            region: AWS region

        Returns:
            ReconcileResult indicating what happened
        """
        cluster_id = cluster.get("id", "unknown")
        cluster_name = cluster.get("name", "unknown")
        cluster_type = cluster.get("type", "")

        try:
            # Determine desired state from ClickHouse cluster data
            desired_state = cluster.get("status", "active").lower()

            if desired_state == "deleted" or desired_state == "deleting":
                # ClickHouse cluster should be deleted
                return self._delete_cluster(cluster)

            # Check if ClickHouse cluster's namespace exists in K8s
            exists = self._cluster_exists(cluster)

            if exists:
                action = ReconcileAction.UPDATE
                action_verb = "updated"
            else:
                action = ReconcileAction.CREATE
                action_verb = "created"

            # ClickHouse cluster should exist - render K8s manifests
            manifests = self.template_service.render_cluster_manifests(
                cluster=cluster,
                org=org,
                karpenter=karpenter,
                keeper=keeper,
                server=server,
                public_domain_name=public_domain_name,
                certificate_arn=certificate_arn,
                region=region,
            )

            # Apply manifests individually and track results
            # Also track specific manifests for status update
            manifest_results = []
            chi_manifest = None
            chk_manifest = None
            ingress_manifest = None

            for manifest in manifests:
                # Parse manifest to extract kind/name for tracking
                kind = "Unknown"
                name = "unknown"
                namespace = cluster_name
                resource = None

                try:
                    resource = yaml.safe_load(manifest)
                    if resource:
                        kind = resource.get("kind", "Unknown")
                        metadata = resource.get("metadata", {})
                        name = metadata.get("name", "unknown")
                        namespace = metadata.get("namespace") or cluster_name

                        # Track specific manifests for status update
                        if kind == "ClickHouseInstallation":
                            chi_manifest = resource
                        elif kind == "ClickHouseKeeperInstallation":
                            chk_manifest = resource
                        elif kind == "Ingress":
                            ingress_manifest = resource

                except Exception as parse_error:
                    # If we can't parse, record error and continue
                    manifest_results.append(
                        ManifestResult(
                            kind="Unknown",
                            name="unknown",
                            namespace=cluster_name,
                            action="failed",
                            error=parse_error,
                        )
                    )
                    continue

                if not self.dry_run:
                    try:
                        # Apply manifest
                        result = self.k8s_service.apply_manifest(
                            manifest=manifest,
                            namespace=cluster_name,
                        )

                        # Record success
                        manifest_results.append(
                            ManifestResult(
                                kind=kind,
                                name=name,
                                namespace=namespace,
                                action=result.get("action", "applied"),
                                error=None,
                            )
                        )
                    except Exception as apply_error:
                        # Record failure but continue with remaining manifests
                        manifest_results.append(
                            ManifestResult(
                                kind=kind,
                                name=name,
                                namespace=namespace,
                                action="failed",
                                error=apply_error,
                            )
                        )
                else:
                    # Dry-run mode - record as "would apply"
                    manifest_results.append(
                        ManifestResult(
                            kind=kind,
                            name=name,
                            namespace=namespace,
                            action="would apply",
                            error=None,
                        )
                    )

            # Determine overall success based on manifest results
            failed_manifests = [m for m in manifest_results if m.action == "failed"]
            if failed_manifests:
                status = ReconcileStatus.FAILED
                success_count = len(manifest_results) - len(failed_manifests)
                message = f"Applied {success_count}/{len(manifest_results)} manifests successfully"
            else:
                status = ReconcileStatus.SUCCESS
                if self.dry_run:
                    message = f"Would apply {len(manifest_results)} manifests (dry-run)"
                else:
                    message = (
                        f"All {len(manifest_results)} manifests applied successfully"
                    )

            # Send status update to control plane (not in dry-run mode)
            if not self.dry_run:
                self._send_status_update(
                    cluster,
                    status,
                    failed_manifests,
                    chi_manifest=chi_manifest,
                    chk_manifest=chk_manifest,
                    ingress_manifest=ingress_manifest,
                )

            return ReconcileResult(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                status=status,
                action=action,
                message=message,
                manifest_results=manifest_results,
            )

        except (TemplateServiceError, K8sServiceError) as e:
            return ReconcileResult(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                status=ReconcileStatus.FAILED,
                action=ReconcileAction.NOOP,
                message=f"Failed to reconcile ClickHouse cluster: {str(e)}",
                error=e,
            )

    def _get_cluster_namespace(self, cluster: dict[str, Any]) -> str | None:
        """Get the Kubernetes namespace for a ClickHouse cluster.

        Uses cluster.slug which matches the namespace used in templates.

        Args:
            cluster: ClickHouse cluster data

        Returns:
            Namespace string (cluster slug), or None if not available
        """
        return cluster.get("slug")

    def _cluster_exists(self, cluster: dict[str, Any]) -> bool:
        """Check if a ClickHouse cluster exists in Kubernetes.

        Each ClickHouse cluster has its own namespace, so we check for namespace existence.

        Args:
            cluster: ClickHouse cluster data

        Returns:
            True if ClickHouse cluster's namespace exists, False otherwise
        """
        try:
            namespace = self._get_cluster_namespace(cluster)
            if not namespace:
                return False

            # Check if namespace exists
            ns = self.k8s_service.get_resource(
                kind="Namespace",
                name=namespace,
            )
            return ns is not None

        except K8sServiceError:
            return False

    def _delete_cluster(self, cluster: dict[str, Any]) -> ReconcileResult:
        """Delete a ClickHouse cluster from Kubernetes.

        Deletes the namespace, which cascades to all resources (CHI/CHK CRDs, etc.).

        Args:
            cluster: ClickHouse cluster data

        Returns:
            ReconcileResult indicating deletion status
        """
        cluster_id = cluster.get("id", "unknown")
        cluster_name = cluster.get("name", "unknown")
        namespace = self._get_cluster_namespace(cluster) or cluster_name

        try:
            # Check if ClickHouse cluster exists
            if not self._cluster_exists(cluster):
                return ReconcileResult(
                    cluster_id=cluster_id,
                    cluster_name=cluster_name,
                    status=ReconcileStatus.SKIPPED,
                    action=ReconcileAction.NOOP,
                    message="ClickHouse cluster already deleted",
                )

            if not self.dry_run:
                # Delete namespace (cascades to all CHI/CHK resources within)
                self.k8s_service.delete_resource(
                    kind="Namespace",
                    name=namespace,
                )
                message = "ClickHouse cluster deleted successfully"
            else:
                message = "ClickHouse cluster would be deleted (dry-run)"

            return ReconcileResult(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                status=ReconcileStatus.SUCCESS,
                action=ReconcileAction.DELETE,
                message=message,
            )

        except K8sServiceError as e:
            return ReconcileResult(
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                status=ReconcileStatus.FAILED,
                action=ReconcileAction.DELETE,
                message=f"Failed to delete ClickHouse cluster: {str(e)}",
                error=e,
            )

    def _send_status_update(
        self,
        cluster: dict[str, Any],
        reconcile_status: ReconcileStatus,
        failed_manifests: list[Any],
        chi_manifest: dict[str, Any] | None = None,
        chk_manifest: dict[str, Any] | None = None,
        ingress_manifest: dict[str, Any] | None = None,
    ) -> None:
        """Send status update to control plane after reconciliation.

        Args:
            cluster: Cluster data
            reconcile_status: Status of the reconciliation
            failed_manifests: List of failed manifest results
            chi_manifest: ClickHouseInstallation manifest (parsed YAML)
            chk_manifest: ClickHouseKeeperInstallation manifest (parsed YAML)
            ingress_manifest: Ingress manifest (parsed YAML)
        """
        cluster_id = cluster.get("id")

        # Map reconcile status to control plane status
        if reconcile_status == ReconcileStatus.SUCCESS:
            cp_status = "ready"
        elif reconcile_status == ReconcileStatus.FAILED:
            cp_status = "error"
        else:
            cp_status = "pending"

        # Collect error messages from failed manifests
        errors = []
        if failed_manifests:
            for manifest in failed_manifests:
                error_msg = f"{manifest.kind}/{manifest.name}: {str(manifest.error)}"
                errors.append(error_msg)

        try:
            # Send status update to control plane with manifest data
            self.api_service.update_cluster_status(
                cluster_id=cluster_id,
                status=cp_status,
                ingress=ingress_manifest,
                chi=chi_manifest,
                chk=chk_manifest,
                errors=errors if errors else None,
            )

        except Exception as e:
            # Log error but don't fail reconciliation
            print(
                f"Warning: Failed to send status update for cluster {cluster_id}: {e}"
            )
