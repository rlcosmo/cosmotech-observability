"""Build the application connectivity/log dashboard from fixed Loki queries."""
import json
from pathlib import Path


def build() -> dict:
    ds = {'type': 'loki', 'uid': 'loki'}
    value = {'uid': 'applications-connectivity-lab', 'title': 'Aplicações | Logs e conexões', 'schemaVersion': 39,
        'version': 0, 'timezone': 'browser', 'time': {'from': 'now-1h', 'to': 'now'}, 'refresh': '30s',
        'tags': ['cosmotech', 'apm', 'logs'], 'panels': [], 'links': [
            {'type': 'link', 'title': 'Command Center', 'url': '/d/command-center'},
            {'type': 'link', 'title': 'Zabbix AWS EKS e APM', 'url': 'https://zabbix.cosmotechsolutions.com.br/zabbix.php?action=dashboard.view&dashboardid=439', 'targetBlank': True}]}
    value['panels'].append({'id': 1, 'type': 'text', 'title': 'Conexões reais a cada 5 minutos',
        'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 4}, 'options': {'mode': 'markdown', 'content':
        'Cada pod faz chamada interna ao serviço par e GET HTTPS em `example.com` a cada **300 segundos**. Uma Lambda fora da VPC chama os dois hosts públicos pelo Scheduler. Logs JSON incluem status, duração e trace ID. As chamadas sintéticas não criam pedidos.\n\nOs spans estão no Tempo e no APM do Zabbix; use o `trace_id` do log para correlacionar. Os contadores abaixo mostram os últimos 15 minutos.'}})
    for i,(app,direction) in enumerate([(a,d) for a in ['orders-api','orders-worker'] for d in ['internal','external']]):
        query = 'sum(count_over_time({namespace="'+app+'",container="'+app+'"} | json | event="synthetic_connection" | direction="'+direction+'" | status_code=200 | __error__="" [15m]))'
        value['panels'].append({'id': i+2, 'type': 'stat', 'title': app+' • '+direction+' HTTP 200', 'datasource': ds,
            'gridPos': {'x': i*6, 'y': 4, 'w': 6, 'h': 4}, 'targets': [{'refId': 'A', 'expr': query, 'queryType': 'instant'}],
            'options': {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}, 'graphMode': 'none', 'colorMode': 'value'},
            'fieldConfig': {'defaults': {'unit': 'short', 'decimals': 0, 'noValue': 'Sem dados'}, 'overrides': []}})
    expression = '{namespace=~"orders-api|orders-worker",container=~"orders-api|orders-worker"} | json | event=~"synthetic_.*"'
    value['panels'].append({'id': 6, 'type': 'logs', 'title': 'Chamadas internas, externas e recebidas • logs correlacionados',
        'datasource': ds, 'gridPos': {'x': 0, 'y': 8, 'w': 24, 'h': 14},
        'targets': [{'refId': 'A', 'expr': expression, 'queryType': 'range', 'maxLines': 1000}],
        'options': {'showTime': True, 'showLabels': False, 'enableLogDetails': True, 'wrapLogMessage': True, 'dedupStrategy': 'none', 'sortOrder': 'Descending'}})
    expression = 'avg by(service,direction) (avg_over_time({namespace=~"orders-api|orders-worker",container=~"orders-api|orders-worker"} | json | event="synthetic_connection" | unwrap duration_ms | __error__="" [5m]))'
    value['panels'].append({'id': 7, 'type': 'timeseries', 'title': 'Duração das conexões', 'datasource': ds,
        'gridPos': {'x': 0, 'y': 22, 'w': 24, 'h': 8}, 'targets': [{'refId': 'A', 'expr': expression, 'queryType': 'range', 'legendFormat': '{{service}} • {{direction}}'}],
        'fieldConfig': {'defaults': {'unit': 'ms'}, 'overrides': []}, 'options': {'legend': {'displayMode': 'list', 'placement': 'bottom'}}})
    return value


if __name__ == '__main__':
    destination = Path(__file__).resolve().parents[1]/'ops/grafana/dashboards/applications-connectivity-lab.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(build(), ensure_ascii=False, indent=2)+'\n')
    print('Built '+destination.name)
