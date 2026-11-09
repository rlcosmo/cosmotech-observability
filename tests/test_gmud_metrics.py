"""Controlled offline cases never submitted to GLPI or any live pipeline."""
import copy
from datetime import datetime,timezone
import pytest
from gmud_metrics import project,render,normalize
NOW=datetime.fromisoformat('2026-11-09T16:00:00+00:00').timestamp()
def when(offset):return datetime.fromtimestamp(NOW+offset,timezone.utc).isoformat()
def change(events=None,phase='CREATED'):
 return {'id':'immutable-change','change_id':17,'criticality':'NON_CRITICAL','synthetic':False,'phase':phase,'release':{'service':'orders-worker','execution_id':'execution-1','run_id':'123'},'events':events or [{'type':'created','at':when(-300)}]}
def event(kind,offset,**details):return {'type':kind,'at':when(offset),'details':details}
def test_no_changes_is_real_zero_with_health():
 text,p=render([],NOW);assert 'cosmotech_gmud_collection_success 1' in text;assert p['pending']==0;assert not p['counts'];assert not p['rows'];assert 'cosmotech_gmud_approval_count_24h 0' in text
@pytest.mark.parametrize('principal,reason,expected',[('policy-engine','deterministic','approved_auto'),('operator@example.invalid','human_decision','approved_manual')])
def test_approval_mode_requires_evidence(principal,reason,expected):
 r=change([event('created',-300),event('approved',-240,principal=principal,reason=reason)],'APPROVED');p=project([r],NOW);assert sum(v for (kind,_,_),v in p['counts'].items() if kind==expected)==1;assert p['approval_durations']==[60]
def test_pending():assert project([change()],NOW)['pending']==1
def test_rejected_is_not_deploy_failure():
 p=project([change([event('created',-300),event('rejected',-200)],'REJECTED')],NOW);assert p['counts'][('rejected','orders-worker','NON_CRITICAL')]==1;assert not p['counts'][('deploy_failed','orders-worker','NON_CRITICAL')]
def test_pipeline_success_does_not_prove_deploy():
 p=project([change([event('created',-300),event('ci_success',-240)],'CREATED')],NOW);assert not p['counts'][('deploy_success','orders-worker','NON_CRITICAL')]
def test_technical_validation_proves_deployment():
 r=change([event('created',-300),event('deploying',-240),event('observing',-120,technical_validation=True)],'OBSERVING');p=project([r],NOW);assert p['counts'][('deploy_success','orders-worker','NON_CRITICAL')]==1;assert p['deployment_durations']==[120]
def test_failed_deployment():
 p=project([change([event('created',-300),event('deploying',-240),event('failed',-120)],'FAILED')],NOW);assert p['counts'][('deploy_failed','orders-worker','NON_CRITICAL')]==1

def test_validated_rollback():
 p=project([change([event('created',-300),event('deploying',-240),event('rolled_back',-120,rollback_validated=True)],'ROLLED_BACK')],NOW);assert p['counts'][('rollback','orders-worker','NON_CRITICAL')]==1

def test_retries_and_duplicate_records_are_idempotent():
 r=change([event('created',-300),event('created',-299),event('approved',-240,principal='policy-engine'),event('approved',-239,principal='policy-engine')],'APPROVED');p=project([r,copy.deepcopy(r)],NOW);assert sum(p['counts'].values())==2

def test_old_changes_outside_window_are_not_created_again():
 r=change([event('created',-90000),event('approved',-240,principal='policy-engine')],'APPROVED');p=project([r],NOW);assert not p['counts'][('created','orders-worker','NON_CRITICAL')];assert p['counts'][('approved_auto','orders-worker','NON_CRITICAL')]==1

def test_unknown_approval_is_not_invented():
 with pytest.raises(ValueError):normalize(change([event('created',-300),event('approved',-200)]))

def test_unvalidated_rollback_rejected():
 with pytest.raises(ValueError):normalize(change([event('created',-300),event('rolled_back',-200)]))

def test_synthetic_changes_are_excluded():
 r=change();r['synthetic']=True;assert not project([r],NOW)['events']

def test_future_event_is_rejected():
 with pytest.raises(ValueError):project([change([event('created',100)])],NOW)
