"""Deterministic GMUD 24h dashboard; no credentials or generated events."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DS={'type':'prometheus','uid':'${datasource}'}
GATE=' and on() (cosmotech_gmud_collection_success == 1 and on() (time() - cosmotech_gmud_last_success_timestamp_seconds < 180))'
D={'uid':'cosmotech-gmud-24h','title':'CosmoTech | GMUD — Últimas 24 Horas','schemaVersion':39,'version':1,'tags':['cosmotech','v2-005','gmud'],'timezone':'browser','time':{'from':'now-24h','to':'now'},'refresh':'1m','editable':False,'description':'Eventos reais do fluxo governado GLPI → Kestra → Actions → Argo CD. Janela móvel UTC de 24h, calculada no observador. Implantações exigem validação técnica registrada; CI verde não é deploy concluído. Mudanças de teste de protocolo fora do fluxo governado são contadas separadamente.','templating':{'list':[{'name':'datasource','type':'datasource','query':'prometheus','current':{'text':'prometheus-aws-eks-istio-lab-dev','value':'prometheus'},'hide':0}]},'panels':[]}
def panel(title,expr,x,y,w=6,h=4,kind='stat',unit='short',description='',gate=True):
 p={'id':len(D['panels'])+1,'title':title,'type':kind,'datasource':DS,'gridPos':{'x':x,'y':y,'w':w,'h':h},'description':description,'targets':[{'refId':'A','expr':'('+expr+')'+(GATE if gate else ''),'instant':True,'format':'table' if kind in ['table','barchart','piechart'] else 'time_series'}],'fieldConfig':{'defaults':{'unit':unit,'noValue':'SEM TELEMETRIA','color':{'mode':'palette-classic'}},'overrides':[]},'options':{'reduceOptions':{'calcs':['lastNotNull'],'values':False},'colorMode':'value','graphMode':'none'}}
 if kind in ['table','barchart','piechart']:
  p['options']={'showHeader':True};p['transformations']=[{'id':'labelsToFields','options':{'mode':'columns'}}]
 D['panels'].append(p);return p
D['panels'].append({'id':1,'title':'Trilha real e significado dos números','type':'text','gridPos':{'x':0,'y':0,'w':24,'h':3},'options':{'mode':'markdown','content':'**GLPI assinado → Kestra → GitHub Actions → Argo CD.** Contagem única por GMUD e transição confirmada; retries não criam eventos. A implantação é concluída quando a validação técnica foi registrada; o encerramento da GMUD pode exigir observação posterior. **Zero só aparece após coleta válida.** Fonte ausente fica sem telemetria. Janela móvel de 24h do observador, independente do zoom de gráficos.'}})
panel('Coleta GLPI assinada','cosmotech_gmud_collection_success',0,3,w=8,gate=False,description='1 = leitura nativa e assinatura verificadas. 0 = indisponível; os demais indicadores são omitidos.')
panel('Idade da coleta','time() - cosmotech_gmud_last_success_timestamp_seconds',8,3,w=8,unit='s',gate=False)
panel('GMUDs verificadas no histórico','cosmotech_gmud_records_verified',16,3,w=8)
items=[('GMUDs criadas','created'),('Aprovadas automaticamente','approved_auto'),('Aprovadas manualmente','approved_manual'),('GMUDs rejeitadas','rejected'),('Aguardando aprovação',None),('Deploys iniciados','deploy_started'),('Deploys concluídos','deploy_success'),('Deploys com falha','deploy_failed'),('Rollbacks validados','rollback')]
for i,(title,event) in enumerate(items):
 expr='cosmotech_gmud_pending_24h' if event is None else 'sum(cosmotech_gmud_events_24h{event="'+event+'"})'
 panel(title,expr,(i%4)*6,7+(i//4)*4,description='Eventos ocorridos nas últimas 24h.' if event else 'GMUDs criadas nas últimas 24h que ainda aguardam aprovação; não é o backlog histórico.')
p=panel('Tempo médio de aprovação','cosmotech_gmud_approval_seconds_sum_24h / cosmotech_gmud_approval_count_24h',6,15,unit='s');p['fieldConfig']['defaults']['noValue']='N/A — sem aprovações'
p=panel('Tempo médio de implantação','cosmotech_gmud_deployment_seconds_sum_24h / cosmotech_gmud_deployment_count_24h',12,15,unit='s');p['fieldConfig']['defaults']['noValue']='N/A — sem implantações'
p=panel('Taxa de sucesso das implantações','100 * sum(cosmotech_gmud_events_24h{event="deploy_success"}) / sum(cosmotech_gmud_events_24h{event=~"deploy_success|deploy_failed|rollback"})',18,15,unit='percent',description='Sucessos / implantações terminadas no período (sucesso, falha ou rollback). Sem terminadas = N/A, nunca 100% inventado.');p['fieldConfig']['defaults']['noValue']='N/A — sem deploys'
panel('GMUDs por hora · janela móvel','cosmotech_gmud_created_hourly',0,19,w=12,h=7,kind='barchart',description='Buckets UTC; primeiro e último podem ser parciais. Apenas eventos reais de criação na janela móvel.')
panel('Automática versus manual','sum by(event)(cosmotech_gmud_events_24h{event=~"approved_auto|approved_manual"})',12,19,w=12,h=7,kind='barchart')
panel('Mudanças por aplicação','sum by(application)(cosmotech_gmud_events_24h{event="created"})',0,26,w=8,h=7,kind='barchart')
panel('Mudanças por criticidade','sum by(criticality)(cosmotech_gmud_events_24h{event="created"})',8,26,w=8,h=7,kind='barchart')
panel('Resultado das implantações','sum by(event)(cosmotech_gmud_events_24h{event=~"deploy_success|deploy_failed|rollback"})',16,26,w=8,h=7,kind='barchart')
p=panel('Linha do tempo · eventos confirmados','cosmotech_gmud_event_timestamp_seconds',0,33,w=24,h=8,kind='table',unit='dateTimeAsIso',description='Timestamp é o horário original do evento, não o horário de scrape. Vazio com coleta saudável e zero eventos significa ausência real no período.')
p['transformations'] += [{'id':'organize','options':{'excludeByName':{'Time':True,'__name__':True,'event_id':True},'renameByName':{'Value':'Horário UTC','gmud_id':'GMUD','event':'Evento','application':'Aplicação','criticality':'Criticidade','execution_id':'Execução','run_id':'Actions run'}}}]
p=panel('GMUDs e registros de origem · atividade nas últimas 24h','cosmotech_gmud_change_info',0,41,w=24,h=9,kind='table',description='Uma linha por GMUD com evento no período. Links apontam os registros originais. Ausência com coleta saudável é zero real de atividade.')
p['transformations'] += [{'id':'organize','options':{'excludeByName':{'Time':True,'Value':True,'__name__':True,'execution_id':True,'run_id':True},'renameByName':{'gmud_id':'GMUD','application':'Aplicação','criticality':'Criticidade','approval':'Aprovação','status':'Status','created_at':'Criação UTC','approval_seconds':'Aprovação (s)','deploy_seconds':'Deploy (s)'}}}]
for field in ['glpi_url','kestra_url','github_url','argo_url']:
 p['fieldConfig']['overrides'].append({'matcher':{'id':'byName','options':field},'properties':[{'id':'links','value':[{'title':'Abrir origem','url':'${__value.raw}','targetBlank':True}]}]})
D['panels'].append({'id':len(D['panels'])+1,'title':'Sem eventos e limites de cobertura','type':'text','gridPos':{'x':0,'y':50,'w':24,'h':4},'options':{'mode':'markdown','content':'Com coleta saudável e **GMUDs criadas = 0**, não houve criação no fluxo governado na janela. Médias sem observações e taxa sem implantações terminadas ficam **N/A**. As duas mudanças de teste/protocolo não assinadas são inventariadas separadamente e não representam releases. O dashboard anterior de Canary permanece independente. Eventos são correlacionados pela GMUD, execução Kestra e run Actions. Loki continua sendo a fonte de logs das aplicações; a trilha de mudanças é projetada diretamente do GLPI assinado, sem conceder escrita adicional no Loki.'}})
# Datasource current UID comes from the deployed default; a deterministic variable
# with no persisted stale selection lets Grafana choose the configured source.
D['templating']['list'][0].pop('current')
path=ROOT/'ops/grafana/dashboards/gmud-24h.json';path.write_text(json.dumps(D,ensure_ascii=False,indent=2)+'\n')
manifest={'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'cosmotech-gmud-24h','namespace':'observability','labels':{'grafana_dashboard':'1'},'annotations':{'grafana_folder':'CosmoTech Lab V2'}},'data':{'gmud-24h.json':json.dumps(D,ensure_ascii=False)}}
(ROOT/'ops/kubernetes/gmud-24h-dashboard.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
