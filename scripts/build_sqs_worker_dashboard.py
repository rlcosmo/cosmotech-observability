"""Render SQS/Workers dashboard and alert manifests for the existing stack."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERCENTILES = (0.50, 0.95, 0.99)


def quantile(value):
    return f"histogram_quantile({value}, sum by (le,channel) (rate(cosmotech_worker_processing_seconds_bucket[5m])))"


def write(path, value):
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


panels = []
for title, expression, unit in [
    ("Backlog", "cosmotech_sqs_visible", "short"),
    ("Mensagens in-flight · SQS", "cosmotech_sqs_inflight", "short"),
    ("Idade da mensagem mais antiga", "cosmotech_sqs_oldest_age_seconds", "s"),
    ("DLQ", "cosmotech_sqs_dlq_visible", "short"),
    ("Throughput de processamento confirmado", 'sum by(channel)(rate(cosmotech_worker_messages_total{result="success"}[5m]))', "ops"),
    ("Taxa de entrada SQS · amostra de 60s", "cosmotech_sqs_sent_per_second", "ops"),
    ("Taxa de recebimento SQS · inclui reentregas", "cosmotech_sqs_received_per_second", "ops"),
    ("Retries", "sum by(channel)(rate(cosmotech_worker_retries_total[5m]))", "ops"),
    ("Falhas de processamento e ACK", 'sum by(channel,result)(rate(cosmotech_worker_messages_total{result=~"error|ack_error"}[5m]))', "ops"),
    *[(f"Processamento P{int(q*100)}", quantile(q), "s") for q in PERCENTILES],
    ("Idade da última amostra SQS", "time() - cosmotech_sqs_data_timestamp_seconds", "s"),
    ("Coleta SQS válida", 'lab_collection_success{group="sqs"}', "short"),
    ("Contadores SQS disponíveis", "cosmotech_sqs_counter_available", "short"),
    ("Workloads scrapeáveis", 'up{namespace="orders-worker"}', "short"),
]:
    index = len(panels)
    panels.append({"id": index + 1, "type": "timeseries", "title": title,
                   "gridPos": {"x": (index % 2) * 12, "y": (index // 2) * 8, "w": 12, "h": 8},
                   "datasource": {"type": "prometheus", "uid": "${datasource}"},
                   "targets": [{"refId": "A", "expr": expression, "legendFormat": "{{channel}} {{result}} {{metric}}"}],
                   "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
                   "options": {"legend": {"displayMode": "list"}},
                   "description": "Sem amostras significa desconhecido; não substituir por zero. Percentis medem processamento, não latência ponta a ponta."})

dashboard = {"uid": "cosmotech-v2-sqs-workers", "title": "CosmoTech · V2 SQS e Workers",
             "schemaVersion": 39, "version": 1, "tags": ["cosmotech", "v2", "sqs"],
             "refresh": "30s", "time": {"from": "now-6h", "to": "now"},
             "templating": {"list": [{"name": "datasource", "type": "datasource", "query": "prometheus"}]},
             "panels": panels}
write("ops/grafana/dashboards/v2-sqs-workers.json", dashboard)
write("ops/kubernetes/v2-sqs-dashboard.json", {
    "apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "cosmotech-v2-sqs-workers", "namespace": "observability", "labels": {"grafana_dashboard": "1"}},
    "data": {"v2-sqs-workers.json": json.dumps(dashboard, ensure_ascii=False)}})

fresh = " and on() (time() - cosmotech_sqs_data_timestamp_seconds < 180)"
alerts = []
for name, expression, duration, severity, summary in [
    ("CosmoTechSQSEvidenceUnavailable", 'max(lab_collection_success{group="sqs"} == 0 or absent(lab_collection_success{group="sqs"}) or time() - cosmotech_sqs_data_timestamp_seconds > 180 or absent(cosmotech_sqs_data_timestamp_seconds))', "5m", "warning", "Coleta SQS ausente, falhou ou está desatualizada"),
    ("CosmoTechSQSBacklog", "cosmotech_sqs_visible > 100" + fresh, "10m", "warning", "Backlog SQS acima de 100 mensagens"),
    ("CosmoTechSQSOldMessages", "cosmotech_sqs_oldest_age_seconds > 180" + fresh, "5m", "warning", "Mensagem mais antiga excede 180 segundos"),
    ("CosmoTechSQSDLQ", "cosmotech_sqs_dlq_visible > 0" + fresh, "2m", "critical", "DLQ contém mensagens; preservar dados e investigar"),
    ("CosmoTechWorkerFailures", 'sum(increase(cosmotech_worker_messages_total{result=~"error|ack_error"}[5m])) > 0', "2m", "warning", "Worker apresentou falhas de processamento ou ACK"),
    ("CosmoTechWorkerRetries", "sum(increase(cosmotech_worker_retries_total[5m])) > 10", "5m", "warning", "Worker apresentou mais de dez retries em cinco minutos"),
    ("CosmoTechWorkerSlow", "(" + quantile(0.95) + " > 30) and on(channel) (sum by(channel)(increase(cosmotech_worker_processing_seconds_count[5m])) >= 20)", "5m", "warning", "P95 de processamento acima de 30s, com amostragem mínima"),
    ("CosmoTechWorkerScrapeUnavailable", 'max(up{namespace="orders-worker"}) == 0 or absent(up{namespace="orders-worker"})', "5m", "critical", "Métricas dos Workers indisponíveis"),
]:
    alerts.append({"alert": name, "expr": expression, "for": duration,
                   "labels": {"severity": severity, "team": "cosmotech"},
                   "annotations": {"summary": summary,
                                   "runbook_url": "https://github.com/rlcosmo/cosmotech-observability/blob/main/docs/lab-v2-sqs-workers.md"}})
groups = [{"name": "cosmotech.v2.sqs-workers", "rules": alerts}]
write("ops/monitoring/v2-sqs-worker-rules.json", {"groups": groups})
write("ops/kubernetes/v2-sqs-worker-alerts.json", {
    "apiVersion": "monitoring.coreos.com/v1", "kind": "PrometheusRule",
    "metadata": {"name": "cosmotech-v2-sqs-workers", "namespace": "observability", "labels": {"release": "prometheus"}},
    "spec": {"groups": groups}})

# Readiness only: these series must be supplied by verified recovery probes.
# Do not invent uptime/RTO/RPO for a region that has not been provisioned.
dr_panels = []
for title, expr, unit in [
    ("Disponibilidade ponta a ponta por região", 'max by(region)(probe_success{job="orders-dr-e2e"})', "percentunit"),
    ("RTO observado · última recuperação validada", "cosmotech_dr_rto_seconds", "s"),
    ("RPO observado · último aceite durável", "cosmotech_dr_rpo_seconds", "s"),
    ("Indisponibilidade em andamento", 'clamp_min(time() - cosmotech_dr_outage_started_timestamp_seconds, 0) and on(region) (max by(region)(probe_success{job="orders-dr-e2e"}) == 0)', "s"),
]:
    index = len(dr_panels)
    dr_panels.append({"id": index + 1, "type": "timeseries", "title": title,
                      "description": "Preparação: sem probe/exportador validado, estado desconhecido. Não comprova recuperação real.",
                      "gridPos": {"x": (index % 2) * 12, "y": (index // 2) * 8, "w": 12, "h": 8},
                      "datasource": {"type": "prometheus", "uid": "${datasource}"},
                      "targets": [{"refId": "A", "expr": expr, "legendFormat": "{{region}}"}],
                      "fieldConfig": {"defaults": {"unit": unit}, "overrides": []}})
write("ops/grafana/dashboards/v2-dr-readiness.json", {
    "uid": "cosmotech-v2-dr-readiness", "title": "CosmoTech · V2 DR · Preparação",
    "schemaVersion": 39, "version": 1, "tags": ["cosmotech", "v2", "dr", "preparacao"],
    "refresh": "15s", "time": {"from": "now-6h", "to": "now"},
    "templating": {"list": [{"name": "datasource", "type": "datasource", "query": "prometheus"}]},
    "panels": dr_panels})
