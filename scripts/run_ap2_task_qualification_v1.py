"""Run two fresh original-function AP2 boundary passes with private evaluator.

These are development realizations attached to prospective held-out labels,
not full shopper performance or independently authored/secret held-out gold.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import ap2_reference_development_v2 as setup
from ap2_task_qualification_evaluator_v1 import grade,adversarial_controls

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def record(path,base):return {'path':path.relative_to(base).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}
def execute(output):
    output=output.absolute();output.mkdir(parents=True,exist_ok=False)
    _,environment,source_rows=setup.frozen_inputs()
    application=ROOT/'benchmark/tasks-v1/ap2/application.json'
    evaluator=ROOT/'benchmark/tasks-v1/ap2/evaluator.json'
    private=ROOT/'benchmark/tasks-v1/ap2/qualification-private-v1.json'
    actor=ROOT/'scripts/ap2_task_qualification_actor_v1.py'
    bank=json.loads(application.read_bytes());gold=json.loads(private.read_bytes())
    signed_capture=ROOT/'runs/ap2-reference-development/v2/offline-subset-base-20261110T1258Z/events.jsonl'
    rows=[json.loads(line) for line in signed_capture.read_bytes().splitlines()]
    token=next(row['actual_result']['payment_mandate'] for row in rows if row['operation']=='original_shopper_signer_results')
    common={'task_id':'public-task-qualification','context_id':'public-context-qualification'}
    cases=[
        {'id':'ap2-ho-019','operation':'merchant_unavailable_cart','data_parts':[{'cart_id':'source-boundary-unavailable-cart'}]},
        {'id':'ap2-ho-020','operation':'merchant_missing_payment_mandate','data_parts':[{'risk_data':'public-development-risk'}]},
        {'id':'ap2-ho-021','operation':'merchant_missing_risk_data','data_parts':[{'ap2.mandates.PaymentMandateSdJwt':token}]},
        {'id':'ap2-ho-022','operation':'dpc_missing_checkout_mandate','data_parts':[]},
        {'id':'ap2-ho-023','operation':'message_first_occurrence','key':'selected','data_parts':[{'selected':None},{'selected':'later-public-value'}]},
        {'id':'ap2-ho-024','operation':'processor_remote_error_diagnostics','peer':'credentials_provider','operation_label':'credential fetch','texts':['first error','second error']},
    ]
    cases=[{**common,**case} for case in cases]
    public={'schema_version':'ap2-task-qualification-public-input/1','root':str(ROOT),'source_root':str(setup.SOURCE_ROOT),
            'samples':str(setup.SAMPLES),'site_packages':environment['site_packages'],
            'environment_manifest':str(ROOT/setup.ENV_REL),'source_hashes':{name:row['sha256'] for name,row in source_rows.items()},
            'cases':cases,'public_task_records':[row for row in bank['records'] if row['id'] in {case['id'] for case in cases}],
            'signed_input_provenance':{'source':signed_capture.relative_to(ROOT).as_posix(),'sha256':sha(signed_capture),
                'classification':'reused original development signer output, possibly expired; no verification or full payment claim; risk guard runs before processor/verifier'}}
    write(output/'public-input.json',public)
    files=[application,evaluator,private,actor,ROOT/'scripts/ap2_task_qualification_evaluator_v1.py',Path(__file__),signed_capture,ROOT/'scripts/ap2_reference_development_v2.py']
    plan={'schema_version':'ap2-task-qualification-plan/1','created_at_utc':datetime.now(timezone.utc).isoformat(),
          'original_inputs':[record(path,ROOT) for path in files],'public_input':record(output/'public-input.json',output),
          'case_ids':[case['id'] for case in cases],'public_actor_has_evaluator_input':False,'worker_timeout_seconds':90,
          'reference_and_actor_passes':2,'provider_requests':0,'qualification_scope':'imported-original source-boundary development controls only'}
    write(output/'plan.json',plan)
    result={'schema_version':'ap2-task-qualification-result/1','status':'failed','runs':[],'provider_requests':0,
            'full_application_qualification':False,'human_review':False,'independent_holdout':False}
    try:
        for label in ('reference','actor'):
            profile=setup.allocate_profile()
            command=[environment['base_interpreter']['path'],'-I','-S','-B',str(actor),'--input',str(output/'public-input.json'),'--output',str(output/(label+'-output.json'))]
            try:
                completed=subprocess.run(command,cwd=profile,env=setup.child_environment(profile),capture_output=True,timeout=90,check=False)
                for name,data in (('stdout.bin',completed.stdout),('stderr.bin',completed.stderr)):
                    with (output/(label+'-'+name)).open('xb') as stream:stream.write(data)
                receipt={'label':label,'argv':command,'returncode':completed.returncode,'private_profile':str(profile)}
            finally:cleanup=setup.cleanup_profile(profile)
            receipt['cleanup']=cleanup
            write(output/(label+'-process.json'),receipt)
            if completed.returncode!=0 or not cleanup['complete']:raise ValueError('original_actor_failed_or_cleanup_incomplete')
            observed=json.loads((output/(label+'-output.json')).read_bytes())
            scored=grade(observed,gold)
            if scored['passed']!=scored['total'] or scored['total']!=6:raise ValueError('source_boundary_gold_mismatch')
            if observed['denials']!={'private_reads_blocked':1,'network_operations_blocked':0,'process_launches_blocked':0}:raise ValueError('actor_isolation_probe_or_offline_denial_failed')
            result['runs'].append({'label':label,'grade':scored,'imported_environment_files_verified':len(observed['imported_environment_files_verified']),
                                   'private_evaluator_read_probe_blocked':observed['private_evaluator_read_probe_blocked']})
        observed=json.loads((output/'actor-output.json').read_bytes())
        controls=adversarial_controls(observed,gold)
        if not controls['all_rejected']:raise ValueError('private_evaluator_negative_control_failed')
        result['adversarial_controls']=controls
        if any(record(ROOT/item['path'],ROOT)!=item for item in plan['original_inputs']):raise ValueError('qualification_original_input_changed')
        result.update(status='development_source_boundary_qualification_passed',original_inputs_unchanged=True,
                      source_cases_per_pass=6,original_imported_invocations_total=12,
                      scope_limit='Two fixed-actor passes, not model-performance trials; neither human gold review nor complete held-out shopper qualification')
    except Exception as error:result['error_type']=type(error).__name__;result['error']=str(error)
    write(output/'result.json',result)
    write(output/'manifest.json',{'files':[record(path,output) for path in sorted(output.rglob('*')) if path.is_file()]})
    print(json.dumps({key:result[key] for key in ('status','provider_requests','full_application_qualification')}))
    return 0 if result['status']=='development_source_boundary_qualification_passed' else 2

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(execute(parser.parse_args().output))
