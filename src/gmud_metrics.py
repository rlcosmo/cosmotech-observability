"""Read-only rolling GMUD projection. No deployment or approval authority."""
from __future__ import annotations
import collections
import hashlib
import json
from datetime import datetime, timezone

EVENTS = ('created','approved_auto','approved_manual','rejected','deploy_started','deploy_success','deploy_failed','rollback')
APPS = ('orders-api','orders-worker')
CRITICALITIES = ('CRITICAL','NON_CRITICAL','CUSTOM_CRITICAL')

def stamp(value):
    d=datetime.fromisoformat(value)
    if d.tzinfo is None: raise ValueError('Timezone required')
    return d.timestamp()

def normalize(record):
    """Deduplicate retries by immutable change/phase/execution binding, not delivery count."""
    if record.get('synthetic') is not False: return []
    release=record.get('release',{})
    app=release.get('service',record.get('application'))
    if app not in APPS or record.get('criticality') not in CRITICALITIES: raise ValueError('Unknown change identity')
    result=[];seen=set();started=False
    for e in sorted(record['events'],key=lambda x:stamp(x['at'])):
        t=e['type'];details=e.get('details',{});at=stamp(e['at']);kind=None
        if t=='created':kind='created'
        elif t=='approved':
            if e.get('manual') is not None:manual=e['manual']
            elif details.get('principal')=='policy-engine':manual=False
            elif details.get('reason')=='human_decision' and details.get('principal'):manual=True
            else:raise ValueError('Unverifiable approval mode')
            kind='approved_manual' if manual else 'approved_auto'
        elif t=='rejected':kind='rejected'
        elif t=='deploying':kind='deploy_started';started=True
        elif t=='observing':
            if details.get('technical_validation') is not True or not started:raise ValueError('Deployment validation absent')
            kind='deploy_success'
        elif t=='failed' and started:kind='deploy_failed'
        elif t=='rolled_back':
            if details.get('rollback_validated') is not True:raise ValueError('Rollback not validated')
            kind='rollback'
        if kind:
            # A governed GMUD has one dispatch and one terminal result. Repeated
            # callbacks/timestamps do not create another business transition.
            key=(str(record['id']),kind)
            if key in seen:continue
            seen.add(key);identity=hashlib.sha256(json.dumps(key).encode()).hexdigest()
            result.append({'event_id':identity,'event':kind,'at':at,'application':app,'criticality':record['criticality'],'gmud_id':str(record['change_id']),'execution_id':release.get('execution_id',record.get('execution_id','')),'run_id':release.get('run_id',record.get('run_id',''))})
    if not any(e['event']=='created' for e in result):raise ValueError('Missing creation event')
    return result

def project(records,now):
    lower=now-86400;events=[];seen={};rows=[];approval=[];deployment=[];counts=collections.Counter();hourly=collections.Counter();all_events=[]
    for r in records:
        if r['id'] in seen:
            if seen[r['id']]!=r:raise ValueError('Conflicting duplicate change')
            continue
        seen[r['id']]=r
        if r.get('synthetic') is not False:continue
        normalized=normalize(r);all_events+=normalized;by={e['event']:e for e in normalized};created=by['created']['at']
        if any(e['at']>now+5 for e in normalized):raise ValueError('Future event')
        in_window=[e for e in normalized if lower<e['at']<=now]
        for e in in_window:
            events.append(e);counts[(e['event'],e['application'],e['criticality'])]+=1
            if e['event']=='created':hourly[int(e['at']//3600)*3600]+=1
        approved=by.get('approved_manual') or by.get('approved_auto')
        if approved and lower<approved['at']<=now:approval.append(approved['at']-created)
        end=by.get('deploy_success') or by.get('deploy_failed') or by.get('rollback');start=by.get('deploy_started')
        if end and start and lower<end['at']<=now:deployment.append(end['at']-start['at'])
        if in_window:
            rel=r.get('release',{});run=str(rel.get('run_id',r.get('run_id','')));app=by['created']['application'];cid=str(r['change_id']);execution=rel.get('execution_id',r.get('execution_id',''))
            rows.append({'gmud_id':cid,'rcl':r.get('rcl_id') or cid,'application':app,'criticality':r['criticality'],'approval':('manual' if approved and approved['event']=='approved_manual' else 'automatic' if approved else 'pending'),'status':r['phase'],'created_at':datetime.fromtimestamp(created,timezone.utc).isoformat(),'approval_seconds':str(approved['at']-created) if approved else '','deploy_seconds':str(end['at']-start['at']) if end and start else '', 'glpi_url':'https://glpi.cosmotechsolutions.com.br/front/change.form.php?id='+cid,'kestra_url':r.get('kestra_url',''),'github_url':f'https://github.com/rlcosmo/cosmotech-{app}/actions/runs/{run}','argo_url':'https://argocd.cosmotechsolutions.com.br/applications/argocd/'+r.get('argo_application',app+'-dev'),'execution_id':execution,'run_id':run})
    pending=sum(r.get('synthetic') is False and r['phase'] in ['CREATED','HUMAN_REVIEW'] and lower<next(e['at'] for e in normalize(r) if e['event']=='created')<=now for r in seen.values())
    return {'counts':counts,'hourly':hourly,'pending':pending,'approval_durations':approval,'deployment_durations':deployment,'events':events,'rows':rows,'historical_events':all_events,'records':len(seen)}

def sample(name,value,**labels):
    text=','.join(k+'='+json.dumps(str(v),ensure_ascii=True) for k,v in sorted(labels.items()))
    return name+('{'+text+'}' if labels else '')+' '+str(value)

def render(records,now):
    p=project(records,now);out=[sample('cosmotech_gmud_collection_success',1),sample('cosmotech_gmud_last_success_timestamp_seconds',now),sample('cosmotech_gmud_records_verified',p['records'])]
    for event in EVENTS:
        for app in APPS:
            for crit in CRITICALITIES:out.append(sample('cosmotech_gmud_events_24h',p['counts'][(event,app,crit)],event=event,application=app,criticality=crit))
    out.append(sample('cosmotech_gmud_pending_24h',p['pending']))
    for name,values in [('approval',p['approval_durations']),('deployment',p['deployment_durations'])]:
        out+=[sample('cosmotech_gmud_'+name+'_seconds_sum_24h',sum(values)),sample('cosmotech_gmud_'+name+'_count_24h',len(values))]
    for i in range(24):
        hour=int(now//3600)*3600-i*3600
        out.append(sample('cosmotech_gmud_created_hourly',p['hourly'][hour],hour=datetime.fromtimestamp(hour,timezone.utc).isoformat()))
    for row in p['rows']:out.append(sample('cosmotech_gmud_change_info',1,**row))
    for e in p['events']:
        event=dict(e);at=event.pop('at');out.append(sample('cosmotech_gmud_event_timestamp_seconds',at,**event))
    return '\n'.join(out)+'\n',p
