"""Private source-boundary evaluator; never imported by the public actor."""
from copy import deepcopy


def grade(output,gold):
    expected={case['id']:case for case in gold['cases']}
    actual={case['id']:case for case in output['cases']}
    if len(actual)!=len(output['cases']) or set(actual)!=set(expected):
        raise ValueError('qualification_case_denominator_changed')
    reports=[]
    for identity,rule in expected.items():
        value=actual[identity]
        if rule['kind']=='original_failure':
            events=value.get('events',[])
            texts=[part.get('text') for event in events for part in event.get('status',{}).get('message',{}).get('parts',[]) if part.get('kind')=='text']
            passed=(len(events)==1 and events[0].get('status',{}).get('state')=='failed'
                    and events[0].get('final') is True and 'artifact' not in events[0]
                    and texts==[rule['text']])
        elif rule['kind']=='first_occurrence':
            passed=value.get('selected','absent') is None and value.get('all_occurrences')==[None,'later-public-value']
        else:
            error=value.get('exception') or {}
            passed=(value.get('extracted_text')==rule['text'] and error.get('type')=='ValueError'
                    and error.get('message','').startswith('credentials_provider credential fetch failed (state=')
                    and error.get('message','').endswith(': '+rule['text']))
        reports.append({'id':identity,'source_boundary_passed':passed})
    return {'cases':reports,'passed':sum(row['source_boundary_passed'] for row in reports),'total':len(reports),
            'full_application_qualification':False,'human_review':False,'independent_holdout':False}


def adversarial_controls(output,gold):
    reports=[]
    for case in output['cases']:
        altered=deepcopy(output)
        value=next(row for row in altered['cases'] if row['id']==case['id'])
        if 'events' in value:value['events'][0]['status']['state']='completed'
        elif 'selected' in value:value['selected']='later-public-value'
        else:value['exception']=None
        rejected=not next(row for row in grade(altered,gold)['cases'] if row['id']==case['id'])['source_boundary_passed']
        reports.append({'id':case['id'],'forged_success_or_changed_output_rejected':rejected})
    missing=deepcopy(output);missing['cases'].pop()
    try:grade(missing,gold)
    except ValueError:missing_rejected=True
    else:missing_rejected=False
    return {'mutated_outputs':reports,'missing_case_rejected':missing_rejected,
            'all_rejected':all(row['forged_success_or_changed_output_rejected'] for row in reports) and missing_rejected}
