"""Independent 1,650-cell read-only cost and cohort reconstruction."""
import collections, hashlib, itertools, json, pathlib, random, statistics, zipfile
BASE=pathlib.Path(__file__).resolve().parent
EXPECTED_SHA='bc84692b270eadb32ee80c0e1c4ac594606329542d6db0852c874287c894be23'
def need(c,r):
    if not c:raise ValueError(r)
def unique(pairs):
    out={}
    for k,v in pairs:
        need(k not in out,'duplicate JSON key');out[k]=v
    return out
def parse(raw):return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def identity(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
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
with (BASE/'independent-raw-cost-review-v1.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['records','pair_cohorts']}|{'cohort_profile_counts':{k:len(v['per_profile']) for k,v in cohorts.items()}},sort_keys=True))

