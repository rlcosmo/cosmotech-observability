"""Build Command Center with genuine Zabbix severity and freshness-gated values."""
import json
from pathlib import Path

DS = {'type': 'prometheus', 'uid': 'prometheus'}
FRESH = '(max(lab_collection_success{group="zabbix"}) == 1) and (time() - max(lab_collection_last_success_timestamp_seconds{group="zabbix"}) < 180)'
COLORS = {5: '#E02F44', 4: '#FF6F61', 2: '#F2CC0C', 3: '#FF9830'}


def build() -> dict:
    dash = {'uid': 'command-center', 'title': 'CosmoTech | Command Center', 'schemaVersion': 39,
        'version': 0, 'timezone': 'browser', 'refresh': '30s', 'time': {'from': 'now-6h', 'to': 'now'},
        'tags': ['cosmotech', 'command-center', 'zabbix', 'infra'], 'editable': True, 'panels': [],
        'links': [{'type': 'link', 'title': title, 'url': url, 'targetBlank': True} for title, url in [
            ('Problemas no Zabbix', 'https://zabbix.cosmotechsolutions.com.br/zabbix.php?action=problem.view'),
            ('Serviços e discos', '/d/observability-tools-lab'), ('Logs e conexões', '/d/applications-connectivity-lab'),
            ('AWS e custos', '/d/aws-account-costs-lab')]]}
    def add(value):
        value['id'] = len(dash['panels'])+1
        dash['panels'].append(value)
    add({'type': 'text', 'title': '', 'gridPos': {'x': 0, 'y': 0, 'w': 24, 'h': 2},
         'options': {'mode': 'markdown', 'content': '**COMMAND CENTER** · Incidentes abertos por prioridade. Reconhecidos continuam visíveis; eventos resolvidos ou suprimidos ficam fora da visão. Atualização automática.'}})
    for label, y in [('RESPOSTA IMEDIATA · Disaster e High', 2), ('ATENÇÃO OPERACIONAL · Warning e Average', 20)]:
        add({'type': 'row', 'title': label, 'collapsed': False, 'gridPos': {'x': 0, 'y': y, 'w': 24, 'h': 1}, 'panels': []})
    for severity, name, x, y in [(5, 'Disaster', 0, 3), (4, 'High', 12, 3), (2, 'Warning', 0, 21), (3, 'Average', 12, 21)]:
        add({'type': 'stat', 'title': name, 'datasource': DS, 'gridPos': {'x': x, 'y': y, 'w': 12, 'h': 4},
             'description': 'Quantidade de eventos abertos, não suprimidos e com trigger/host monitorado. Sem coleta válida, exibe SEM COLETA.',
             'targets': [{'refId': 'A', 'expr': '(sum(lab_zabbix_problem_count{severity="'+str(severity)+'"}) and on() ('+FRESH+')) or on() (-1 * (vector(1) unless on() ('+FRESH+')))', 'instant': True, 'range': False}],
             'options': {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}, 'colorMode': 'background_solid',
                         'graphMode': 'none', 'textMode': 'value', 'justifyMode': 'center', 'orientation': 'horizontal'},
             'fieldConfig': {'defaults': {'unit': 'short', 'decimals': 0, 'noValue': 'SEM COLETA',
                 'color': {'mode': 'thresholds'}, 'thresholds': {'mode': 'absolute', 'steps': [
                     {'value': None, 'color': '#299C46'}, {'value': 1, 'color': COLORS[severity]}]},
                 'mappings': [{'type': 'value', 'options': {'-1': {'text': 'SEM COLETA', 'color': 'red'}}}, {'type': 'special', 'options': {'match': 'null', 'result': {'text': 'SEM COLETA', 'color': 'red'}}}]}, 'overrides': []}})
        add({'type': 'table', 'title': name+' · problemas e hosts', 'datasource': DS,
             'gridPos': {'x': x, 'y': y+4, 'w': 12, 'h': 12},
             'targets': [{'refId': 'A', 'expr': '(time() - lab_zabbix_problem_started_timestamp_seconds{severity="'+str(severity)+'"}) and on() ('+FRESH+')',
                          'instant': True, 'range': False, 'format': 'time_series'}],
             'transformations': [{'id': 'labelsToFields', 'options': {'mode': 'columns'}},
                 {'id': 'merge', 'options': {}}, {'id': 'filterFieldsByName', 'options': {'include': {'names': ['host','problem','Value','acknowledged','event_id']}}},
                 {'id': 'organize', 'options': {'indexByName': {'host': 0, 'problem': 1, 'Value': 2, 'acknowledged': 3, 'event_id': 4},
                    'renameByName': {'host': 'Host', 'problem': 'Problema', 'Value': 'Duração', 'acknowledged': 'Reconhecido', 'event_id': 'Evento'}}}],
             'fieldConfig': {'defaults': {'custom': {'align': 'auto', 'cellOptions': {'type': 'auto'}}}, 'overrides': [
                 {'matcher': {'id': 'byName', 'options': 'Duração'}, 'properties': [{'id': 'unit', 'value': 's'}, {'id': 'custom.width', 'value': 100}]},
                 {'matcher': {'id': 'byName', 'options': 'Problema'}, 'properties': [{'id': 'custom.width', 'value': 350}]},
                 {'matcher': {'id': 'byName', 'options': 'Reconhecido'}, 'properties': [{'id': 'mappings', 'value': [
                     {'type': 'value', 'options': {'0': {'text': 'Não'}, '1': {'text': 'Sim'}}}]}]}]},
             'options': {'showHeader': True, 'cellHeight': 'sm', 'sortBy': [{'displayName': 'Duração', 'desc': True}], 'footer': {'show': False}},
             'links': [{'title': 'Abrir problemas no Zabbix', 'url': 'https://zabbix.cosmotechsolutions.com.br/zabbix.php?action=problem.view', 'targetBlank': True}]})
    for title, expression, x, unit, status in [
        ('Coleta de alertas', 'min(lab_collection_success{group="zabbix"})', 0, 'short', True),
        ('Última coleta válida · idade', 'time() - max(lab_collection_last_success_timestamp_seconds{group="zabbix"})', 8, 's', False),
        ('Integração · dias até renovar credencial', '(min(lab_zabbix_token_expiration_timestamp_seconds)-time())/86400', 16, 'd', False)]:
        defaults = {'unit': unit, 'decimals': 0, 'noValue': 'SEM COLETA'}
        if status:
            defaults.update({'color': {'mode': 'thresholds'}, 'thresholds': {'mode': 'absolute', 'steps': [{'value': None, 'color': 'red'}, {'value': 1, 'color': 'green'}]},
                'mappings': [{'type': 'value', 'options': {'0': {'text': 'FALHA', 'color': 'red'}, '1': {'text': 'OK', 'color': 'green'}}}]})
        add({'type': 'stat', 'title': title, 'datasource': DS, 'gridPos': {'x': x, 'y': 38, 'w': 8, 'h': 4},
             'targets': [{'refId': 'A', 'expr': expression, 'instant': True, 'range': False}],
             'fieldConfig': {'defaults': defaults, 'overrides': []},
             'options': {'reduceOptions': {'calcs': ['lastNotNull'], 'values': False}, 'colorMode': 'value', 'graphMode': 'none'}})
    dash["panels"].sort(key=lambda p: (p["gridPos"]["y"], p["gridPos"]["x"]))
    return dash


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1]/'ops/grafana/dashboards/command-center.json'
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2)+'\n')
    print('Built '+path.name)
