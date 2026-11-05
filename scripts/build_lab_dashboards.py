"""Build the two Grafana dashboards; credentials and live values never enter JSON."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASOURCE = {"type": "prometheus", "uid": "prometheus"}
TOOLS = {
    "Zabbix": "https://zabbix.cosmotechsolutions.com.br/",
    "Grafana": "https://grafana.cosmotechsolutions.com.br/",
    "Prometheus": "https://prometheus-aws-eks-istio-lab-dev.cosmotechsolutions.com.br/",
    "Alertmanager": "https://alertmanager.cosmotechsolutions.com.br/",
    "Tempo": "https://tempo.cosmotechsolutions.com.br/ready",
    "Argo CD": "https://argocd.cosmotechsolutions.com.br/",
    "GLPI": "https://glpi.cosmotechsolutions.com.br/",
    "Kestra": "https://kestra.cosmotechsolutions.com.br/ui/",
}


def dashboard(uid, title, description):
    return {"uid": uid, "title": title, "description": description, "schemaVersion": 39,
            "version": 0, "tags": ["cosmotech", "laboratorio"], "timezone": "browser",
            "time": {"from": "now-24h", "to": "now"}, "refresh": "1m", "editable": True,
            "panels": [], "links": [{"type": "link", "title": "AWS e custos", "url": "/d/aws-account-costs-lab"},
                                     {"type": "link", "title": "Observabilidade", "url": "/d/observability-tools-lab"}]}


def text(dash, title, content, x, y, w=24, h=3):
    dash["panels"].append({"id": len(dash["panels"]) + 1, "type": "text", "title": title,
                           "gridPos": {"x": x, "y": y, "w": w, "h": h}, "options": {"mode": "markdown", "content": content}})


def panel(dash, title, expr, x, y, w=6, h=4, kind="stat", unit="short", legend="", status=False, description="", url=None):
    field = {"unit": unit, "decimals": 2, "color": {"mode": "palette-classic"}}
    options = {"legend": {"displayMode": "list", "placement": "bottom"}, "tooltip": {"mode": "multi"}}
    target = {"refId": "A", "expr": expr, "legendFormat": legend, "instant": kind != "timeseries", "range": kind == "timeseries", "format": "table" if kind == "table" else "time_series"}
    if status:
        field.update({"decimals": 0, "min": 0, "max": 1, "mappings": [{"type": "value", "options": {"0": {"text": "FALHA", "color": "red", "index": 0}, "1": {"text": "OK", "color": "green", "index": 1}}}],
                      "thresholds": {"mode": "absolute", "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]}, "color": {"mode": "thresholds"}})
    if kind == "stat":
        options = {"reduceOptions": {"values": False, "calcs": ["lastNotNull"], "fields": ""}, "orientation": "auto", "textMode": "auto", "colorMode": "background_solid" if status else "value", "graphMode": "none", "justifyMode": "auto"}
    if kind == "bargauge":
        options = {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}, "orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True}
    if kind == "table":
        options = {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}}
    obj = {"id": len(dash["panels"]) + 1, "title": title, "type": kind, "description": description,
           "datasource": DATASOURCE, "gridPos": {"x": x, "y": y, "w": w, "h": h},
           "targets": [target], "fieldConfig": {"defaults": field, "overrides": []}, "options": options}
    if url:
        obj["links"] = [{"title": "Abrir ferramenta", "url": url, "targetBlank": True}]
    dash["panels"].append(obj)
    return obj


def table(dash, title, expr, columns, names, x, y, w=12, h=8):
    obj = panel(dash, title, expr, x, y, w, h, kind="table")
    obj["transformations"] = [
        {"id": "filterFieldsByName", "options": {"include": {"names": columns}}},
        {"id": "organize", "options": {"indexByName": {name: i for i, name in enumerate(columns)}, "renameByName": names}},
    ]
    return obj


def build():
    aws = dashboard("aws-account-costs-lab", "AWS | Recursos e custos", "Conta AWS: custos, créditos e inventário fora do EKS. Fontes: AWS APIs e Cost Explorer.")
    text(aws, "Visão da conta • AWS", "**414053644145 · us-east-1**  |  Infraestrutura fora do EKS + faturamento global da conta.\n\nCustos são estimados e podem ter atraso da AWS. **O total financeiro inclui EKS e recursos compartilhados**; inventário e servidores excluem nodes do EKS. Créditos abaixo são do **Free Tier**, não de outros programas promocionais.", 0, 0, h=4)
    for title, expr, x in [
        ("Gasto bruto do mês", "lab_aws_cost_mtd_gross_usd", 0),
        ("Créditos Free Tier restantes", "lab_aws_free_tier_credit_remaining_usd", 6),
        ("Créditos aplicados neste mês", "lab_aws_cost_mtd_credits_applied_usd", 12),
        ("Custo líquido do mês", "lab_aws_cost_mtd_net_usd", 18),
    ]:
        panel(aws, title, expr, x, 4, unit="currencyUSD", description="Valor informado pela AWS na última coleta bem-sucedida. Confira a idade e o estado da coleta abaixo.")
    panel(aws, "Coleta de custos", 'lab_collection_success{group="costs"}', 0, 8, w=4, h=3, status=True)
    panel(aws, "Idade dos custos", 'time() - lab_collection_last_success_timestamp_seconds{group="costs"}', 4, 8, w=4, h=3, unit="s")
    panel(aws, "Coleta de créditos", 'lab_collection_success{group="credits"}', 8, 8, w=4, h=3, status=True)
    panel(aws, "Idade dos créditos", 'time() - lab_collection_last_success_timestamp_seconds{group="credits"}', 12, 8, w=4, h=3, unit="s")
    panel(aws, "Servidores EC2 fora do EKS", 'sum(lab_aws_inventory_resources{aws_service="EC2 sem nodes EKS"})', 16, 8, w=4, h=3)
    panel(aws, "Alarmes AWS disparados", 'sum(lab_aws_cloudwatch_alarms{state="ALARM"})', 20, 8, w=4, h=3)
    panel(aws, "Gasto por serviço • sem linha EKS", 'sort_desc(lab_aws_cost_service_mtd_usd{aws_service!="Amazon Elastic Container Service for Kubernetes"} > 0)', 0, 11, w=14, h=9, kind="bargauge", unit="currencyUSD", legend="{{aws_service}}", description="EC2, EBS e rede podem incluir recursos compartilhados com EKS. A API por serviço não permite atribuir esses custos exclusivamente a cada workload.")
    panel(aws, "Gasto bruto por dia • conta completa", "lab_aws_cost_daily_usd", 14, 11, w=10, h=9, kind="bargauge", unit="currencyUSD", legend="{{date}}")
    table(aws, "Inventário de serviços AWS", "lab_aws_inventory_resources", ["aws_service", "Value"], {"aws_service": "Serviço", "Value": "Recursos"}, 0, 20, h=10)
    table(aws, "Recursos encontrados", "lab_aws_resource_info", ["aws_service", "resource"], {"aws_service": "Serviço", "resource": "Recurso"}, 12, 20, h=10)
    panel(aws, "Saúde dos servidores", "lab_aws_server_up", 0, 30, w=8, h=5, status=True, legend="{{server}}", description="OK = instância Running e verificações EC2 de sistema e instância em estado ok.")
    panel(aws, "CPU dos servidores • CloudWatch", "lab_aws_server_cpu_percent", 8, 30, w=16, h=7, kind="timeseries", unit="percent", legend="{{server}}")
    table(aws, "Leitura do inventário por API", "lab_aws_inventory_api_up", ["aws_service", "Value"], {"aws_service": "Serviço", "Value": "Leitura AWS (1=OK)"}, 0, 37, w=12, h=8)
    text(aws, "Fontes e atualização", "**Custos:** Cost Explorer, UnblendedCost, mês corrente, atualização a cada 6h.\n\n**Créditos:** Free Tier GetAccountPlanState, atualização a cada hora. Outros créditos: consulta de Billing indisponível para esta identidade.\n\n**Inventário:** us-east-1; S3 global. A cada 15min. Uma quantidade zero significa API consultada sem recursos; falha de permissão aparece separadamente.\n\n**Servidores:** EC2 status + CPU CloudWatch, a cada 5min. Nenhuma instância ou aplicação é modificada.\n\n[Billing e créditos](https://console.aws.amazon.com/billing/home#/credits) · [Cost Explorer](https://console.aws.amazon.com/costmanagement/home#/cost-explorer)", 12, 37, w=12, h=8)

    obs = dashboard("observability-tools-lab", "Observabilidade | Ferramentas e servidores", "Disponibilidade externa, links, latência e saúde da stack de observabilidade e servidores.")
    obs["links"] += [{"type": "link", "title": name, "url": url, "targetBlank": True} for name, url in TOOLS.items()]
    text(obs, "Central de observabilidade", "**Disponibilidade externa + saúde interna + servidores**\n\nOs cartões de ferramentas testam HTTPS, certificado e resposta esperada. **Kestra OK** significa que a API respondeu 401 e exige autenticação; não é uma execução de workflow. Use os links dos cartões ou a barra superior para abrir cada ferramenta.", 0, 0, h=4)
    panel(obs, "Ferramentas respondendo", "sum(lab_tool_up)", 0, 4, w=6)
    panel(obs, "Ferramentas com falha", "count(lab_tool_up == 0) or vector(0)", 6, 4, w=6)
    panel(obs, "Servidores saudáveis", "sum(lab_aws_server_up)", 12, 4, w=6)
    panel(obs, "Idade da verificação web", 'time() - lab_collection_last_success_timestamp_seconds{group="web"}', 18, 4, w=6, unit="s")
    for index, (name, url) in enumerate(TOOLS.items()):
        panel(obs, name, 'lab_tool_up{tool=' + json.dumps(name) + '}', (index % 4) * 6, 8 + (index // 4) * 4, w=6, h=4, status=True, url=url)
    panel(obs, "Coletor disponível", 'up{service="cosmotech-lab-monitoring"}', 0, 94, status=True)
    components = [
        ("Loki • logs", 'min(kube_statefulset_status_replicas_ready{namespace="loki",statefulset="loki"} / kube_statefulset_replicas{namespace="loki",statefulset="loki"})', "/explore?schemaVersion=1&panes=%7B%22a%22:%7B%22datasource%22:%22loki%22%7D%7D&orgId=1"),
        ("Tempo • traces", 'min(kube_statefulset_status_replicas_ready{namespace="observability",statefulset="tempo"} / kube_statefulset_replicas{namespace="observability",statefulset="tempo"})', TOOLS["Tempo"]),
        ("Alloy • coleta de logs", 'min(kube_daemonset_status_number_ready{namespace="observability",daemonset="alloy"} / kube_daemonset_status_desired_number_scheduled{namespace="observability",daemonset="alloy"})', TOOLS["Grafana"]),
        ("OpenTelemetry Collector", 'min(kube_deployment_status_replicas_available{namespace="observability",deployment="otel-collector-opentelemetry-collector"} / kube_deployment_spec_replicas{namespace="observability",deployment="otel-collector-opentelemetry-collector"})', TOOLS["Grafana"]),
    ]
    for index, (title, expr, url) in enumerate(components):
        panel(obs, title, expr, index * 6, 16, status=True, url=url, description="Prontidão das réplicas pelo kube-state-metrics. Não substitui teste de ingestão e consulta de dados.")
    table(obs, "Ferramentas e links", "lab_tool_up", ["tool", "url", "Value"], {"tool": "Ferramenta", "url": "Link", "Value": "Disponível (1=OK)"}, 0, 20, w=12, h=9)["fieldConfig"]["overrides"] = [{"matcher": {"id": "byName", "options": "Link"}, "properties": [{"id": "links", "value": [{"title": "Abrir", "url": "${__value.raw}", "targetBlank": True}]}]}]
    panel(obs, "Tempo de resposta HTTPS", "lab_tool_response_seconds", 12, 20, w=12, h=9, kind="timeseries", unit="s", legend="{{tool}}")
    panel(obs, "Servidores • verificações EC2", "lab_aws_server_up", 0, 29, w=8, h=5, status=True, legend="{{server}}")
    panel(obs, "CPU dos servidores", "lab_aws_server_cpu_percent", 8, 29, w=16, h=7, kind="timeseries", unit="percent", legend="{{server}}")
    panel(obs, "Estado das ferramentas • últimas 24h", "lab_tool_up", 0, 36, w=24, h=7, kind="timeseries", legend="{{tool}}", status=True)
    text(obs, "Como interpretar", "**Ferramentas:** teste HTTPS a cada minuto a partir do servidor privado, passando pelo endereço público e WAF.\n\n**Componentes internos:** prontidão reportada pelo Kubernetes; sem teste sintético de ingestão.\n\n**Servidores:** ITSM, Argo CD e Zabbix; nodes do EKS ficam na dashboard já existente.\n\n**Sem dados** não significa OK. Confira o estado do coletor e a idade da última coleta. O Prometheus existente retém 24 horas de histórico.", 0, 43, h=4)
    fresh_codex = '(time() - lab_codex_quota_observed_timestamp_seconds < 900) and on() (lab_collection_success{group="codex"} == 1)'
    text(aws, "Codex • cota da conta", "Cota medida pelo Codex autenticado neste ambiente, atualizada a cada 5 minutos. A OpenAI fornece **percentual disponível por janela e horário de renovação**, não saldo absoluto em tokens. Valores antigos ficam sem dados após 15 minutos. [Ver uso no Codex](https://chatgpt.com/codex/settings/usage)", 0, 45, h=4)
    for x, window, title in [(0, "primary", "Codex • cota disponível na janela curta"), (6, "secondary", "Codex • cota disponível na janela semanal")]:
        panel(aws, title, 'lab_codex_quota_remaining_percent{bucket="codex",window="' + window + '"} and on() (' + fresh_codex + ')', x, 49, unit="percent", description="Percentual informado pela OpenAI. Não é uma contagem de tokens.")
        panel(aws, "Renova • " + ("janela curta" if window == "primary" else "semanal"), '1000 * lab_codex_quota_reset_timestamp_seconds{bucket="codex",window="' + window + '"} and on() (' + fresh_codex + ')', x + 12, 49, unit="dateTimeAsIso", description="Horário real de reset informado pelo Codex, no fuso do navegador.")
    panel(aws, "Idade da cota Codex", 'time() - lab_codex_quota_observed_timestamp_seconds', 0, 53, w=8, unit="s")
    panel(aws, "Coleta da cota Codex", 'lab_collection_success{group="codex"}', 8, 53, w=8, status=True)
    text(aws, "Saldo absoluto em tokens", "**Não informado pela OpenAI.** Use os percentuais e as janelas de renovação acima. Nenhum token de autenticação ou conteúdo de conversa é enviado à AWS.", 16, 53, w=8, h=4)

    # Existing sections end at row 47; the new application-only service inventory follows.
    live_hosts = '(time() - lab_ec2_host_last_success_timestamp_seconds < 180)'
    service_expr = '((lab_ec2_application_service_status and on(instance_id) ' + live_hosts + ') and on() (lab_collection_success{group="application_hosts"} == 1)) or on(instance_id,app_service) (-1 * lab_ec2_application_service_info)'
    text(obs, "EC2 • serviços essenciais de aplicação", "Processos de aplicação e dependências: Zabbix, Argo CD, GLPI e Kestra. **UP** = processo pronto; **DOWN** = parado, ausente ou não saudável; **DESCONHECIDO** = a sondagem falhou. Docker e Kubernetes são consultados diretamente; não se inventa uma unit systemd para containers. A coluna de recuperação identifica o serviço para a equipe de infra.", 0, 47, h=4)
    for x, title, expr in [(0, "Serviços UP", 'count((' + service_expr + ') == 1) or vector(0)'), (8, "Serviços DOWN", 'count((' + service_expr + ') == 0) or vector(0)'), (16, "Serviços sem leitura válida", 'count((' + service_expr + ') == -1) or vector(0)')]:
        panel(obs, title, expr, x, 51, w=8)
    obj = table(obs, "Serviços de aplicação • estado e recuperação", service_expr, ["server", "application", "app_service", "manager", "repair", "Value"], {"server":"EC2", "application":"Aplicação", "app_service":"Serviço", "manager":"Gerenciador", "repair":"Recuperação sugerida", "Value":"Estado"}, 0, 55, w=24, h=12)
    obj["fieldConfig"]["overrides"] = [{"matcher":{"id":"byName","options":"Estado"}, "properties":[{"id":"mappings","value":[{"type":"value","options":{"1":{"text":"UP","color":"green"},"0":{"text":"DOWN","color":"red"},"-1":{"text":"DESCONHECIDO","color":"orange"}}}]},{"id":"custom.cellOptions","value":{"type":"color-background"}}]}]
    incident = panel(obs, "Serviços que precisam de intervenção", '(' + service_expr + ') == 0', 0, 67, w=24, h=5, legend="{{server}} • {{application}} • {{app_service}}", status=True, description="A lista identifica o serviço de aplicação parado. Não executa recuperação automaticamente.")
    incident["options"]["textMode"] = "value_and_name"
    incident["fieldConfig"]["defaults"]["noValue"] = "Nenhum serviço DOWN"
    incident["fieldConfig"]["defaults"]["displayName"] = "${__field.labels.server} • ${__field.labels.application} • ${__field.labels.app_service}"
    table(obs, "Discos EC2 • uso por ponto de montagem", 'lab_ec2_filesystem_used_percent and on(instance_id) ' + live_hosts, ["server","mountpoint","device","Value"], {"server":"EC2","mountpoint":"Montagem","device":"Dispositivo","Value":"Uso (%)"}, 0, 72, w=14, h=10)["fieldConfig"]["defaults"].update({"unit":"percent","thresholds":{"mode":"absolute","steps":[{"color":"green","value":None},{"color":"orange","value":80},{"color":"red","value":90}]}})
    panel(obs, "Espaço disponível nos discos", 'lab_ec2_filesystem_available_bytes and on(instance_id) ' + live_hosts, 14, 72, w=10, h=10, kind="bargauge", unit="bytes", legend="{{server}} {{mountpoint}}")
    panel(obs, "Uso de discos • histórico", 'lab_ec2_filesystem_used_percent', 0, 82, w=24, h=7, kind="timeseries", unit="percent", legend="{{server}} {{mountpoint}}")
    table(obs, "Sondagens EC2 • atualização", "time() - lab_ec2_host_last_success_timestamp_seconds", ["server","Value"], {"server":"EC2","Value":"Idade da leitura (s)"}, 0, 89, w=24, h=5)
    target = ROOT / "ops/grafana/dashboards"
    target.mkdir(parents=True, exist_ok=True)
    for item in (aws, obs):
        (target / (item["uid"] + ".json")).write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n")
    return aws, obs


if __name__ == "__main__":
    for item in build():
        print(item["uid"], len(item["panels"]), "panels")
