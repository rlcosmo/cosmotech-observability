"""Poll native signed GLPI records using existing host credentials; GETs only."""
from __future__ import annotations
import json,os,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from gmud_metrics import render,sample

def atomic(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(value);temporary.chmod(0o644);temporary.replace(path)

def collect(destination):
    now=time.time();destination.mkdir(parents=True,exist_ok=True)
    try:
        # Reuse only the read adapter and decoder, never Runtime/ChangeJournal
        # constructors: those initialize authority journals and may dispatch work.
        sys.path.insert(0,'/opt/cosmotech/promotion/source')
        from automation.gmud import GLPIChanges,ChangeJournal
        cli=os.environ.get('LAB_AWS_CLI','/snap/aws-cli/current/bin/aws')
        result=subprocess.run([cli,'ssm','get-parameter','--region','us-east-1','--name','/cosmotech/itsm/glpi/automation-credentials','--with-decryption','--output','json'],capture_output=True,timeout=30,check=True)
        credentials=json.loads(json.loads(result.stdout)['Parameter']['Value'])
        native=GLPIChanges(credentials).all_changes();reader=object.__new__(ChangeJournal);reader.key=Path('/var/lib/cosmotech-promotion/authority/gmud.key').read_bytes();records=[];unmanaged=0
        for row in native:
            if 'cosmotech_gmud' not in row.get('content',''):
                # Test/protocol changes are explicitly outside the governed flow.
                unmanaged+=1;continue
            records.append(reader.decode(row))
        # Timestamp after bounded native fetch; aggregation uses the same UTC
        # instant for all sources and does not revive stale historical events.
        now=time.time();metrics,p=render(records,now)
        metrics+=sample('cosmotech_gmud_native_changes_scanned',len(native))+'\n'+sample('cosmotech_gmud_unmanaged_changes',unmanaged)+'\n'
        atomic(destination/'gmud.prom',metrics)
        atomic(destination/'summary.json',json.dumps({'at':now,'verified':len(records),'native':len(native),'unmanaged':unmanaged,'created_24h':sum(v for (e,_,_),v in p['counts'].items() if e=='created'),'events_24h':len(p['events'])}))
        print(json.dumps({'component':'gmud-observer','collection_success':True,'verified_records':len(records),'events_24h':len(p['events'])}))
    except Exception as error:
        # Never publish a cached green or fake zero; old gauges disappear on
        # the next scrape. Do not log exception bodies/credential material.
        atomic(destination/'gmud.prom',sample('cosmotech_gmud_collection_success',0)+'\n'+sample('cosmotech_gmud_last_attempt_timestamp_seconds',now)+'\n')
        print(json.dumps({'component':'gmud-observer','collection_success':False,'error_type':type(error).__name__}));return 1
    return 0
if __name__=='__main__':raise SystemExit(collect(Path(os.environ.get('GMUD_METRICS_DIRECTORY','/var/lib/cosmotech-gmud-observer'))))
