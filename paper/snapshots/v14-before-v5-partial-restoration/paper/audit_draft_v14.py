"""Independent V14 manuscript audit using retained raw receipts; stdlib only.

Imports no builder, actor, evaluator, worker, solver, method or checker.
Certificate header identity is checked without semantic proof execution.
"""
from __future__ import annotations
import argparse
import collections
from datetime import datetime, timezone
import hashlib
import itertools
import json
import pathlib
import random
import re
import statistics
from urllib.parse import unquote, urlparse
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXPECTED_SHA='bc84692b270eadb32ee80c0e1c4ac594606329542d6db0852c874287c894be23'
COST_AUDIT_SHA='737ce96dfbe415898c5d7e31eb38f2f25e4fedaabaf2c622b7563a2c9b61338e'
COST_AUDITOR_SHA='bfe3a6ed3baf905684f42729de1840e0609a8b901e027e2fffea5dcce3bc7b6d'
INHERITED={
 'paper/working-draft-v13.md':{'bytes':91174,'sha256':'1ee16425a043c632570300663348c339cf7315c48409597afa239222784092e1'},
 'paper/working-draft-v13.provenance.json':{'bytes':924671,'sha256':'8eba03b5d0fbe3a0693dbb94cf72093a2637969be834fbc33bfba9e9d5a07306'},
 'paper/working-draft-v13.audit.json':{'bytes':10154,'sha256':'888a321a47a5b6e166808ca3d37e575567a5e4a50a68a6da3670fa754be5e19d'},
}
METHODS=['legacy_direct','goal_pruned_direct','original_refinement','shared_lift','guard_pruned_direct']
STATUSES=['certified','unknown','failure','timeout','stopped','stopped_without_closing_receipt','not_started']
FIELDS=['cpu_total_ns','outer_wall_ns','peak_rss_bytes']
METRIC_LABELS={'cpu_total_ns':'Lifetime CPU','outer_wall_ns':'Outer wall','peak_rss_bytes':'Lifetime peak RSS'}
STRICT_PROSE='Shared lifting adds no certified profile coverage and has higher observed full-process median CPU, outer wall and peak RSS than goal-pruned direct on every one of the 54 eligible profiles.'
ORIGINAL_PROSE='Original refinement also has lower observed CPU, wall and RSS medians than shared lifting on all 54 profiles.'

def need(c,r):
    if not c:raise ValueError(r)

def unique(pairs):
    out={}
    for k,v in pairs:
        need(k not in out,'duplicate JSON key');out[k]=v
    return out

def parse(raw):
    return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))

def identity(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def same(a,b):
    return canonical(a)==canonical(b)

def identify(path):
    path=pathlib.Path(path)
    need(not path.is_symlink(),'symbolic input refused')
    path=path.resolve();need(path.is_relative_to(ROOT) and path.is_file(),'regular workspace file required')
    h=hashlib.sha256();size=0
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(262144),b''):h.update(block);size+=len(block)
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':size,'sha256':h.hexdigest()}

def table_rows(draft,marker):
    need(draft.count(marker)==1,'one exact table marker required:'+marker)
    section=draft.split(marker,1)[1]
    block=[];started=False
    for line in section.splitlines():
        if line.startswith('|'):
            block.append([v.strip() for v in line.strip().strip('|').split('|')]);started=True
        elif started:break
    need(len(block)>=2 and all(re.fullmatch(r':?-+:?',v) for v in block[1]),'complete markdown table required')
    need(all(len(r)==len(block[0]) for r in block),'table column count differs')
    return block[0],block[2:]

def summarize_ratios(values):
    need(values and all(type(v) in [int,float] and v>0 for v in values),'positive ratio samples required')
    return {'median_ratio':statistics.median(values),'min_ratio':min(values),'max_ratio':max(values),
            'lower':sum(v<1 for v in values),'equal':sum(v==1 for v in values),'higher':sum(v>1 for v in values)}

def reconstruct_cost(base):
    BASE=pathlib.Path(base).resolve()
    archive=BASE/'artifact.zip';need(identity(archive.read_bytes())['sha256']==EXPECTED_SHA,'archive digest differs')
    records=[]
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();need(len(names)==len(set(names))==11634,'archive member census differs')
        data={n:z.read(n) for n in names}
        def read(n):return parse(data[n])
        retention=parse((BASE/'retention.json').read_bytes())
        need(retention['archive_sha256']==EXPECTED_SHA and retention['archive_bytes']==9438211 and retention['digest_matches_api'] is True,'retention differs')
        extracted=parse((BASE/'extracted-manifest.json').read_bytes())['files']
        need({r['path']:{k:r[k] for k in ['bytes','sha256']} for r in extracted}=={n:identity(raw) for n,raw in data.items()},'extracted inventory differs')
        manifest=read('manifest.json')['files']
        need({r['path'] for r in manifest}==set(names)-{'manifest.json'},'raw artifact inventory differs')
        for r in manifest:need(identity(data[r['path']])=={k:r[k] for k in ['bytes','sha256']},'raw artifact identity differs')
        protocol=read('snapshot/protocol.json');order=read('snapshot/order.json');allocation=read('allocation.json');stored=read('results.json')
        methods=[r['id'] for r in protocol['methods']]
        need(methods==['legacy_direct','goal_pruned_direct','original_refinement','shared_lift','guard_pruned_direct'],'methods differ')
        need(protocol['declared_cells']==allocation['declared_cells']==1650 and protocol['profile_count']==66 and protocol['repeat_count']==5,'allocation denominator differs')
        caps=protocol['caps'];need(caps=={'cpu_soft_seconds':5,'cpu_hard_seconds':6,'wall_seconds':10,'address_space_bytes':536870912,'rss_hard_cap_claimed':False,'solver_logical_allowance':100000000},'caps differ')
        profiles=[p['id'] for p in protocol['profiles']];need(profiles==[f'scale-{i:04d}' for i in range(1,67)] and order['seed']==2026111101,'profiles/seed differ')
        rng=random.Random(2026111101);blocks={}
        for p in profiles:
            perm=methods.copy();rot=list(range(5));rng.shuffle(perm);rng.shuffle(rot);blocks[p]={'initial_permutation':perm,'rotation_for_repeat':rot}
        need(blocks==order['method_blocks'],'balanced method blocks differ')
        expected=[]
        for repeat in range(5):
            ps=profiles.copy();rng.shuffle(ps);need(ps==order['profile_orders'][repeat],'profile order differs')
            for p in ps:
                block=blocks[p];shift=block['rotation_for_repeat'][repeat];perm=block['initial_permutation']
                seed=1+int(hashlib.sha256(f'2026111101|{p}|{repeat}|hash'.encode()).hexdigest()[:16],16)%(2**32-1)
                for position,method in enumerate(perm[shift:]+perm[:shift]):
                    expected.append({'index':len(expected),'id':f'r{repeat+1:02d}--{p}--{method}','profile_id':p,'method_id':method,'repeat':repeat,'position':position,'hash_seed':seed})
        need(expected==order['cells']==allocation['cells'] and len(stored['cells'])==1650,'frozen exact cell order differs')
        need(len(allocation['frozen_files'])==1730,'preexecution file count differs')
        for r in allocation['frozen_files']:need(identity(data[r['path']])=={k:r[k] for k in ['bytes','sha256']},'preexecution frozen file differs')
        previous_suite=read('snapshot/provenance/prior-suite.json');previous_inputs=read('snapshot/provenance/prior-input-manifest.json')
        priors={r['profile_id']:r for r in previous_inputs['cases']}
        need(len(priors)==len(previous_suite['cases'])==66,'prior profile census differs')
        for p,old in zip(protocol['profiles'],previous_suite['cases']):
            need(p['path']==old['path'] and p['family']==old['family'] and identity(data['snapshot/'+p['path']])=={k:priors[p['id']]['input'][k] for k in ['bytes','sha256']},'prior authored profile identity differs')
        unknown_direct={'evidence_not_fresh','indeterminate_observables_or_relations','incomplete_model_or_relation_coverage','work_budget_exhausted'}
        unknown_refine={'evidence_not_fresh','indeterminate_observables','unresolved_relation_or_recipe','incomplete_model_or_relation_coverage','work_budget_exhausted'}
        reasons={
          'legacy_direct':{'supported':{'concrete_recipe_path'},'unsupported':{'complete_relational_product_exhausted'},'unknown':unknown_direct},
          'goal_pruned_direct':{'supported':{'concrete_recipe_path'},'unsupported':{'goal_relevant_relational_product_exhausted'},'unknown':unknown_direct},
          'original_refinement':{'supported':{'public_recipe_witness'},'unsupported':{'certified_refinement_exhaustion'},'unknown':unknown_refine},
          'shared_lift':{'supported':{'public_recipe_witness'},'unsupported':{'certified_refinement_exhaustion'},'unknown':unknown_refine},
          'guard_pruned_direct':{'supported':{'concrete_recipe_path'},'unsupported':{'guard_pruned_goal_relevant_product_exhausted'},'unknown':unknown_direct}}
        probes=collections.defaultdict(set);last_started=None
        for i,cell in enumerate(expected):
            prefix='cells/'+cell['id']+'/'
            job,before,after,reply,result=(read(prefix+n) for n in ['job.json','before.json','after.json','reply.json','solver-result.json'])
            need(job['cell']==before['cell']==after['cell']==reply['cell']==stored['cells'][i]['cell']==cell and job['caps']==before['caps']==reply['caps_observed']==caps,'cell/job/caps identity differs')
            need(before['job_identity']==identity(data[prefix+'job.json']) and before['hash_seed']==cell['hash_seed'] and before['argv'][1:4]==['-S','-P','-B'],'opening identity/seed flags differ')
            need(last_started is None or before['started_utc']>=last_started,'serial openings reversed');last_started=before['started_utc']
            need(stored['cells'][i]==after,'saved row differs from raw closing receipt')
            res=after['resources'];need(type(res) is dict and res['caps_applied_before_exec']==caps and res['resource_source']=='sole terminal os.wait4 per-child rusage after termination' and res['owned_group_cleanup_requested_before_terminal_reap'] is True and res['pid']==res['owned_process_group'] and res['pid']>0,'resource ownership differs')
            for f in ['cpu_user_ns','cpu_system_ns','cpu_total_ns','outer_wall_ns','peak_rss_bytes']:need(type(res[f]) is int and res[f]>=0,'resource value invalid')
            need(abs(res['cpu_user_ns']+res['cpu_system_ns']-res['cpu_total_ns'])<=1 and res['peak_rss_bytes']>=reply['peak_rss_before_reply_bytes'],'CPU sum or RSS scope differs')
            wait=res['wait_status'];code=res['returncode'];need(code==(-(wait&127) if wait&127 else (wait>>8)&255) and wait&127!=127,'terminal status differs')
            derived={'cell':cell,'status':'failure','decision':None,'certificate_valid':None,'resources':res}
            if res['parent_interruption_type'] or res['group_cleanup_error_type']:derived.update(status='stopped',failure_kind='parent_interruption_or_group_cleanup_error')
            elif res['wall_cap_kill_requested'] or code==-14:derived.update(status='timeout',timeout_kind='wall')
            elif code==-24:derived.update(status='timeout',timeout_kind='cpu_soft')
            elif code==-9:derived.update(failure_kind='SIGKILL_cpu_hard_or_external_cause_unattributed')
            elif code==0:derived.update({k:v for k,v in reply.items() if k not in ['schema_version','cell','resources']})
            else:derived.update(failure_kind='nonzero_or_missing_invalid_worker_reply')
            need(derived==after,'status/reply projection differs')
            need(reply['solver_result_identity']==identity(data[prefix+'solver-result.json']) and canonical(result)==data[prefix+'solver-result.json'],'result identity differs')
            meter={'budget':result['stats'].get('budget'),'work_units':result['stats'].get('work_units'),'reason':result.get('reason')}
            need(reply['method_meter']==meter and result['decision']==reply['decision'],'raw meter/decision differs')
            raw_headroom=type(meter['work_units']) is int and meter['budget']==100000000 and meter['work_units']<meter['budget']
            need(reply['solver_logical_cap_nonbinding'] is raw_headroom,'raw frozen headroom projection differs')
            valid_reason=meter['reason'] in reasons[cell['method_id']][result['decision']]
            independent_headroom=False if meter['reason']=='work_budget_exhausted' or meter['work_units']>=meter['budget'] else (True if valid_reason and meter['budget']==100000000 else None)
            if after['status']=='certified':need(after['certificate_valid'] is True and after['decision'] in ['supported','unsupported'],'unaccepted verdict counted')
            if after['status']=='unknown':need(after['decision']=='unknown' and after['certificate_valid'] is None,'unknown verdict differs')
            need(reply['interpreter_flags']=={'no_site':1,'safe_path':True,'isolated':0,'ignore_environment':0},'seed interpreter flags differ')
            probes[(cell['profile_id'],cell['repeat'])].add(reply['hash_seed_probe'])
            profile_raw=data['snapshot/'+job['profile']['path']];model=parse(profile_raw)
            need(reply['profile_identity']==identity(profile_raw),'worker profile byte identity differs')
            if after['status']=='certified':
                certificate=result['certificate']
                digest=hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
                need(certificate['profile_sha256']==digest and all(type(certificate[f]) is int for f in ['checked_at','horizon','valid_until']) and certificate['checked_at']==100 and certificate['horizon']==model['model']['horizon'] and certificate['valid_until']==model['model']['evidence']['valid_until'],'certificate profile or strict clock/horizon/expiry binding differs')
                expected_kind='recipe-path' if result['decision']=='supported' else {'legacy_direct':'relational-exhaustion','goal_pruned_direct':'goal-pruned-relational-exhaustion/2','original_refinement':'refinement-exhaustion','shared_lift':'refinement-exhaustion','guard_pruned_direct':'goal-pruned-relational-exhaustion/2'}[cell['method_id']]
                need(certificate['kind']==expected_kind,'certificate kind differs')
            records.append({'cell':cell,'status':after['status'],'decision':after['decision'],'certificate_valid':after['certificate_valid'],'resources':res,'method_meter':meter,'raw_headroom':raw_headroom,'independent_headroom':independent_headroom,'headroom_label_disagrees':raw_headroom is not independent_headroom,'valid_method_reason':valid_reason})
        need(all(len(p)==1 for p in probes.values()) and len(probes)==330,'shared seeded hash probe differs')
        indexed={(r['cell']['profile_id'],r['cell']['repeat'],r['cell']['method_id']):r for r in records}
        contradictions=[]
        for p in profiles:
            verdicts={r['decision'] for r in records if r['cell']['profile_id']==p and r['status']=='certified'}
            if len(verdicts)>1:contradictions.append(p)
        cohorts={}
        for left,right in itertools.combinations(methods,2):
            accepted=[];excluded=[]
            for p in profiles:
                pairs=[(indexed[(p,r,left)],indexed[(p,r,right)]) for r in range(5)]
                allrows=[r for pair in pairs for r in pair];why=[]
                if p in contradictions:why.append('profile-wide certified contradiction')
                if any(r['status']!='certified' for r in allrows):why.append('not all five paired repeats certified')
                if len({r['decision'] for r in allrows})!=1:why.append('different paired or repeated decisions')
                if any(r['independent_headroom'] is not True for r in allrows):why.append('logical allowance binding or indeterminate')
                if any(not r['valid_method_reason'] for r in allrows):why.append('unrecognized method reason')
                if any(r['resources']['cpu_total_ns']>=5000000000 or r['resources']['outer_wall_ns']>=10000000000 for r in allrows):why.append('CPU or wall limit binding')
                if why:excluded.append({'profile_id':p,'reasons':why});continue
                item={'profile_id':p,'paired_repeats':5}
                for field in ['cpu_total_ns','outer_wall_ns','peak_rss_bytes']:
                    a=statistics.median(r[0]['resources'][field] for r in pairs);b=statistics.median(r[1]['resources'][field] for r in pairs)
                    item[field]={'left_median':a,'right_median':b,'left_over_right':a/b if b>0 else None}
                accepted.append(item)
            key=left+'__'+right
            frozen=stored['summary']['paired_costs'][key]
            projection={'complete_same_decision_certified_profile_count':len(accepted),'required_paired_repeats_per_profile':5,'per_profile':accepted}
            need(projection==frozen,'independent conservative cohort differs from frozen runner:'+key)
            cohorts[key]={**projection,'excluded_profiles':excluded}
        method_totals={}
        for m in methods:
            rows=[r for r in records if r['cell']['method_id']==m]
            statuses=dict(collections.Counter(r['status'] for r in rows))
            need(statuses==stored['summary']['by_method_status_counts'][m],'status total differs')
            method_totals[m]={'allocated':len(rows),'statuses':statuses,'decisions':dict(collections.Counter(r['decision'] for r in rows)),'cpu_total_ns_sum':sum(r['resources']['cpu_total_ns'] for r in rows),'outer_wall_ns_sum':sum(r['resources']['outer_wall_ns'] for r in rows),'peak_rss_bytes_max':max(r['resources']['peak_rss_bytes'] for r in rows),'unknown_reasons':dict(collections.Counter(r['method_meter']['reason'] for r in rows if r['status']=='unknown')),'headroom_label_discrepancies':sum(r['headroom_label_disagrees'] for r in rows)}
    result={'status':'independent_all_1650_raw_cost_review_complete','archive_identity':{'bytes':9438211,'sha256':EXPECTED_SHA},'run_id':42927208534,'head_sha':'d058c2a05e278b71ad5969e49ecdd344576cf166','cells':1650,'launched_and_closed':1650,'verified_archive_members':11634,'frozen_preexecution_files':1730,'methods':method_totals,'pair_cohorts':cohorts,'certified_profile_contradictions':contradictions,'hash_seed_probe_disagreements':0,'logical_label_discrepancies':sum(r['headroom_label_disagrees'] for r in records),'records':records,'original_worker_solver_checker_application_or_provider_execution':False,'certificate_semantics_reexecuted':False,'limits':['66 related authored profiles; five dependent timing replicates','Enforced RLIMIT_AS; measured lifetime RSS with no RSS hard-cap claim','Costs include fresh interpreter/import/solver/checker/output lifetime','Checker acceptance comes from bound captured receipts','Unknown/exhausted/failure/timeout outcomes stay in denominator and outside cost ratios']}
    
    return result

def audit(draft_path, provenance_path, cost_base, cost_audit_path, output):
    draft_path,provenance_path,cost_base,cost_audit_path,output=map(lambda p:pathlib.Path(p).resolve(),[draft_path,provenance_path,cost_base,cost_audit_path,output])
    need(not output.exists() and output.is_relative_to(ROOT),'fresh workspace audit output required')
    draft=draft_path.read_text(encoding='utf-8');flat=re.sub(r'\s+',' ',draft)
    provenance=parse(provenance_path.read_bytes());checks=[]
    def check(name,condition,evidence):
        checks.append({'id':name,'passed':bool(condition),'evidence':evidence})
        need(condition,'V14 check failed:'+name)
    inputs=provenance['inputs']
    check('all_build_input_bytes_and_current_draft_bound',provenance['schema_version']=='paper-v14-evidence-bound-build/1'
          and provenance['paper_sha256']==identify(draft_path)['sha256']
          and len(inputs)==len({r['path'] for r in inputs})
          and all(same(identify(ROOT/r['path']),r) for r in inputs),len(inputs))
    for name,expected in INHERITED.items():
        actual=identify(ROOT/name)
        check('frozen_'+name.replace('/','_'),same({k:actual[k] for k in ['bytes','sha256']},expected)
              and actual in inputs,actual)
    inherited=(ROOT/'paper/working-draft-v13.md').read_text(encoding='utf-8')
    check('registered_title_and_inherited_V13_identity',draft.splitlines()[0]==inherited.splitlines()[0]
          and provenance['inherited_v13_sha256']==INHERITED['paper/working-draft-v13.md']['sha256'],draft.splitlines()[0])
    for marker in ['**Table V13A.','**Table V13S.']:
        check('inherited_'+marker,table_rows(draft,marker)==table_rows(inherited,marker),'Earlier native cell tables unchanged')
    run=parse((cost_base/'github-run.json').read_bytes())
    artifact=parse((cost_base/'github-artifacts.json').read_bytes())['artifacts']
    retention=parse((cost_base/'retention.json').read_bytes())
    candidates=[r for r in artifact if r['id']==retention['artifact_id']]
    check('actual_API_bound_completed_cost_run',run['id']==42927208534 and run['run_attempt']==1
          and run['status']=='completed' and run['head_sha']=='d058c2a05e278b71ad5969e49ecdd344576cf166'
          and retention['workflow_conclusion']==run['conclusion'] and retention['head_sha']==run['head_sha']
          and retention['api_digest']=='sha256:'+EXPECTED_SHA and len(candidates)==1
          and candidates[0]['workflow_run']['id']==run['id'] and candidates[0]['workflow_run']['head_sha']==run['head_sha']
          and candidates[0]['digest']==retention['api_digest'] and candidates[0]['size_in_bytes']==9438211,
          {'run_id':run['id'],'conclusion':run['conclusion']})
    check('final_cost_audit_and_preserved_source_bound',identify(cost_audit_path)['sha256']==COST_AUDIT_SHA
          and identify(cost_audit_path.parent/'auditor-source.py')['sha256']==COST_AUDITOR_SHA
          and identify(cost_audit_path) in inputs,identify(cost_audit_path))
    cost=reconstruct_cost(cost_base)
    check('all_1650_raw_cost_rows_and_ten_cohorts_reconstructed',cost['cells']==cost['launched_and_closed']==1650
          and len(cost['pair_cohorts'])==10 and all(len(p['per_profile'])==54 for p in cost['pair_cohorts'].values()),cost['methods'])
    saved_audit=parse(cost_audit_path.read_bytes())
    audit_rows=[parse(line) for line in (cost_audit_path.parent/'cells.jsonl').read_bytes().splitlines()]
    check('independent_raw_rows_match_final_read_audit',len(audit_rows)==1650 and all(
          all(same(ours[f],theirs[f]) for f in ['cell','status','decision','certificate_valid','resources','method_meter'])
          and ours['independent_headroom'] is theirs['independent_solver_logical_cap_nonbinding']
          for ours,theirs in zip(cost['records'],audit_rows)),1650)
    check('ten_final_audit_cohort_tables_match_raw_medians',all(
          same(pair['per_profile'],saved_audit['paired_profile_costs'][key]['per_profile'])
          for key,pair in cost['pair_cohorts'].items()),10)
    counts={}
    for method in METHODS:
        totals=cost['methods'][method]
        counts[method]={'allocated':totals['allocated'],**{s:totals['statuses'].get(s,0) for s in STATUSES},
                        'supported':totals['decisions'].get('supported',0),'unsupported':totals['decisions'].get('unsupported',0)}
    pair_summaries={}
    for key,pair in cost['pair_cohorts'].items():
        left,right=key.split('__')
        pair_summaries[key]={'left_method':left,'right_method':right,'profiles':len(pair['per_profile']),
                            'medians':{f:statistics.median(p[f]['left_over_right'] for p in pair['per_profile']) for f in FIELDS}}
    inverse={f:summarize_ratios([p[f]['right_median']/p[f]['left_median'] for p in cost['pair_cohorts']['goal_pruned_direct__shared_lift']['per_profile']]) for f in FIELDS}
    check('provenance_cost_inputs_and_reconstructed_summary_bound',provenance['cost_run_id']==42927208534
          and provenance['cost_run_attempt']==1 and pathlib.Path(provenance['cost_base_path']).resolve()==cost_base
          and pathlib.Path(provenance['cost_audit_path']).resolve()==cost_audit_path
          and same(provenance['cost_method_counts'],counts)
          and same(provenance['cost_pair_summaries'],pair_summaries)
          and same(provenance['shared_vs_goal_pruned_direct'],inverse),'All summaries computed from raw receipts')
    header,rows=table_rows(draft,'**Table V14A.')
    expected_header=['Method','Allocated','Certified','Supported','Unsupported','Unknown','Failure','Timeout','Stopped','Unclosed','Not started']
    expected_rows=[[m]+[str(counts[m][f]) for f in ['allocated','certified','supported','unsupported','unknown','failure','timeout','stopped','stopped_without_closing_receipt','not_started']] for m in METHODS]
    check('V14A_complete_status_denominators_and_decisions',header==expected_header and rows==expected_rows,counts)
    header,rows=table_rows(draft,'**Table V14B.')
    expected_rows=[[p['left_method']+' / '+p['right_method'],str(p['profiles'])]+[f"{p['medians'][f]:.6f}" for f in FIELDS] for p in pair_summaries.values()]
    check('V14B_all_ten_six_decimal_paired_cost_tables',header==['Left / right method','Paired profiles','Median CPU ratio','Median wall ratio','Median peak RSS ratio']
          and rows==expected_rows,pair_summaries)
    header,rows=table_rows(draft,'**Table V14C.')
    expected_rows=[[METRIC_LABELS[f],f"{inverse[f]['median_ratio']:.6f}",f"{inverse[f]['min_ratio']:.6f} to {inverse[f]['max_ratio']:.6f}",
                    f"{inverse[f]['lower']} / {inverse[f]['equal']} / {inverse[f]['higher']}"] for f in FIELDS]
    check('V14C_per_profile_inversion_ranges_and_strict_direction',header==['Metric','Median shared/direct ratio','Observed profile ratio range','Shared lower / equal / higher']
          and rows==expected_rows and all(inverse[f]['lower']==inverse[f]['equal']==0 and inverse[f]['higher']==54 and inverse[f]['min_ratio']>1 for f in FIELDS),inverse)
    check('shared_vs_goal_prose_matches_every_paired_profile',STRICT_PROSE in flat,'Strictly higher on every eligible profile; no inversion of aggregate median')
    check('original_vs_shared_prose_matches_all_54_profiles',ORIGINAL_PROSE in flat and all(
          p[f]['left_median']<p[f]['right_median'] for p in cost['pair_cohorts']['original_refinement__shared_lift']['per_profile'] for f in FIELDS),54)
    check('cost_limits_and_original_study_scope_remain_explicit',all(s in flat for s in [
          'five dependent timing','RLIMIT_AS','RSS','96-task','288-path-cell','96-crossing'])
          and ('66 authored development profiles' in flat or '66 related authored profiles' in flat)
          and 'related' in flat and 'held-out' in flat and 'human' in flat
          and provenance['original_study_tasks']==96 and provenance['original_study_paths']==288 and provenance['original_study_crossings']==96
          and all(provenance[k] is False for k in ['original_full_scope_revised','full_original_study_complete','publication_ready','human_scientific_review']),
          'Single-run development pipeline; original qualification remains open')
    broken=[]
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',draft):
        if target.startswith(('http://','https://','#','mailto:')):continue
        path=(draft_path.parent/unquote(target.split('#',1)[0])).resolve()
        if not path.exists() and path!=output:broken.append(target)
    check('local_manuscript_links_resolve',not broken,broken)
    result={'schema_version':'paper-v14-independent-read-audit/1','status':'passed_independent_raw_cost_and_manuscript_audit',
            'created_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'checks_passed':len(checks),
            'draft_identity':identify(draft_path),'provenance_identity':identify(provenance_path),
            'cost_archive_identity':cost['archive_identity'],'cost_method_counts':counts,'cost_pair_summaries':pair_summaries,
            'shared_vs_goal_pruned_direct':inverse,'inherited_V13_frozen_identities':INHERITED,
            'new_builder_actor_evaluator_worker_solver_checker_or_provider_calls':0,
            'certificate_semantics_reexecuted':False,'auditor_source_identity':identify(__file__)}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['draft','provenance','cost-base','cost-audit','output']:parser.add_argument('--'+name,type=pathlib.Path,required=True)
    args=parser.parse_args()
    result=audit(args.draft,args.provenance,args.cost_base,args.cost_audit,args.output)
    print(json.dumps({'status':result['status'],'checks_passed':result['checks_passed'],'new_runtime_calls':0},sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())

