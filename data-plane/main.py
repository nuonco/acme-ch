"""ACME ClickHouse Data Plane Agent CLI.

Manages ClickHouse clusters (CHI/CHK CRDs) via Altinity ClickHouse Operator
within a single Kubernetes cluster. Note: "cluster" in this context refers to
ClickHouse clusters, not Kubernetes clusters.
"""

import sys
from typing import Any

import fire

from config import ConfigError, get_config
from services.reconciler import Reconciler, ReconcileStatus, SecretInfo


class DataPlaneAgent:
    """ACME ClickHouse Data Plane Agent.

    Manages ClickHouse clusters (CHI/CHK CRDs) via Altinity ClickHouse Operator
    based on control plane state. All ClickHouse clusters run within the same
    Kubernetes cluster where this agent executes.
    """

    def __init__(self):
        """Initialize the agent."""
        try:
            self.config = get_config()
        except ConfigError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)

    def reconcile(
        self,
        cluster_id: str | None = None,
        dry_run: bool = False,
        fail_fast: bool = False,
        verbose: bool = False,
    ) -> None:
        """Reconcile ClickHouse clusters.

        Fetches ClickHouse cluster definitions from control plane and reconciles
        K8s resources (CHI/CHK CRDs, namespaces, services, etc.) within the
        current Kubernetes cluster.

        Args:
            cluster_id: Optional specific ClickHouse cluster ID to reconcile
            dry_run: Show what would be done without making changes
            fail_fast: Stop on first error
            verbose: Show detailed output

        Examples:
            python main.py reconcile
            python main.py reconcile --cluster-id=abc123
            python main.py reconcile --dry-run --verbose
            python main.py reconcile --fail-fast
        """
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text

        console = Console()

        try:
            # Show header
            if verbose:
                header_text = Text()
                header_text.append("Starting reconciliation\n", style="bold cyan")
                header_text.append(f"Organization: {self.config.org_id}\n")
                if cluster_id:
                    header_text.append(
                        f"Filtering to cluster: {cluster_id}\n", style="yellow"
                    )
                if dry_run:
                    header_text.append(
                        "Mode: DRY-RUN (no changes will be applied)",
                        style="yellow bold",
                    )
                console.print(
                    Panel(header_text, title="Reconciliation", border_style="cyan")
                )
                console.print()

            # Create reconciler
            reconciler = Reconciler(dry_run=dry_run)

            # Run reconciliation
            results = reconciler.reconcile_all_clusters(
                cluster_id=cluster_id,
                fail_fast=fail_fast,
            )

            # Build results table
            table = Table(
                show_header=True,
                header_style="bold magenta",
                title="Reconciliation Results",
            )
            table.add_column("Status", style="dim", width=10)
            table.add_column("Cluster Name", style="cyan")
            table.add_column("Message", style="white")

            success_count = 0
            failed_count = 0
            skipped_count = 0

            for result in results:
                if result.status == ReconcileStatus.SUCCESS:
                    success_count += 1
                    status_text = Text("✓ SUCCESS", style="green bold")
                    table.add_row(status_text, result.cluster_name, result.message)
                    if verbose and result.error:
                        table.add_row("", "", f"Error: {result.error}", style="red dim")
                elif result.status == ReconcileStatus.FAILED:
                    failed_count += 1
                    status_text = Text("✗ FAILED", style="red bold")
                    table.add_row(status_text, result.cluster_name, result.message)
                    if verbose and result.error:
                        table.add_row("", "", f"Error: {result.error}", style="red dim")
                else:  # SKIPPED
                    skipped_count += 1
                    if verbose:
                        status_text = Text("- SKIPPED", style="yellow")
                        table.add_row(status_text, result.cluster_name, result.message)

            console.print(table)
            console.print()

            # Always show secret info (regardless of verbosity)
            for result in results:
                if result.secret_info:
                    secret = result.secret_info
                    if secret.created:
                        console.print(
                            f"[green]Secret created:[/green] {secret.name} in namespace {secret.namespace}"
                        )
                    else:
                        console.print(
                            f"[dim]Secret exists:[/dim] {secret.name} in namespace {secret.namespace}"
                        )
            console.print()

            # Show manifest details for each cluster
            for result in results:
                if result.manifest_results and (
                    verbose or result.status == ReconcileStatus.FAILED
                ):
                    # Create manifest details table
                    manifest_table = Table(
                        show_header=True,
                        header_style="bold cyan",
                        title=f"{result.cluster_name} - Manifest Details",
                        border_style="cyan"
                        if result.status == ReconcileStatus.SUCCESS
                        else "red",
                    )
                    manifest_table.add_column("Kind", style="white", width=20)
                    manifest_table.add_column("Name", style="cyan", width=25)
                    manifest_table.add_column("Action", style="yellow", width=12)
                    manifest_table.add_column("Status", style="white", width=8)

                    for manifest_result in result.manifest_results:
                        # Determine status symbol
                        if manifest_result.action == "failed":
                            status_symbol = Text("✗", style="red bold")
                        elif manifest_result.action == "would apply":
                            status_symbol = Text("○", style="yellow")
                        else:
                            status_symbol = Text("✓", style="green bold")

                        manifest_table.add_row(
                            manifest_result.kind,
                            manifest_result.name,
                            manifest_result.action,
                            status_symbol,
                        )

                        # Show error details if present and verbose
                        if manifest_result.error and verbose:
                            error_msg = str(manifest_result.error)
                            # Split long error messages into multiple rows
                            max_width = 80
                            if len(error_msg) > max_width:
                                # Split by newlines first, then by width
                                lines = error_msg.split("\n")
                                for line in lines[:10]:  # Show first 10 lines
                                    if len(line) > max_width:
                                        # Wrap long lines
                                        for i in range(0, len(line), max_width):
                                            chunk = line[i : i + max_width]
                                            manifest_table.add_row(
                                                "", Text(chunk, style="red dim"), "", ""
                                            )
                                    else:
                                        manifest_table.add_row(
                                            "", Text(line, style="red dim"), "", ""
                                        )
                            else:
                                manifest_table.add_row(
                                    "",
                                    Text(f"Error: {error_msg}", style="red dim"),
                                    "",
                                    "",
                                )

                    console.print(manifest_table)
                    console.print()

            # Summary panel
            summary_text = Text()
            summary_text.append(f"Success: {success_count}", style="green bold")
            summary_text.append(" | ")
            summary_text.append(
                f"Failed: {failed_count}",
                style="red bold" if failed_count > 0 else "dim",
            )
            summary_text.append(" | ")
            summary_text.append(
                f"Skipped: {skipped_count}",
                style="yellow" if skipped_count > 0 else "dim",
            )

            panel_style = "green" if failed_count == 0 else "red"
            console.print(
                Panel(summary_text, title="Summary", border_style=panel_style)
            )

            sys.exit(0 if failed_count == 0 else 1)

        except Exception as e:
            console.print(f"[red bold]Reconciliation failed:[/red bold] {str(e)}")
            if verbose:
                console.print_exception()
            sys.exit(1)

    def get_org(self, verbose: bool = False) -> None:
        """Get organization details from the control plane.

        Args:
            verbose: Show detailed output

        Examples:
            python main.py get-org
            python main.py get-org --verbose
        """
        try:
            from services.api_service import APIService
            from rich.console import Console
            from rich.table import Table
            import json

            api_service = APIService(config=self.config)
            org = api_service.get_org()

            if verbose:
                print(json.dumps(org, indent=2))
            else:
                # Create a rich table
                console = Console()
                table = Table(
                    show_header=True,
                    header_style="bold magenta",
                    title="Organization Details",
                )

                table.add_column("Field", style="cyan", no_wrap=True)
                table.add_column("Value", style="green")

                # Add rows for all non-complex fields
                for key, value in org.items():
                    if not isinstance(value, (dict, list)):
                        # Format key to be more readable
                        display_key = key.replace("_", " ").title()
                        table.add_row(display_key, str(value))

                console.print(table)

            sys.exit(0)

        except Exception as e:
            print(f"Failed to get organization: {str(e)}", file=sys.stderr)
            if verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)

    def get_clusters(
        self, cluster_id: str | None = None, verbose: bool = False
    ) -> None:
        """Get ClickHouse clusters from the control plane.

        Args:
            cluster_id: Optional specific ClickHouse cluster ID to fetch
            verbose: Show detailed output with full JSON

        Examples:
            python main.py get-clusters
            python main.py get-clusters --cluster-id=abc123
            python main.py get-clusters --verbose
        """
        try:
            from services.api_service import APIService
            from rich.console import Console
            from rich.table import Table
            import json

            api_service = APIService(config=self.config)
            clusters = api_service.get_clusters(cluster_id=cluster_id)

            if not clusters:
                print("No ClickHouse clusters found")
                sys.exit(0)

            if verbose:
                # Show full JSON output
                print(json.dumps(clusters, indent=2))
            else:
                # Create a rich table
                console = Console()
                table = Table(show_header=True, header_style="bold magenta")

                # Add columns
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Name", style="green")
                table.add_column("Type", style="yellow")
                table.add_column("Status", style="blue")

                # Add optional columns based on what's in the data
                has_created = any("created_at" in c or "created" in c for c in clusters)
                if has_created:
                    table.add_column("Created", style="dim")

                # Add rows
                for cluster in clusters:
                    row = [
                        cluster.get("id", "N/A"),
                        cluster.get("name", "N/A"),
                        cluster.get("cluster_type_display", "N/A"),
                        cluster.get("status", "N/A"),
                    ]

                    if has_created:
                        created = cluster.get("created_at") or cluster.get(
                            "created", "N/A"
                        )
                        row.append(str(created))

                    table.add_row(*row)

                console.print(table)
                print(f"\nTotal: {len(clusters)} cluster(s)")

            sys.exit(0)

        except Exception as e:
            print(f"Failed to get clusters: {str(e)}", file=sys.stderr)
            if verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)

    def render(self, cluster_id: str | None = None, verbose: bool = False) -> None:
        """Render ClickHouse cluster manifests without applying to Kubernetes.

        Useful for debugging templates during development. Outputs K8s manifests
        (CHI/CHK CRDs, namespaces, etc.) to stdout.

        Args:
            cluster_id: Optional specific ClickHouse cluster ID to render
            verbose: Show detailed output

        Examples:
            python main.py render
            python main.py render --cluster-id=abc123
            python main.py render --verbose
        """
        try:
            from services.api_service import APIService
            from services.template_service import TemplateService
            from services.k8s_service import K8sService, K8sServiceError
            from services.credentials import ClusterCredentials
            from constants import TYPE_SINGLE_NODE, TYPE_CLUSTER

            # Fetch data from API
            api_service = APIService(config=self.config)
            template_service = TemplateService()

            if verbose:
                print("# Fetching organization data...", file=sys.stderr)

            org = api_service.get_org()
            state = api_service.get_install_state()

            # Extract configuration
            karpenter = state.get("sandbox", {}).get("outputs", {}).get("karpenter", {})
            public_domain_name = (
                state.get("sandbox", {})
                .get("outputs", {})
                .get("nuon_dns", {})
                .get("public_domain", {})
                .get("name", "")
            )
            components = state.get("components", {})
            keeper = components.get("img_clickhouse_keeper", {}).get("outputs", {})
            server = components.get("img_clickhouse_server", {}).get("outputs", {})
            certificate_arn = (
                components.get("certificate", {}).get("outputs", {}).get("arn", "")
            )

            # Extract and validate region
            region = state.get("install_stack", {}).get("outputs", {}).get("region")
            if not region:
                print(
                    "ERROR: Region not found in install_stack.outputs.region",
                    file=sys.stderr,
                )
                print(
                    "Cannot proceed with template rendering without a valid AWS region.",
                    file=sys.stderr,
                )
                sys.exit(1)

            if verbose:
                print("# Fetching clusters...", file=sys.stderr)

            clusters = api_service.get_clusters(cluster_id=cluster_id)

            if not clusters:
                print("# No ClickHouse clusters found", file=sys.stderr)
                sys.exit(0)

            # Initialize k8s service to check for existing secrets
            try:
                k8s_service = K8sService(in_cluster=self.config.in_cluster)
                k8s_available = True
            except Exception as e:
                if verbose:
                    print(
                        f"# K8s not available (will use placeholders for all secrets): {e}",
                        file=sys.stderr,
                    )
                k8s_available = False

            # Render each cluster
            for idx, cluster in enumerate(clusters):
                cluster_name = cluster.get("name", "unknown")
                cluster_slug = cluster.get("slug", cluster_name)
                cluster_type = cluster.get("cluster_type", "")

                if idx > 0:
                    print()  # Blank line between clusters

                print("---")
                print(f"# Cluster: {cluster_name} ({cluster_type})")
                print("---")

                # Determine if we need credentials
                needs_credentials = cluster_type in (TYPE_SINGLE_NODE, TYPE_CLUSTER)
                credentials = None
                secret_exists = False

                if needs_credentials:
                    # Check if secret exists in k8s (using slug as namespace, matching templates)
                    if k8s_available:
                        try:
                            secret = k8s_service.get_resource(
                                kind="Secret",
                                name="clickhouse-cluster-pw",
                                namespace=cluster_slug,
                                api_version="v1",
                            )
                            secret_exists = secret is not None
                        except K8sServiceError:
                            secret_exists = False

                    if secret_exists:
                        if verbose:
                            print(
                                f"# Secret already exists in cluster, would be skipped during reconcile",
                                file=sys.stderr,
                            )
                        # Don't generate credentials, will skip secret in manifests
                    else:
                        # Use placeholder credentials
                        credentials = ClusterCredentials(
                            username="PLACEHOLDER_USERNAME",
                            password="PLACEHOLDER_PASSWORD_24CH",
                        )
                        if verbose:
                            print(
                                f"# Using placeholder credentials (secret would be generated with random values)",
                                file=sys.stderr,
                            )

                # Render manifests
                manifests = template_service.render_cluster_manifests(
                    cluster=cluster,
                    org=org,
                    karpenter=karpenter,
                    keeper=keeper,
                    server=server,
                    public_domain_name=public_domain_name,
                    certificate_arn=certificate_arn,
                    region=region,
                    credentials=credentials if not secret_exists else None,
                )

                # Print manifests
                for manifest_idx, manifest in enumerate(manifests):
                    if manifest_idx > 0:
                        print("---")
                    print(manifest.rstrip())

            if verbose:
                print(f"\n# Rendered {len(clusters)} cluster(s)", file=sys.stderr)

            sys.exit(0)

        except Exception as e:
            print(f"Failed to render manifests: {str(e)}", file=sys.stderr)
            if verbose:
                import traceback

                traceback.print_exc()
            sys.exit(1)

    def version(self) -> None:
        """Show version information.

        Examples:
            python main.py version
        """
        print("ACME ClickHouse Data Plane Agent v0.1.0")
        sys.exit(0)

    def config_info(self) -> None:
        """Show current configuration (redacted).

        Examples:
            python main.py config-info
        """
        import json

        config_data = {
            "api_url": self.config.api_url,
            "org_id": self.config.org_id,
            "api_token": "***" + self.config.api_token[-4:]
            if len(self.config.api_token) > 4
            else "***",
        }
        print(json.dumps(config_data, indent=2))
        sys.exit(0)

    def debug_state(self) -> None:
        """Debug command to inspect install state structure.

        Examples:
            python main.py debug-state
        """
        import json
        from services.api_service import APIService

        try:
            api_service = APIService(config=self.config)
            state = api_service.get_install_state()

            print("=== Full Install State ===")
            print(json.dumps(state, indent=2))

            print("\n=== Karpenter Path: sandbox.outputs.karpenter ===")
            karpenter = state.get("sandbox", {}).get("outputs", {}).get("karpenter", {})
            print(json.dumps(karpenter, indent=2))

            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            sys.exit(1)


def main():
    """CLI entry point."""
    fire.Fire(DataPlaneAgent)


if __name__ == "__main__":
    main()
