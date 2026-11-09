"""Apply only audited fixes to versioned dashboard models; no live Grafana writes."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def fix_grafana_overview(d):
    d=copy.deepcopy(d);panel=next(p for p in d['panels'] if p['id']==6)
    for t in panel.get('targets',[]):
        if 'grafana_alerting_result_total' in t.get('expr',''):
            t['expr']=t['expr'].replace('grafana_alerting_result_total','grafana_alerting_alerts')
    panel['description']='Current alerting-state gauge exposed by Grafana 13.3. The legacy evaluation counter is absent; no zero fallback is added.'
    return d

def fix_canary(d):
    d=copy.deepcopy(d);p=next(p for p in d['panels'] if p['id']==5)
    p['targets']=[{'refId':'A','expr':'cosmotech_worker_inflight','legendFormat':'em processamento · {{cosmotech_io_gmud_id}} · {{channel}}'},{'refId':'B','expr':'cosmotech_worker_draining','legendFormat':'drenagem · {{cosmotech_io_gmud_id}} · {{channel}}'}]
    p['description']='Two independent gauges. PromQL OR would mask draining when both gauges share the same label set.'
    return d

def fix_retention(d):
    d=copy.deepcopy(d)
    for p in d['panels']:
        options=p.get('options',{});text=options.get('content','')
        if 'O Prometheus existente retém 24 horas de histórico.' in text:
            options['content']=text.replace('O Prometheus existente retém 24 horas de histórico.','O Prometheus restaurado está configurado para até 30 dias ou 8 GB; a disponibilidade real depende da coleta e do ponto restaurado. O Tempo usa retenção de 720h na cópia consistente. Lacunas anteriores à restauração não são preenchidas artificialmente.')
    return d

if __name__=='__main__':
    p=ROOT/'ops/grafana/dashboards/orders-worker-canary.json';p.write_text(json.dumps(fix_canary(json.loads(p.read_text())),ensure_ascii=False,indent=2)+'\n')
    p=ROOT/'scripts/build_lab_dashboards.py';s=p.read_text().replace('O Prometheus existente retém 24 horas de histórico.','O Prometheus restaurado está configurado para até 30 dias ou 8 GB; a disponibilidade real depende da coleta e do ponto restaurado. O Tempo usa retenção de 720h na cópia consistente. Lacunas anteriores à restauração não são preenchidas artificialmente.');p.write_text(s)
