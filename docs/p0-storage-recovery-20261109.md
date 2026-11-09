# P0 storage recovery — 2026-11-09

All legacy recovery volumes are in us-east-1a, not 1b. All original claims and EBS volumes remain intact. No original PV/PVC is deleted or rebound.

Grafana source: completed AWS Backup snapshot snap-01ff125356e3db5e6, 2026-11-09 05:21:53 UTC, from vol-0d46fc5d30780ca02. Additional original backup snap-06ac6d5a0aebe4fc7 completed before cutover. Source is detached with no writers. Encrypted recovery copy vol-0426070ae45055fce is in 1b, bound exclusively to observability/grafana-p0-1b, Retain.

Read-only SQLite integrity check returned ok, three users, four datasources, 728 migration records. Isolated boot using unchanged Grafana 13.3.0 reached 3/3 Ready. Authenticated API returned 200, 37 provisioned dashboards including V2 SQS/Workers, and four datasources. This does not yet validate datasource connectivity.

Recovery manifests are additive. Apply grafana-storage.json, then stop the isolated validation deployment and wait for termination before patching the main deployment with grafana-deployment-patch.json. Never run two SQLite writers. Helm overlay grafana-1b.json reproduces the change with the pinned chart and existing release values. No workload storage is owned by the current Argo project (only dashboard ConfigMap and PrometheusRule); do not expand its permissions implicitly.

Rollback: stop the recovery writer, restore the saved deployment template to grafana-data. Original data is untouched, but that rollback needs a Ready node in 1a. Do not roll back to emptyDir. New writes on the recovery volume are not automatically merged back. Preserve snapshots and clones; no automatic cleanup. New volumes and snapshots incur storage costs.
