# V2-005 / V2-006 — GMUD 24h and evidence-based dashboard audit

## Baseline before changes

2026-11-09: authenticated Grafana inventory contains 37 dashboards and 461 panels (41 text/row panels, 420 query panels). Prometheus, Loki, Tempo and Alertmanager proxy health passed. Grafana 3/3, Prometheus 2/2, Tempo 1/1, Collector 1/1; two Ready EKS nodes in 1b. Repositories reviewed: infrastructure, observability, GitOps, Orders API, Orders Worker and automation.

All three recovered EBS volumes are encrypted, attached in 1b and have completed post-recovery snapshots from 2026-11-09 16:06 UTC. This proves point-in-time protection, not periodic backup selection; original Terraform selection still follows the old five claims. No volume, PV/PVC, node group, Power Manager or DR configuration is changed by this activity.

## V2-005 semantics and source boundary

Dashboard UID `cosmotech-gmud-24h`, title `CosmoTech | GMUD — Últimas 24 Horas`. The existing `orders-worker-canary` dashboard is retained. It measures version/Canary behavior and is not a duplicate of a GMUD event overview.

The minimal observer on the existing ITSM host reads native GLPI Changes with existing authentication and verifies signed envelopes with the installed trusted decoder. It never instantiates authority Runtime/ChangeJournal constructors, writes authority journals, starts Kestra executions, approves changes or dispatches deployments. Existing signed records contain immutable GMUD, Kestra execution, GitHub run and Argo application/revision correlation. Real deployment completion requires an `observing` transition with `technical_validation=true`; pipeline success is not accepted as deployment proof. GMUD closure after the observation period remains distinct.

Metrics are gauges computed directly from original UTC event timestamps in `(now-86400, now]`, not `increase()` over a newly deployed counter. Duplicate record deliveries and phase retries do not increment counts. Conflicting duplicate changes fail collection. Synthetic records are excluded. Two native GLPI protocol/test changes outside the signed release flow are separately counted as unmanaged; this dashboard covers governed release GMUDs, not every arbitrary GLPI Change.

The live baseline has 15 native Changes, 13 signed governed GMUDs and zero creations/events in the last 24h. These are source observations, never fixtures published to telemetry. Controlled offline tests cover empty, pending, auto/manual approval, rejection, failed deploy, verified rollback, duplicate retries, stale/future records and unverified completion.

A successful empty window exports actual zero counters. Collection failure exports `collection_success=0` and omits business gauges. Dashboard freshness gates prevent cached values older than 180s from looking healthy. Means and success rates with zero denominators are N/A, not fabricated zeros or 100%. Current pending counts only changes created in the 24h window; historical backlog is outside that KPI.

Prometheus supplies indicators, hourly buckets, correlated event timeline and detailed table. Existing Loki remains the application log source. The existing folder-scoped Grafana publisher cannot push Loki logs (403 verified with an empty, no-event request), so no permissions are broadened and no synthetic log events are generated. Detailed GMUD events are projected directly from their signed source using bounded Prometheus series.

Host files are versioned under `ops/monitoring/gmud/`; only the private Nginx 8088 server serves `/gmud-metrics`. A systemd oneshot/timer polls every minute with bounded runtime/memory. The existing ServiceMonitor gains one endpoint; no new AWS or EKS compute is required. Dashboard ConfigMap publication uses the existing Argo application with prune disabled.

Rollback: stop/disable only `cosmotech-gmud-observer.timer`, remove its private Nginx include, restore the saved server configuration and reload after `nginx -t`; remove the additional ServiceMonitor endpoint via source. Original dashboards, approval policies and authority databases are unchanged.

## V2-006 audit method

The authenticated audit records dashboard UID, folder, panel ID, datasource, original and interpolated query, variable options, time interval, HTTP status, series/finite/nonzero sample counts and cause. All target queries, including hidden ones, are included. Real 24h range requests use a bounded one-hour step and an eight-second Prometheus evaluation timeout to avoid unbounded recovery load. No result is converted from empty to zero.

Zero requires returned finite zero samples, or separate proof that an event/sample count is zero. Empty series are not automatically legitimate absence. Rows/text are tracked separately and excluded from real-data totals. Missing MacOS/etcd/mesh exporters are telemetry/dependency findings, not invitations to install infrastructure or delete panels. Current selected variables and historical range observations must be distinguished; an empty first namespace is not proof that a query is broken.

Raw inventory, query results and authenticated captures are private working artifacts under `/tmp/v2-005-006/`. Sanitized per-panel results and operational evidence are published under `docs/evidence/` after final validation. Credentials, session cookies, raw signed envelopes and private IPs are excluded from Git artifacts.
