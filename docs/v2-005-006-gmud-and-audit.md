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

## Proven corrections prepared after query evidence

1. Grafana Overview, UID `6be0s85Mk`, panel 6: `grafana_alerting_result_total` is absent on the restored Grafana 13.3. Actual `grafana_alerting_alerts{state="alerting"}` is exposed and returns a real zero gauge. The override preserves existing filters and changes only the proven obsolete metric.
2. Canary, UID `orders-worker-canary`, panel 5: `cosmotech_worker_inflight or cosmotech_worker_draining` coalesces equal label sets and masks the draining series. Two independent targets preserve both real gauges. No Worker instrumentation or deployment changes.
3. Observability tools, UID `observability-tools-lab`, explanatory panel: the old 24h Prometheus retention statement is inconsistent with the restored 30d/8GB configuration. Text is corrected; histories and retention settings are not changed.

No standard dashboard is deleted. Empty namespace selections, EKS-managed unavailable component metrics, absent macOS exporters, idle Worker quantiles and expired quota observations remain explicit findings. Existing valid queries are not changed to force values. A full last-24h range was queried with a bounded one-hour evaluation step; short bursts between samples may not be visible in this audit. Raw-query and per-target evidence remains private.

## Operational interruption — 2026-11-09

Observability PR #7 merged as `8d0dc0b186e8ce963f227f7ee3cc7fc273b311d9`, after CI run `42654492901` passed. The observer install command `be62d75e-3717-483c-9c42-f666cde27319` was submitted before interruption; its terminal result is **unconfirmed**. Do not replay installation blindly. First inspect the SSM result, installed file hashes, systemd status and `/gmud-metrics` after access returns.

On resumption, AWS API returned invalid credentials, the existing login profile failed renewal, and both EKS and Grafana timed out. An explicitly authorized `aws login --profile serverless-lab --remote` then reached a sign-in page reporting **account suspended**. The login command was cancelled. Billing/nonpayment is only one possibility mentioned by the page; the suspension cause has not been established. No restriction workaround, billing action or repeated login attempt was performed.

V2-005 and V2-006 are **not operationally accepted**. The previous healthy baseline is dated evidence, not a claim of present service health. GitOps changes are prepared in a draft PR and must not be merged while automatic sync and operational validation cannot be verified. Repositories contain complete reviewable sources and passing offline tests, but offline fixtures do not prove an operational dashboard or an operational data collector.

## Resume after AWS reactivation

1. Confirm account access and live services without changing nodes/storage/Power Manager/DR.
2. Read the existing installation command result before deciding whether any repair is needed. Verify native GLPI counts and timestamps again; do not reuse the baseline zero as current truth.
3. Validate observer collection success, HTTP private endpoint and Prometheus scrape. Add only the reviewed ServiceMonitor endpoint.
4. Merge the reviewed GitOps PR after CI passes and the operational prerequisites are verified. Check Argo `Synced/Healthy`, actual ConfigMap adoption and dashboard UID count (37 original plus one GMUD overview).
5. Re-run the authenticated full per-panel audit and compare classifications, keeping data gaps explicit. Check all datasources, authenticated HTTPS login, source event counts, Zabbix events, and regression health. Capture actual updated dashboards; no screenshot mockups.
6. Replace the interruption status with final operational evidence only after these checks pass. Periodic backup coverage for the new recovery claims is an existing separate dependency; this task never changes volumes or backup selections.

## Audit counts at the dated baseline (not final operational acceptance)

37 dashboards, 461 panels: 420 query panels and 41 structural/text panels. After correlating query results with source/version evidence, query-panel classifications are 253 OK with nonzero real samples, 39 ZERO LEGÍTIMO with real zero samples, 113 SEM TELEMETRIA, 13 BLOQUEADO (managed etcd endpoint absent), and 2 ERRO with proven corrections prepared. Structural panels add 40 OK and one erroneous retention statement. Total including structural panels: 293 OK, 39 ZERO LEGÍTIMO, 113 SEM TELEMETRIA, 13 BLOQUEADO, 3 ERRO.

These classifications deliberately leave uncertain absences unresolved. They are not 113 confirmed broken dashboards. Idle/undefined quantiles, empty namespace selections, stale quota sources and unavailable exporter families need separate interpretation. None of the prepared corrections is counted as operationally validated while access is suspended. The complete per-panel table is in `docs/evidence/v2-005-006/panel-baseline.json`; variable resolution and the audit summary are adjacent.

## Historical reconciliation and timestamp validation

The sanitized real GLPI fixture is used **only offline**, with its original historical timestamps. At 2026-11-06 17:54:11 UTC it reconciles 13 created GMUDs, five automatic/eight manual approvals, 13 deployment starts, ten validated deployments and three verified rollbacks: 52 distinct events. Re-evaluating the same records at the dated 2026-11-09 baseline returns no events in the last 24h. Controlled pending/rejection/failure cases remain isolated tests, not real metrics.

The hourly rolling projection includes the two partial UTC boundary hours (up to 25 buckets for a rolling 24h period). Timeline seconds are explicitly converted to milliseconds for Grafana date formatting. Failure tests verify old zero-valued business metrics are removed when source collection fails, and error messages cannot leak credential content.

GitOps publication is staged in `rlcosmo/cosmotech-gitops` PR #25 (draft). Its CI passed. The draft is deliberately unmerged because main automatically syncs to Argo and the AWS account suspension prevents safe operational validation. Real baseline capture is available in that PR's `docs/evidence/v2-005-006/baseline-canary.png`; no capture of the unpublished GMUD dashboard is claimed.
