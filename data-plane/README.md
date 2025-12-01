# A.C.M.E ClickHouse: Data Plane

This data-plane runs on the k8s cluster. It is responsible for managing the clusters as defined in the control plane.

For the sake of this demo, it's a simple python process that runs on schedule.

1. Check Control Plan
2. Check remote state against local state
3. apply changes to cluster.
   - create
   - update
   - delete

The resource this is concerned with is a pre-determined config from the templates directory.

| Type | Description           |
| ---- | --------------------- |
| CHI  | single node cluster   |
| CHK  | 3-node keeper cluster |

<!-- | CHK + CHI | multi-node CHI cluster w/ keeper for replication | -->

These are actually just jinja templates which are populated w/ the facts from the control plane and then applied on the
cluster.

## Facts

The agent hits the api and gets a couple of things.

1. org
2. org/state
3. the list of clusters for a given org/state

From the org/state which corresponds to the nuon install state, the agent pulls the karpenter outputs.

the state passed to the templates is then:

```json
{
  "org": "<org>",
  "karpenter": "<state.sandbox.outputs.karpenter>",
  "cluster": "cluster[i]",
  "keeper": "<state.img_clickhouse_keeper.outputs>",
  "server": "<state.img_clickhouse_server.outputs>"
}
```

These are used by the agent in to check the status of a given cluster and create/update/delete as necessary.

## Permissions

The pod this data-plane component runs on needs to be able to:

1. CRUD `Namespace`s
2. CRUD `CHI`
3. CRUD `CHK`
4. CRUD `Ingress`es

## Operation

This "agent" is just a CLI. It should essentially the following command on a cron (1m):

```bash
python agent.py reconcile --type all
```

## Config

The environment should include the following

1. ACME_CH_API_URL
2. ACME_CH_API_TOKEN
3. ACME_CH_ORG_ID

With these facts, the agent can construct the necessary request to carry out its work.
