# User Flow

## Overview

1. Users can create an account and an org.
2. When an org is created, we create an installation for the org on nuon and poll for the CF Installation link. As part
   of this process, we create a django user for the org and create a token for it.
3. When the installation is ready, the data plane starts up and reports to the control plane. At this point, the user
   can begin creating Clickhouse resources.

## Sign Up

## Creating an org

This is done by default. No teams or anything.

## Creating Clusters

When a user creates a clickhouse resource, we create a job the data plane can read. The data plane polls for these and
manages the install.

The org dashboard includes facts about the cluster and the installs which we fetch using from the cluster with Nuon
using nuon actions. We surface certain facts, such as the connection urls (or ch-ui) etc.
