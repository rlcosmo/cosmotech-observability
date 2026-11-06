import base64
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

secret=json.loads(subprocess.check_output(['kubectl','-n','observability','get','secret','prometheus-grafana','-o','json']))['data']
user=base64.b64decode(secret['admin-user']).decode();password=base64.b64decode(secret['admin-password']).decode()
headers={'Authorization':'Basic '+base64.b64encode((user+':'+password).encode()).decode(),'Content-Type':'application/json'}
origin='https://grafana.cosmotechsolutions.com.br'
def call(path,body=None):
 with urllib.request.urlopen(urllib.request.Request(origin+path,headers=headers,data=json.dumps(body).encode() if body is not None else None,method='POST' if body is not None else 'GET'),timeout=25) as r:return json.load(r)
p=Path(__file__).resolve().parents[1]/'ops/grafana/dashboards/orders-worker-canary.json'
dashboard=json.loads(p.read_text())
try:
 previous=call('/api/dashboards/uid/orders-worker-canary')
 backup=Path('/tmp/cosmotech-dashboard-before-rcl.json');backup.write_text(json.dumps(previous));backup.chmod(0o600)
 dashboard['id']=previous['dashboard']['id'];dashboard['version']=previous['dashboard']['version']
except urllib.error.HTTPError as e:
 if e.code!=404:raise
result=call('/api/dashboards/db',{'dashboard':dashboard,'overwrite':True,'message':'GMUD RCL e métricas reais por versão; sem dados não é zero'})
verified=call('/api/dashboards/uid/orders-worker-canary')
assert verified['dashboard']['title']==dashboard['title']
print(json.dumps({'status':result['status'],'uid':result['uid'],'url':origin+result['url'],'panels':len(verified['dashboard']['panels']),'all_panels_validated':False}))
