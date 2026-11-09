import json,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('fixes',ROOT/'scripts/build_dashboard_audit_fixes.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_canary_keeps_both_gauges_and_every_other_panel():
 d=json.loads((ROOT/'ops/grafana/dashboards/orders-worker-canary.json').read_text());p=next(p for p in d['panels'] if p['id']==5);assert [t['expr'] for t in p['targets']]==['cosmotech_worker_inflight','cosmotech_worker_draining'];assert len(d['panels'])==12;assert m.fix_canary(d)==d

def test_grafana_replaces_only_the_proven_obsolete_metric():
 d={'uid':'keep','panels':[{'id':6,'targets':[{'expr':'grafana_alerting_result_total{state="alerting"}'}]},{'id':7,'targets':[{'expr':'up'}]}]};f=m.fix_grafana_overview(d);assert f['panels'][0]['targets'][0]['expr']=='grafana_alerting_alerts{state="alerting"}';assert f['panels'][1]==d['panels'][1];assert f['uid']==d['uid']

def test_retention_text_matches_recovery_configuration():
 d=json.loads((ROOT/'ops/grafana/dashboards/observability-tools-lab.json').read_text());s=json.dumps(d,ensure_ascii=False);assert 'até 30 dias ou 8 GB' in s;assert 'existente retém 24 horas' not in s
