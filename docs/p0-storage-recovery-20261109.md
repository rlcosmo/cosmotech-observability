# P0 storage recovery — 2026-11-09

All legacy recovery volumes are in us-east-1a, not 1b. All original claims and EBS volumes remain intact. No original PV/PVC is deleted or rebound.

Grafana source: completed AWS Backup snapshot snap-01ff125356e3db5e6, 2026-11-09 05:21:53 UTC, from vol-0d46fc5d30780ca02. Additional original backup snap-06ac6d5a0aebe4fc7 completed before cutover. Source is detached with no writers. Encrypted recovery copy vol-0426070ae45055fce is in 1b, bound exclusively to observability/grafana-p0-1b, Retain.

Read-only SQLite integrity check returned ok, three users, four datasources, 728 migration records. Isolated boot using unchanged Grafana 13.3.0 reached 3/3 Ready. Authenticated API returned 200, 37 provisioned dashboards including V2 SQS/Workers, and four datasources. This does not yet validate datasource connectivity.

Recovery manifests are additive. Apply grafana-storage.json, then stop the isolated validation deployment and wait for termination before patching the main deployment with grafana-deployment-patch.json. Never run two SQLite writers. Helm overlay grafana-1b.json reproduces the change with the pinned chart and existing release values. No workload storage is owned by the current Argo project (only dashboard ConfigMap and PrometheusRule); do not expand its permissions implicitly.

Rollback: stop the recovery writer, restore the saved deployment template to grafana-data. Original data is untouched, but that rollback needs a Ready node in 1a. Do not roll back to emptyDir. New writes on the recovery volume are not automatically merged back. Preserve snapshots and clones; no automatic cleanup. New volumes and snapshots incur storage costs.

## Prometheus and Tempo validation

Prometheus uses a new encrypted 1b copy of completed pre-cutover snapshot snap-053d0bc34a20a98c5 from the detached original vol-02c4cccd0b6088ca3. Isolated Prometheus v3.15.1 completed WAL replay, reported healthy blocks and Ready, and count(max_over_time(up[7d])) returned 67. Observed memory after replay was 358 MiB; use 350Mi request and 1Gi limit, with 16Mi/128Mi for configuration reloaders. Requests are scheduling reservations, not memory caps; monitor actual consumption and OOM status. The cluster has limited scheduling headroom.

The Prometheus override deliberately replaces the main container's /prometheus mount by strategic merge with recovered-data. StorageSpec removes the original volumeClaimTemplate and uses an unused emptyDir; the TSDB must never mount that emptyDir. Inspect generated StatefulSet and actual pod before accepting recovery. Old PVC retention stays Retain. The operator can recreate its StatefulSet when its immutable claim template changes; do not delete PVCs.

Tempo prioritizes completed quiesced snapshot snap-0da8501e7373d8447, 2026-11-04 10:29:07 UTC, on a new encrypted 1b volume. Isolated Tempo 3.1.1 became Ready, search returned historical traces, and trace 12764de176cd2b744c5d1c067e45dab1 was retrieved via /api/v2/traces. This recovery point is older than the current original volume: traces after that point are not in this serving copy. Original volume and additional backup snap-0744219066f50fc51 remain preserved for reconciliation; do not claim zero RPO or complete historical consolidation.

Temporary retention is 30d/8GB for metrics and 720h for traces to avoid deleting restored old data at startup. Capacity must be monitored; reverting retention requires a separate review because it expires history. Stop isolated readers/writers before cutover. Tempo's chart has no existingClaim support: persistence.enabled=false suppresses claim templates, while explicit extraVolumes and extraVolumeMounts supply the durable restored PVC. It does NOT mean ephemeral trace storage. Changing the immutable StatefulSet requires orphaning only the controller, terminating its Pending pod, and recreating the controller from the pinned chart. Original PVC/PV remain untouched, and captured controller manifests permit rollback when 1a compute returns.
