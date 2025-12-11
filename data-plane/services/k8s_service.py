"""Service for Kubernetes operations."""

from typing import Any

import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException


class K8sServiceError(Exception):
    """Raised when Kubernetes operation fails."""

    pass


class K8sService:
    """Service for Kubernetes resource operations.

    Handles CRUD operations for CHI, CHK, Namespaces, and other K8s resources.
    """

    def __init__(self, in_cluster: bool = False):
        """Initialize the Kubernetes service.

        Args:
            in_cluster: Whether running inside a K8s cluster.
                       If True, uses in-cluster config. Otherwise uses kubeconfig.
        """
        try:
            if in_cluster:
                config.load_incluster_config()
            else:
                config.load_kube_config()

            self.core_v1 = client.CoreV1Api()
            self.custom_objects = client.CustomObjectsApi()
            self.networking_v1 = client.NetworkingV1Api()

        except Exception as e:
            raise K8sServiceError(f"Failed to initialize K8s client: {str(e)}") from e

    def apply_manifest(
        self, manifest: str, namespace: str | None = None
    ) -> dict[str, Any]:
        """Apply a Kubernetes manifest (create or update).

        Args:
            manifest: YAML manifest as string
            namespace: Namespace to apply to (required for namespaced resources)

        Returns:
            Dictionary with operation result

        Raises:
            K8sServiceError: If apply operation fails
        """
        try:
            # Parse YAML
            resource = yaml.safe_load(manifest)
            if not resource:
                raise K8sServiceError("Empty manifest")

            kind = resource.get("kind")
            api_version = resource.get("apiVersion")
            metadata = resource.get("metadata", {})
            name = metadata.get("name")

            if not all([kind, api_version, name]):
                raise K8sServiceError(
                    "Manifest missing required fields: kind, apiVersion, or metadata.name"
                )

            # Prefer namespace from manifest metadata, fall back to parameter
            manifest_namespace = metadata.get("namespace")
            if manifest_namespace:
                namespace = manifest_namespace
            elif namespace is None:
                namespace = "default"

            # Route to appropriate API based on kind
            if kind == "Namespace":
                return self._apply_namespace(resource)
            elif kind == "Service":
                return self._apply_service(resource, namespace)
            elif kind == "Ingress":
                return self._apply_ingress(resource, namespace)
            elif kind == "EC2NodeClass":
                return self._apply_cluster_scoped_custom_resource(
                    resource, "ec2nodeclasses"
                )
            elif kind == "NodePool":
                return self._apply_cluster_scoped_custom_resource(resource, "nodepools")
            elif kind in ("ClickHouseInstallation", "CHI"):
                return self._apply_custom_resource(
                    resource, namespace, "clickhouseinstallations"
                )
            elif kind in ("ClickHouseKeeper", "CHK"):
                return self._apply_custom_resource(
                    resource, namespace, "clickhousekeepers"
                )
            else:
                # Generic custom resource or unsupported type
                return self._apply_custom_resource(resource, namespace)

        except yaml.YAMLError as e:
            raise K8sServiceError(f"Invalid YAML manifest: {str(e)}") from e
        except ApiException as e:
            # Include response body for better error messages
            error_msg = f"Failed to apply {kind}/{name}: ({e.status}) {e.reason}"
            if e.body:
                try:
                    import json

                    body = json.loads(e.body)
                    if "message" in body:
                        error_msg += f"\n{body['message']}"
                except:
                    error_msg += f"\n{e.body}"
            raise K8sServiceError(error_msg) from e
        except Exception as e:
            raise K8sServiceError(f"Failed to apply manifest: {str(e)}") from e

    def _apply_namespace(self, resource: dict[str, Any]) -> dict[str, Any]:
        """Apply namespace resource."""
        name = resource["metadata"]["name"]
        try:
            # Try to get existing namespace
            self.core_v1.read_namespace(name)
            # Update existing
            result = self.core_v1.patch_namespace(name, resource)
            return {"action": "updated", "kind": "Namespace", "name": name}
        except ApiException as e:
            if e.status == 404:
                # Create new
                result = self.core_v1.create_namespace(resource)
                return {"action": "created", "kind": "Namespace", "name": name}
            raise

    def _apply_service(
        self, resource: dict[str, Any], namespace: str
    ) -> dict[str, Any]:
        """Apply service resource."""
        name = resource["metadata"]["name"]
        try:
            # Try to get existing service
            self.core_v1.read_namespaced_service(name, namespace)
            # Update existing
            result = self.core_v1.patch_namespaced_service(name, namespace, resource)
            return {
                "action": "updated",
                "kind": "Service",
                "name": name,
                "namespace": namespace,
            }
        except ApiException as e:
            if e.status == 404:
                # Create new
                result = self.core_v1.create_namespaced_service(namespace, resource)
                return {
                    "action": "created",
                    "kind": "Service",
                    "name": name,
                    "namespace": namespace,
                }
            raise

    def _apply_ingress(
        self, resource: dict[str, Any], namespace: str
    ) -> dict[str, Any]:
        """Apply ingress resource."""
        name = resource["metadata"]["name"]
        try:
            # Try to get existing ingress
            self.networking_v1.read_namespaced_ingress(name, namespace)
            # Update existing
            result = self.networking_v1.patch_namespaced_ingress(
                name, namespace, resource
            )
            return {
                "action": "updated",
                "kind": "Ingress",
                "name": name,
                "namespace": namespace,
            }
        except ApiException as e:
            if e.status == 404:
                # Create new
                result = self.networking_v1.create_namespaced_ingress(
                    namespace, resource
                )
                return {
                    "action": "created",
                    "kind": "Ingress",
                    "name": name,
                    "namespace": namespace,
                }
            raise

    def get_ingress(self, name: str, namespace: str) -> dict[str, Any] | None:
        """Get ingress resource from cluster with full status.

        Args:
            name: Ingress name
            namespace: Namespace

        Returns:
            Ingress resource as dict (includes status with load balancer info),
            or None if not found
        """
        try:
            ingress = self.networking_v1.read_namespaced_ingress(name, namespace)
            return ingress.to_dict()
        except ApiException as e:
            if e.status == 404:
                return None
            raise K8sServiceError(f"Failed to get ingress {name}: {str(e)}") from e

    def _apply_cluster_scoped_custom_resource(
        self, resource: dict[str, Any], plural: str | None = None
    ) -> dict[str, Any]:
        """Apply cluster-scoped custom resource (EC2NodeClass, NodePool, etc.)."""
        kind = resource["kind"]
        name = resource["metadata"]["name"]
        api_version = resource["apiVersion"]

        # Parse group and version from apiVersion
        if "/" in api_version:
            group, version = api_version.split("/", 1)
        else:
            group = ""
            version = api_version

        # Infer plural if not provided
        if plural is None:
            plural = f"{kind.lower()}s"

        try:
            # Try to get existing resource
            self.custom_objects.get_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                name=name,
            )
            # Update existing
            result = self.custom_objects.patch_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                name=name,
                body=resource,
            )
            return {"action": "updated", "kind": kind, "name": name, "namespace": None}
        except ApiException as e:
            if e.status == 404:
                # Create new
                result = self.custom_objects.create_cluster_custom_object(
                    group=group,
                    version=version,
                    plural=plural,
                    body=resource,
                )
                return {
                    "action": "created",
                    "kind": kind,
                    "name": name,
                    "namespace": None,
                }
            raise

    def _apply_custom_resource(
        self, resource: dict[str, Any], namespace: str, plural: str | None = None
    ) -> dict[str, Any]:
        """Apply namespaced custom resource (CHI, CHK, etc.)."""
        kind = resource["kind"]
        name = resource["metadata"]["name"]
        api_version = resource["apiVersion"]

        # Parse group and version from apiVersion
        if "/" in api_version:
            group, version = api_version.split("/", 1)
        else:
            group = ""
            version = api_version

        # Infer plural if not provided
        if plural is None:
            plural = f"{kind.lower()}s"

        try:
            # Try to get existing resource
            self.custom_objects.get_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=name,
            )
            # Update existing
            result = self.custom_objects.patch_namespaced_custom_object(
                group=group,
                version=version,
                namespace=namespace,
                plural=plural,
                name=name,
                body=resource,
            )
            return {
                "action": "updated",
                "kind": kind,
                "name": name,
                "namespace": namespace,
            }
        except ApiException as e:
            if e.status == 404:
                # Create new
                result = self.custom_objects.create_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural,
                    body=resource,
                )
                return {
                    "action": "created",
                    "kind": kind,
                    "name": name,
                    "namespace": namespace,
                }
            raise

    def get_resource(
        self,
        kind: str,
        name: str,
        namespace: str | None = None,
        api_version: str = "v1",
    ) -> dict[str, Any] | None:
        """Get a Kubernetes resource.

        Args:
            kind: Resource kind (Namespace, CHI, CHK, etc.)
            name: Resource name
            namespace: Namespace (required for namespaced resources)
            api_version: API version

        Returns:
            Resource dictionary if found, None if not found

        Raises:
            K8sServiceError: If operation fails
        """
        try:
            if kind == "Namespace":
                result = self.core_v1.read_namespace(name)
                return client.ApiClient().sanitize_for_serialization(result)

            elif kind == "Service":
                if not namespace:
                    raise K8sServiceError("Namespace required for Service")
                result = self.core_v1.read_namespaced_service(name, namespace)
                return client.ApiClient().sanitize_for_serialization(result)

            elif kind == "Ingress":
                if not namespace:
                    raise K8sServiceError("Namespace required for Ingress")
                result = self.networking_v1.read_namespaced_ingress(name, namespace)
                return client.ApiClient().sanitize_for_serialization(result)

            elif kind in ("ClickHouseInstallation", "CHI"):
                if not namespace:
                    raise K8sServiceError("Namespace required for CHI")
                group, version = (
                    api_version.split("/", 1)
                    if "/" in api_version
                    else ("", api_version)
                )
                result = self.custom_objects.get_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural="clickhouseinstallations",
                    name=name,
                )
                return result

            elif kind in ("ClickHouseKeeper", "CHK"):
                if not namespace:
                    raise K8sServiceError("Namespace required for CHK")
                group, version = (
                    api_version.split("/", 1)
                    if "/" in api_version
                    else ("", api_version)
                )
                result = self.custom_objects.get_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural="clickhousekeepers",
                    name=name,
                )
                return result

            else:
                raise K8sServiceError(f"Unsupported resource kind: {kind}")

        except ApiException as e:
            if e.status == 404:
                return None
            raise K8sServiceError(f"Failed to get {kind}/{name}: {str(e)}") from e

    def delete_resource(
        self,
        kind: str,
        name: str,
        namespace: str | None = None,
        api_version: str = "v1",
    ) -> dict[str, Any]:
        """Delete a Kubernetes resource.

        Args:
            kind: Resource kind
            name: Resource name
            namespace: Namespace (required for namespaced resources)
            api_version: API version

        Returns:
            Dictionary with deletion result

        Raises:
            K8sServiceError: If operation fails
        """
        try:
            if kind == "Namespace":
                self.core_v1.delete_namespace(name)
                return {"action": "deleted", "kind": kind, "name": name}

            elif kind == "Service":
                if not namespace:
                    raise K8sServiceError("Namespace required for Service")
                self.core_v1.delete_namespaced_service(name, namespace)
                return {
                    "action": "deleted",
                    "kind": kind,
                    "name": name,
                    "namespace": namespace,
                }

            elif kind == "Ingress":
                if not namespace:
                    raise K8sServiceError("Namespace required for Ingress")
                self.networking_v1.delete_namespaced_ingress(name, namespace)
                return {
                    "action": "deleted",
                    "kind": kind,
                    "name": name,
                    "namespace": namespace,
                }

            elif kind in ("ClickHouseInstallation", "CHI", "ClickHouseKeeper", "CHK"):
                if not namespace:
                    raise K8sServiceError(f"Namespace required for {kind}")
                group, version = (
                    api_version.split("/", 1)
                    if "/" in api_version
                    else ("", api_version)
                )
                plural = (
                    "clickhouseinstallations"
                    if kind in ("ClickHouseInstallation", "CHI")
                    else "clickhousekeepers"
                )
                self.custom_objects.delete_namespaced_custom_object(
                    group=group,
                    version=version,
                    namespace=namespace,
                    plural=plural,
                    name=name,
                )
                return {
                    "action": "deleted",
                    "kind": kind,
                    "name": name,
                    "namespace": namespace,
                }

            else:
                raise K8sServiceError(f"Unsupported resource kind: {kind}")

        except ApiException as e:
            if e.status == 404:
                return {"action": "not_found", "kind": kind, "name": name}
            raise K8sServiceError(f"Failed to delete {kind}/{name}: {str(e)}") from e
