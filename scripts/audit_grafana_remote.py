"""Authenticated bounded audit. Run inside the existing Grafana sidecar; credentials stay in its environment. NDJSON goes to a private file, never Git raw. Distinguishes empty results from real zero samples."""
import os,json,re,time,math,requests,collections
S=requests.Session();S.trust_env=False;S.auth=(os.environ['REQ_USERNAME'],os.environ['REQ_PASSWORD']);B='http://localhost:3000';NOW=time.time();START=NOW-86400
D=S.get(B+'/api/datasources',timeout=15).json();byuid={x['uid']:x for x in D};byname={x['name']:x for x in D};P=next(x for x in D if x['type']=='prometheus');CACHE={}
def request(ds,path,params):
 key=json.dumps([ds['uid'],path,params],sort_keys=True)
 if key not in CACHE:
  try:
   r=S.get(B+'/api/datasources/proxy/uid/'+ds['uid']+path,params=params,timeout=18);a=r.json();CACHE[key]=(r.status_code,a)
  except Exception as e:CACHE[key]=(0,{'error':type(e).__name__})
 return CACHE[key]
def expand(q,v):
 for k,val in sorted(v.items(),key=lambda x:-len(x[0])):
  q=q.replace('${'+k+':regex}',str(val)).replace('${'+k+'}',str(val));q=re.sub(r'\$'+re.escape(k)+r'\b',lambda m:str(val),q)
 return q
mac={'__rate_interval':'5m','__interval':'5m','__range':'24h','__range_s':'86400','__interval_ms':'300000','__range_ms':'86400000','__from':str(int(START*1000)),'__to':str(int(NOW*1000))}
def dsresolve(obj,vs):
 if obj is None:return P,None
 uid=obj.get('uid') if isinstance(obj,dict) else obj
 uid=expand(str(uid),vs)
 if uid in byuid:return byuid[uid],None
 if uid in byname:return byname[uid],None
 if uid in ['-- Mixed --','mixed','-- Grafana --','grafana','__expr__']:return None,None
 return None,'Invalid datasource reference: '+uid
search=S.get(B+'/api/search',params={'type':'dash-db','limit':1000},timeout=15).json()
for item in search:
 row=S.get(B+'/api/dashboards/uid/'+item['uid'],timeout=20).json();d=row['dashboard'];vs=dict(mac);vr=[]
 for v in d.get('templating',{}).get('list',[]):
  n=v['name'];kind=v.get('type');cur=v.get('current') or {};value=cur.get('value');query=v.get('query','');query=query.get('query','') if isinstance(query,dict) else query
  if kind=='datasource':
   selected=next((x for x in D if x['type']==query),P);vs[n]=selected['uid'];vr.append({'name':n,'kind':kind,'configured':value,'resolved':vs[n],'invalid_current':bool(value and value not in byuid and value not in byname and value not in ['default'])});continue
  if kind in ['constant','custom','textbox','interval']:
   vs[n]=value or str(query).split(',')[0];continue
  if kind!='query':continue
  query=expand(str(query),vs);values=[];err=None
  if query.startswith('label_values(') and query.endswith(')'):
   inner=query[13:-1];selector,label=inner.rsplit(',',1) if ',' in inner else ('',inner);selector=selector.strip();label=label.strip()
   params={'start':START,'end':NOW}
   if selector:params['match[]']=selector
   code,a=request(P,'/api/v1/label/'+label+'/values',params);values=a.get('data',[]) if code==200 else [];err=a.get('error') if code!=200 else None
  elif query.startswith('query_result('):
   code,a=request(P,'/api/v1/query',{'query':query[13:-1],'time':NOW,'timeout':'8s'});values=[str(r.get('value',['',''])[1]) for r in a.get('data',{}).get('result',[])] if code==200 else []
  if v.get('includeAll') and (value=='$__all' or value==['$__all']):resolved=v.get('allValue') or '.*'
  elif isinstance(value,str) and value in values:resolved=value
  else:resolved=values[0] if values else ''
  vs[n]=resolved;vr.append({'name':n,'kind':kind,'query':query,'configured':value,'resolved':resolved,'options_count':len(values),'empty_options':not values,'error':err})
 print(json.dumps({'kind':'variables','dashboard':d['uid'],'variables':vr}),flush=True)
 def panels(ps):
  for p in ps:
   yield p
   yield from panels(p.get('panels',[]))
 for p in panels(d.get('panels',[])):
  rec={'kind':'panel','dashboard':d['uid'],'dashboard_title':d['title'],'folder':row['meta'].get('folderTitle'),'panel_id':p.get('id'),'title':p.get('title'),'type':p.get('type'),'start':START,'end':NOW,'targets':[]}
  targets=p.get('targets',[])
  if not targets:
   rec.update(classification='OK',structural=True,reason='Static text, navigation or row; no data query');print(json.dumps(rec),flush=True);continue
  for t in targets:
   ds,err=dsresolve(t.get('datasource',p.get('datasource')),vs);q=t.get('expr') or t.get('query') or '';raw=q;q=expand(q,vs);tr={'refId':t.get('refId'),'hidden':t.get('hide',False),'raw_query':raw,'query':q,'datasource_uid':ds['uid'] if ds else None,'datasource_type':ds['type'] if ds else None}
   if err:tr.update(classification='ERRO',reason=err)
   elif ds is None or not q:tr.update(classification='SEM TELEMETRIA',reason='No executable datasource query')
   elif re.search(r'\$[A-Za-z_{]',q):tr.update(classification='ERRO',reason='Unresolved dashboard variable')
   elif ds['type']=='prometheus':
    code,a=request(ds,'/api/v1/query_range',{'query':q,'start':START,'end':NOW,'step':3600,'timeout':'8s','limit':100})
    tr['http_status']=code;tr['warnings']=a.get('warnings',[])
    if code!=200 or a.get('status')!='success':tr.update(classification='BLOQUEADO' if code in [0,429,503,504] or a.get('errorType') in ['timeout','canceled'] else 'ERRO',reason=str(a.get('error','HTTP '+str(code)))[:500])
    else:
     rs=a.get('data',{}).get('result',[]);vals=[float(v[1]) for r in rs for v in r.get('values',[]) if len(v)>1 and v[1] not in ['NaN','+Inf','-Inf']];tr.update(series=len(rs),finite_samples=len(vals),nonzero_samples=sum(v!=0 for v in vals))
     if vals:tr.update(classification='OK' if any(v!=0 for v in vals) else 'ZERO LEGÍTIMO',reason='Real samples returned' if any(v!=0 for v in vals) else 'Real zero-valued samples returned')
     else:tr.update(classification='SEM TELEMETRIA',reason='Query valid but no finite samples; zero is not inferred')
   elif ds['type']=='loki':
    code,a=request(ds,'/loki/api/v1/query_range',{'query':q,'start':int(START*1e9),'end':int(NOW*1e9),'step':3600,'limit':100});rs=a.get('data',{}).get('result',[]);tr['http_status']=code;tr['series']=len(rs)
    if code!=200:tr.update(classification='ERRO',reason=str(a.get('error','HTTP '+str(code)))[:500])
    else:tr.update(classification='OK' if rs else 'SEM TELEMETRIA',reason='Real Loki results' if rs else 'No matching streams in retained interval; absence not proven to be zero')
   elif ds['type']=='tempo':
    code,a=request(ds,'/api/search',{'q':q,'start':int(START),'end':int(NOW),'limit':10});tr.update(http_status=code,classification=('OK' if a.get('traces') else 'SEM TELEMETRIA') if code==200 else 'ERRO',reason='Tempo search executed')
   else:tr.update(classification='BLOQUEADO',reason='Datasource audit adapter not available')
   rec['targets'].append(tr)
  order={'ERRO':5,'BLOQUEADO':4,'SEM TELEMETRIA':3,'OK':2,'ZERO LEGÍTIMO':1};rec['classification']=max((x['classification'] for x in rec['targets']),key=lambda c:order[c]);print(json.dumps(rec),flush=True)
