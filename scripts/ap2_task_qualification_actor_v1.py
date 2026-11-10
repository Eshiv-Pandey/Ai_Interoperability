"""Execute public AP2 boundary inputs using fully imported original modules.

No evaluator/gold input is read. This fixed development actor is not a shopper
model and does not establish a complete native/provider purchase trajectory.
"""
import argparse
import asyncio
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    inputs=json.loads(args.input.read_bytes())
    root=Path(inputs['root'])
    forbidden={root/'benchmark/tasks-v1/ap2/evaluator.json',root/'benchmark/tasks-v1/ap2/qualification-private-v1.json',
               root/'scripts/ap2_task_qualification_evaluator_v1.py',root/'scripts/run_ap2_task_qualification_v1.py'}
    counts={'private_reads_blocked':0,'network_operations_blocked':0,'process_launches_blocked':0}
    def deny(event,values):
        if event=='open' and values and isinstance(values[0],(str,bytes,os.PathLike)):
            path=Path(os.fsdecode(values[0])).absolute()
            if path in forbidden or path.name.lower().startswith('gemini-api-key') or path.name=='.env':
                counts['private_reads_blocked']+=1
                raise PermissionError('private_or_credential_input_denied')
        if event in {'socket.connect','socket.connect_ex','socket.bind','socket.getaddrinfo','socket.sendto'}:
            counts['network_operations_blocked']+=1
            raise PermissionError('offline_network_denied')
        if event=='subprocess.Popen' or event=='os.system' or event.startswith('os.spawn'):
            counts['process_launches_blocked']+=1
            raise PermissionError('owned_actor_descendant_denied')
    sys.addaudithook(deny)
    try:
        (root/'benchmark/tasks-v1/ap2/evaluator.json').read_bytes()
    except PermissionError:
        probe_blocked=True
    else:
        raise ValueError('private_input_probe_was_not_blocked')
    if any(name in os.environ for name in ('GOOGLE_API_KEY','GEMINI_API_KEY','GOOGLE_APPLICATION_CREDENTIALS')):
        raise ValueError('provider_credential_present')
    sys.path[:0]=[inputs['samples'],inputs['site_packages']]
    import logging
    logging.disable(logging.CRITICAL)
    from a2a.server.events.event_queue import EventQueue
    from a2a.server.tasks.task_updater import TaskUpdater
    from a2a.types import Task,TaskStatus,TaskState
    from common import message_utils
    from common.a2a_message_builder import A2aMessageBuilder
    merchant=importlib.import_module('roles.merchant_agent.tools')
    processor=importlib.import_module('roles.merchant_payment_processor_agent.tools')
    source_records={}
    for module in (merchant,processor,message_utils,importlib.import_module('common.a2a_message_builder')):
        path=Path(module.__file__).absolute()
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        expected=inputs['source_hashes'][path.relative_to(Path(inputs['source_root'])).as_posix()]
        if digest!=expected:raise ValueError('original_imported_source_changed')
        source_records[module.__name__]={'path':str(path),'sha256':digest}
    async def execute():
        results=[]
        for case in inputs['cases']:
            operation=case['operation']
            output={'id':case['id'],'operation':operation}
            if operation=='message_first_occurrence':
                output['selected']=message_utils.find_data_part(case['key'],case['data_parts'])
                output['all_occurrences']=message_utils.find_data_parts(case['key'],case['data_parts'])
            elif operation=='processor_remote_error_diagnostics':
                builder=A2aMessageBuilder().set_context_id(case['context_id']).set_task_id(case['task_id'])
                builder.add_text(case['texts'][0]).add_data('unrelated_metadata',{'text':'not a TextPart'})
                builder.add_text('').add_text(case['texts'][1])
                task=Task(id=case['task_id'],context_id=case['context_id'],status=TaskStatus(state=TaskState.failed,message=builder.build()))
                output['extracted_text']=processor._extract_task_error_text(task)
                try:
                    processor._raise_if_task_failed(task,case['peer'],case['operation_label'])
                except Exception as error:
                    output['exception']={'type':type(error).__name__,'message':str(error)}
                else:output['exception']=None
            else:
                queue=EventQueue(max_queue_size=16)
                updater=TaskUpdater(queue,case['task_id'],case['context_id'])
                function=merchant.create_checkout if operation=='merchant_unavailable_cart' else merchant.dpc_finish if operation=='dpc_missing_checkout_mandate' else merchant.initiate_payment
                await function(case['data_parts'],updater,None)
                events=[]
                while not queue.queue.empty():
                    event=await queue.dequeue_event(no_wait=True)
                    events.append(event.model_dump(mode='json',by_alias=True,exclude_none=True))
                    queue.task_done()
                output['events']=events
            results.append(output)
        return results
    # Windows' asyncio loop constructor opens a loopback self-pipe. These
    # already-immediate SDK failure paths need no loop or external await.
    coroutine=execute()
    try:
        coroutine.send(None)
    except StopIteration as completed:
        results=completed.value
    else:
        coroutine.close()
        raise ValueError('external_async_wait_outside_boundary_control')
    imported={}
    environment=json.loads(Path(inputs['environment_manifest']).read_bytes())
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if not filename:continue
        path=Path(filename).absolute()
        env_root=Path(environment['root'])
        if path.is_relative_to(env_root):
            name=path.relative_to(env_root).as_posix()
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            if name not in environment['files'] or digest!=environment['files'][name]['sha256']:
                raise ValueError('frozen_imported_module_changed')
            imported[name]=digest
    result={'schema_version':'ap2-task-qualification-actor/1','status':'harness_completed','cases':results,
            'original_modules_imported':source_records,'imported_environment_files_verified':imported,
            'private_evaluator_read_probe_blocked':probe_blocked,'denials':counts,
            'provider_requests':0,'full_shopper_workflow_completed':False,'actor_type':'fixed original-function development actor',
            'async_intervention':'Drive only already-immediate original SDK coroutines; external awaits refused; no event loop/service bootstrap'}
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps({'status':result['status'],'cases':len(results),'provider_requests':0}))


if __name__=='__main__':main()
