# Nuon Configs for the Data Plane

The data plan is a kubernetes cluster where a tenant's clickhouse clusters are deployed.

### Cloudformation Template

Uses a non-main version of the CF install stack template that includes the RDS Subnet. This makes deployments slightly
faster, but the real motivation is that this component does not really change so we're moving it into the stack
alongside other "fixed" infra resources.

### Sandbox

This deployment uses the EKS Auto Mode template as an exercise.

### Components

- clickhouse operator
- tailscale operator
- datadog operator

- data-plane API
