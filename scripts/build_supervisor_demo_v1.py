#!/usr/bin/env python3
"""Build a portable, read-only presentation of retained AgentOps v10 evidence.

No application processes, network requests, model calls or outcome changes.
Only writes demo/supervisor-v1; --check verifies the built package and inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "supervisor-v1"
REPORT = "runs/agentops-native-eligibility/bridge-parent-check-v10.json"
GAPS = "docs/research/source-evidence/agentops-bridge-gaps-v1/result.json"
RAW = "runs/agentops-native-eligibility/linux-bridge-v10/workspace/runs/agentops-http-control"
ORDER = [f"N{i}" for i in range(1, 12)] + [f"B{i}" for i in range(1, 8)]
TITLE = "Benchmarking Framework for LLM-Based Agent Interoperability: Measuring Interoperability Loss Across Heterogeneous Agent Boundaries"
BRIDGES = {
    "B1": "Amir ordinary typed text",
    "B2": "Amir Tasks form",
    "B3": "Amir MRTR opaque-state continuation",
    "B4": "mgcrea typed polling text",
    "B5": "mgcrea stock raw request",
    "B6": "mgcrea public factory · passthrough fetch",
    "B7": "mgcrea public factory · explicit version header",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


CSS = r"""
:root{--paper:#f3f4f7;--surface:#ffffff;--ink:#24273a;--muted:#575b6c;--line:#cbcbd1;--accent:#3e428c;--accent-soft:#e9e9f4;--good:#24644c;--good-bg:#e8f2ec;--warn:#7a4e16;--warn-bg:#f6ebd7;--quiet:#eae8e3;font-family:Segoe UI,Arial,sans-serif;color:var(--ink);background:var(--paper);font-synthesis:none;font-size:16px;line-height:1.5;scrollbar-color:var(--muted) var(--paper);accent-color:var(--accent);caret-color:var(--accent)}
*{box-sizing:border-box}body{margin:0}a{color:var(--accent);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}button,select{font:inherit}button,select,.button{min-height:42px;border:1px solid var(--line);border-radius:5px;color:var(--ink);background:var(--surface);padding:8px 12px}button,.button{cursor:pointer}button:hover,.button:hover{background:var(--accent-soft)}button:disabled{opacity:.48;cursor:default}button.primary{background:var(--accent);color:white;border-color:var(--accent)}button.primary:hover{background:#30346f}button.active{border-color:var(--accent);background:var(--accent-soft)}:focus-visible{outline:3px solid var(--accent);outline-offset:3px}::selection{background:#d6d5ef;color:var(--ink)}h1,h2,h3,p{margin-top:0}h1,h2,h3{font-family:Georgia,Cambria,serif;line-height:1.12;font-weight:400;text-wrap:balance}h1{font-size:clamp(2.1rem,3.8vw,3.5rem);letter-spacing:-.035em;max-width:22ch;margin-bottom:18px}h2{font-size:1.7rem;margin-bottom:13px}h3{font-size:1.2rem;margin-bottom:10px}p{max-width:74ch}code,pre{font-family:Consolas,monospace;font-size:.84rem}code{overflow-wrap:anywhere}pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;background:#eef0f5;padding:15px;border-radius:4px;line-height:1.55;max-height:370px;overflow:auto}small,.small{font-size:.84rem}.muted{color:var(--muted)}.nowrap{white-space:nowrap}.skip{position:absolute;top:-100px;left:10px;background:white;padding:12px;z-index:10}.skip:focus{top:10px}.shell{max-width:1540px;margin:auto;padding:0 42px}.topbar{border-bottom:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;gap:20px;padding:18px 0}.brand{font-weight:650;letter-spacing:-.025em;font-size:1.12rem}.toplinks{display:flex;align-items:center;gap:20px;font-size:.9rem}.archive{background:var(--accent);color:white;padding:4px 9px;border-radius:3px;font-size:.78rem;font-weight:600;white-space:nowrap}.intro{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:70px;padding:42px 0 30px;align-items:end}.intro p{margin-bottom:0;color:var(--muted)}.accounting{border-top:1px solid var(--ink);border-bottom:1px solid var(--line);padding:13px 0}.accounting strong{font-weight:650}.countrow{display:flex;justify-content:space-between;padding:6px 0;gap:20px}.countrow b{font-variant-numeric:tabular-nums;font-size:1.22rem}.countfoot{font-size:.8rem;margin-top:10px!important}.workspace{display:grid;grid-template-columns:235px minmax(0,1fr);border-top:1px solid var(--line);padding-top:26px;gap:32px}.sidebar label{display:block;font-size:.8rem;font-weight:600;margin:0 0 6px}.filters{display:grid;grid-template-columns:1fr;gap:12px}.filters select{width:100%;font-size:.88rem;min-width:0}.case-list{margin:15px 0 0;padding:0;list-style:none;display:grid;gap:1px}.case-button{border:0;border-radius:3px;width:100%;text-align:left;display:grid;grid-template-columns:36px 1fr;gap:7px;font-size:.8rem;min-height:48px;padding:8px}.case-button strong{font-size:.92rem}.case-button[aria-pressed=true]{background:var(--accent);color:white}.case-button .case-sub{display:block;font-size:.78rem;opacity:.86}.case-button:hover:not([aria-pressed=true]){background:var(--accent-soft)}.case-count{font-size:.8rem;color:var(--muted);margin:14px 0 0}.viewbar{display:flex;justify-content:space-between;align-items:center;gap:15px;margin-bottom:18px;flex-wrap:wrap}.viewbar h2{margin:0}.view-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.view-controls label{font-size:.82rem}.view-controls select{max-width:190px;font-size:.85rem}.comparison{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:25px}.comparison.single{grid-template-columns:minmax(0,1fr)}.case-detail{min-width:0;background:var(--surface);border-top:1px solid var(--accent);padding:24px 22px}.case-heading{display:flex;justify-content:space-between;align-items:start;gap:12px}.case-heading h2{font-size:2rem;margin:0 0 7px}.case-heading .muted{font-size:.8rem}.profile{min-height:45px;font-size:.93rem;margin-bottom:17px}.status-tag{font-size:.78rem;line-height:1.25;font-weight:650;border-radius:3px;padding:6px 8px;display:inline-block;max-width:135px}.status-good{color:var(--good);background:var(--good-bg)}.status-partial{color:var(--warn);background:var(--warn-bg)}.status-no{color:var(--ink);background:var(--quiet)}.verdicts{margin:0 0 22px}.verdicts>div{display:grid;grid-template-columns:1fr 1fr;gap:10px;border-top:1px solid var(--line);padding:10px 0;font-size:.87rem}.verdicts dt{color:var(--muted)}.verdicts dd{margin:0;font-weight:600}.verdicts dd small{display:block;font-weight:400;color:var(--muted);margin-top:2px}.explanation{font-size:.91rem;margin:0 0 20px;line-height:1.58}.evidence-section{border-top:1px solid var(--line);padding-top:18px;margin-top:24px}.evidence-section h3{margin-bottom:12px}.binding{margin:10px 0;font-size:.82rem}.binding span{display:block;color:var(--muted);margin-bottom:3px}.binding code{font-size:.76rem}.binding-note{font-size:.8rem;color:var(--muted);margin:8px 0}.request{margin:8px 0;border-top:1px solid #deddd8}.request summary{padding:12px 0;cursor:pointer;font-size:.84rem;list-style-position:inside}.request summary strong{font-weight:650}.request-meta{display:flex;gap:12px;flex-wrap:wrap;font-size:.78rem;color:var(--muted);margin:0 0 10px}.request .source-link{display:block;font-size:.8rem;margin:8px 0 13px}.request.error summary{color:var(--warn)}.gaps{padding-left:18px;font-size:.78rem;overflow-wrap:anywhere}.observer summary,.source-detail summary{font-size:.84rem;cursor:pointer;margin:15px 0 10px}.boundary{padding:23px 0;border-top:1px solid var(--line);margin-top:34px;color:var(--muted);font-size:.87rem;max-width:none}.footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--line);padding:22px 0 32px;font-size:.82rem}.footer-links{display:flex;gap:17px;flex-wrap:wrap}.empty{padding:20px 0;color:var(--muted)}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.compare-note{font-size:.82rem;color:var(--muted);margin-top:14px}.noscript{padding:25px;background:var(--warn-bg)}
@media(max-width:1100px){.shell{padding:0 25px}.workspace{grid-template-columns:190px 1fr;gap:20px}.case-detail{padding:20px 16px}.intro{gap:32px}.comparison{gap:16px}.verdicts>div{grid-template-columns:1fr}.profile{min-height:66px}}
@media(max-width:800px){.shell{padding:0 18px}.topbar{align-items:flex-start;gap:12px}.toplinks{gap:12px;flex-wrap:wrap;justify-content:flex-end}.toplinks .archive{order:3}.intro{grid-template-columns:1fr;gap:23px;padding:30px 0}.intro h1{max-width:25ch}.workspace{grid-template-columns:1fr;padding-top:20px}.filters{grid-template-columns:1fr 1fr}.case-list{grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}.case-button{display:block;text-align:center;min-height:43px;border:1px solid var(--line);padding:7px 3px}.case-button .case-text{display:none}.case-count{margin-top:8px}.comparison{gap:14px}.profile{min-height:65px}.case-detail{padding:18px 13px}.footer{flex-direction:column}.brand{font-size:.95rem}.toplinks{font-size:.8rem}}
@media(max-width:560px){.comparison{grid-template-columns:1fr}.case-detail{padding:22px 19px}.profile{min-height:0}.verdicts>div{grid-template-columns:1fr 1fr}.viewbar{align-items:flex-start}.view-controls{width:100%}.view-controls select{flex:1;max-width:none}.toplinks{gap:8px 12px}.brand{max-width:100px}.intro h1{font-size:2.35rem}.countrow{font-size:.92rem}.comparison .case-detail+ .case-detail{margin-top:5px}.case-heading h2{font-size:1.8rem}}
@media(prefers-reduced-motion:no-preference){button,a,select{transition:background-color .12s ease-out}.case-detail{animation:reveal .18s ease-out}@keyframes reveal{from{background-color:#ededf8}to{background-color:var(--surface)}}}
@media print{.topbar,.sidebar,.view-controls,.footer,.skip{display:none}.shell{padding:0}.intro{padding-top:0}.workspace{display:block}.comparison{grid-template-columns:1fr 1fr}.case-detail{break-inside:avoid}details{display:block}pre{max-height:none}.archive{color:var(--ink);background:none}.boundary{margin-top:10px}}
"""

INDEX = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AgentOps · archived evidence replay</title><link rel="stylesheet" href="styles.css"><script src="data.js" defer></script><script src="app.js" defer></script></head>
<body><a class="skip" href="#workspace">Skip to case evidence</a><div class="shell">
<header class="topbar"><span class="brand">Agent interoperability / research</span><nav class="toplinks" aria-label="Artifact navigation"><span class="archive">Archived replay · 27 Oct 2026</span><a href="presentation.html">Presentation</a><a href="README.md">Start guide</a></nav></header>
<section class="intro" aria-labelledby="title"><div><h1 id="title">When a task finishes,<br>what actually survived?</h1><p>Inspect the recorded protocol, task state and inventory effect across 18 native and bridge cases. A completed task is only one part of the success contract.</p></div><div class="accounting" aria-label="Recorded case accounting"><div class="countrow"><span>Strict successes <span class="muted">· all native</span></span><b id="count-success">—</b></div><div class="countrow"><span>Complete recorded non-successes</span><b id="count-no">—</b></div><div class="countrow"><span>Unknown or partial outcomes</span><b id="count-partial">—</b></div><p class="countfoot">Descriptive case accounting from one fixed development matrix. No population success-rate estimate.</p></div></section>
<noscript><p class="noscript">Enable JavaScript to compare the archived cases, or open <a href="source-report.json">the complete source report</a>.</p></noscript>
<main class="workspace" id="workspace"><aside class="sidebar" aria-label="Choose an archived case"><div class="filters"><div><label for="kind-filter">Route</label><select id="kind-filter"><option value="all">All routes</option><option value="native">Native only</option><option value="bridge">Bridge only</option></select></div><div><label for="outcome-filter">Outcome</label><select id="outcome-filter"><option value="all">All outcomes</option><option value="strict_success">Strict success</option><option value="observed_non_success">Complete non-success</option><option value="unknown_or_partial">Unknown / partial</option></select></div></div><p class="case-count" id="case-count"></p><ul class="case-list" id="case-list"></ul></aside><section aria-labelledby="case-view-title"><div class="viewbar"><h2 id="case-view-title">Case comparison</h2><div class="view-controls"><button type="button" id="compare-toggle" class="active" aria-pressed="true">Compare cases</button><label for="compare-case">With</label><select id="compare-case"></select></div></div><div class="comparison" id="case-view"></div><p class="compare-note" id="compare-note">Each column is a separate recorded attempt. Case controls change only the displayed evidence.</p><div class="sr-only" id="announcement" role="status" aria-live="polite"></div></section></main>
<p class="boundary">Evidence boundary: reproduced AgentOps confirmation fixture, deterministic model double, simulated SQLite inventory. This page makes no application request. These bounded observations do not establish whole-interface failure, a novel method, a qualified second domain, or a live-model benchmark. Synthetic protocol approval is not authenticated human approval.</p>
<footer class="footer"><span>Prepared for 31 October supervisor review · context updated 28 October 2026</span><nav class="footer-links" aria-label="Evidence sources"><a href="source-report.json">Full v10 report</a><a href="data.json">Portable data</a><a href="manifest.json">SHA-256 manifest</a></nav></footer></div></body></html>
"""

JS = r"""'use strict';
const D=window.SUPERVISOR_DATA;
const byId=Object.fromEntries(D.cases.map(c=>[c.case_id,c]));
const $=id=>document.getElementById(id);
const state={selected:'B6',comparison:'B7',compare:true,kind:'all',outcome:'all'};
const labels={strict_success:'Strict success',observed_non_success:'Complete non-success',unknown_or_partial:'Unknown / partial'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function add(parent,tag,text,cls){const n=el(tag,text,cls);parent.append(n);return n;}
function badge(c){return el('span',labels[c.outcome],`status-tag ${c.strict_success?'status-good':c.complete?'status-no':'status-partial'}`);}
function fmtHeader(r){return r.version_headers.length?r.version_headers.join(', '):'omitted';}
function shape(r){if(!r.message)return '';return r.message.parts.map(p=>Object.hasOwn(p,'data')?'DataPart':Object.hasOwn(p,'text')?'TextPart':'Other part').join(' + ');}
function explanation(c){const id=c.case_id;if(id==='B7')return 'The explicitly configured header exposed the public confirmation binding. A DataPart continuation completed the original task and produced one attributed effect. Process teardown was unclean and the terminal snapshot is missing: this remains partial.';if(id==='B5'||id==='B6')return 'The raw GetTask read omitted A2A-Version and received HTTP 200 with JSON-RPC −32009. The caller did not observe the confirmation binding, so no continuation was attempted. This is a partial observation, not a failed confirmation attempt.';if(id==='N10')return 'The raw DataPart continuation omitted A2A-Version and received a protocol-version error. The original task remained input_required and inventory remained down.';if(c.strict_success)return 'The recorded structured continuation retained the original task and context, completed the task and produced one attributed inventory effect. The whole-case checker found the required evidence complete.';if(id==='B1'||id==='B2')return 'The public confirmation binding was available. The continuation carried confirmation JSON as text, rather than as a DataPart. The original task remained input_required and the domain stayed unchanged.';if(id==='B3'||id==='B4')return 'The confirmation binding was not publicly observed. The recorded route used the permitted literal-text fallback. The original task remained input_required and the domain stayed unchanged.';return 'This recorded text continuation did not satisfy the confirmation contract. The original task remained input_required and the domain stayed unchanged. The conclusion is bounded to this fixed attempt.';}
function row(dl,label,value,note){const wrap=add(dl,'div');add(wrap,'dt',label);const dd=add(wrap,'dd',value);if(note)add(dd,'small',note);}
function binding(parent,label,value){const p=add(parent,'p',undefined,'binding');add(p,'span',label);add(p,'code',value===undefined?'Not observed publicly':typeof value==='string'?value:JSON.stringify(value));}
function section(parent,title){const n=add(parent,'section',undefined,'evidence-section');add(n,'h3',title);return n;}
function caseView(c){const s=c.service,a=el('article',undefined,'case-detail');a.setAttribute('aria-label',`${c.case_id} evidence`);const head=add(a,'div',undefined,'case-heading');const name=add(head,'div');add(name,'h2',c.case_id);add(name,'span',c.kind==='native'?'Native control':'Bridge deployment','muted');head.append(badge(c));add(a,'p',c.display_profile,'profile');const dl=add(a,'dl',undefined,'verdicts');row(dl,'Original task',s.task_completed?'Completed':'Not completed',s.final_state);row(dl,'Domain effect',s.effect.domain_changed?'Inventory operational':'Inventory down',`${s.effect.new_audit_rows} new audit ${s.effect.new_audit_rows===1?'row':'rows'} · ${s.effect.classification.replaceAll('_',' ')}`);row(dl,'Evidence',c.complete?'Complete':'Incomplete',c.complete?'Required boundaries captured':`${c.observation_gaps.length} recorded ${c.observation_gaps.length===1?'gap':'gaps'}`);row(dl,'Strict result',c.strict_success?'Pass':c.complete?'Non-success':'Unknown / partial');add(a,'p',explanation(c),'explanation');
 const pub=section(a,'What the caller could see');const b=c.client.public_bindings;binding(pub,'Public task ID',b.task_id);binding(pub,'Public context ID',b.context_id);binding(pub,'Public confirmation-call ID',b.confirmation_call_id);if(b.request_state!==undefined)binding(pub,'Opaque public request state',b.request_state);add(pub,'p',s.continuation_attempted?'Continuation attempted using the declared route.':'No continuation attempted. Only the initial send was captured.','binding-note');
 const wire=section(a,'Recorded wire requests');add(wire,'p','A2A-Version is read from the captured request headers. Expand a request to inspect its exact body.','binding-note');for(const r of c.requests){const det=add(wire,'details',undefined,`request${r.errors.length?' error':''}`);const sum=add(det,'summary');add(sum,'strong',`${r.sequence}. ${r.method}`);add(sum,'span',` · ${shape(r)||'read'} · ${fmtHeader(r)}`);const meta=add(det,'div',undefined,'request-meta');add(meta,'span',`A2A-Version: ${fmtHeader(r)}`);add(meta,'span',`HTTP ${r.http_status}`);add(meta,'span',r.errors.length?`JSON-RPC ${r.errors.map(e=>e.code).join(', ')}`:'No RPC error');if(r.role==='evaluator')add(det,'p','Evaluator final read: this observer request was not a caller continuation.','binding-note');if(r.errors.length)add(det,'pre',JSON.stringify(r.errors,null,2));add(det,'pre',JSON.stringify(r.body,null,2));const l=add(det,'a','Open captured request','source-link');l.href=r.request_copy;const l2=add(det,'a','Open captured exchange headers','source-link');l2.href=r.exchange_copy;}
 const evidence=section(a,'Evidence boundaries');if(c.observation_gaps.length){const ul=add(evidence,'ul',undefined,'gaps');for(const gap of c.observation_gaps)add(ul,'li',gap);}else add(evidence,'p','No whole-case observation gaps recorded.','binding-note');const obs=add(evidence,'details',undefined,'observer');add(obs,'summary','Evaluator observation · original task and context');add(obs,'p','These retained service values explain attribution. They are not a claim that the caller observed or used every value.','binding-note');binding(obs,'Original task ID',s.original.task_id);binding(obs,'Original context ID',s.original.context_id);const exact=add(evidence,'details',undefined,'source-detail');add(exact,'summary','Whole-case checker record');const original={...c};delete original.requests;delete original.display_profile;add(exact,'pre',JSON.stringify(original,null,2));return a;}
function render(){const visible=D.cases.filter(c=>(state.kind==='all'||c.kind===state.kind)&&(state.outcome==='all'||c.outcome===state.outcome));if(visible.length&&!visible.some(c=>c.case_id===state.selected))state.selected=visible[0].case_id;$('case-count').textContent=`${visible.length} of ${D.cases.length} cases shown`;$('case-list').replaceChildren();for(const c of visible){const li=add($('case-list'),'li');const btn=add(li,'button',undefined,'case-button');btn.type='button';btn.setAttribute('aria-pressed',String(state.selected===c.case_id));btn.setAttribute('aria-label',`${c.case_id}, ${c.display_profile}, ${labels[c.outcome]}`);add(btn,'strong',c.case_id);const txt=add(btn,'span',undefined,'case-text');add(txt,'span',c.display_profile);add(txt,'span',labels[c.outcome],'case-sub');btn.onclick=()=>{state.selected=c.case_id;render();const active=document.querySelector('.case-button[aria-pressed=true]');if(active)active.focus();};}
 $('case-view').classList.toggle('single',!state.compare);$('case-view').replaceChildren();if(!visible.length){add($('case-view'),'p','No cases match both filters. Choose another route or outcome.','empty');}else{$('case-view').append(caseView(byId[state.selected]));if(state.compare)$('case-view').append(caseView(byId[state.comparison]));}$('compare-toggle').setAttribute('aria-pressed',String(state.compare));$('compare-toggle').classList.toggle('active',state.compare);$('compare-case').disabled=!state.compare;$('case-view-title').textContent=state.compare?'Case comparison':'Case evidence';$('compare-note').textContent=state.compare?'Each column is a separate recorded attempt. The comparison selector includes all 18 cases.':'Case controls change only the displayed evidence.';$('announcement').textContent=visible.length?`Showing ${state.selected}${state.compare?' compared with '+state.comparison:''}`:'No matching cases';}
for(const c of D.cases){const o=add($('compare-case'),'option',`${c.case_id} · ${c.display_profile}`);o.value=c.case_id;}$('compare-case').value=state.comparison;$('compare-case').onchange=e=>{state.comparison=e.target.value;render();};$('compare-toggle').onclick=()=>{state.compare=!state.compare;render();};$('kind-filter').onchange=e=>{state.kind=e.target.value;render();};$('outcome-filter').onchange=e=>{state.outcome=e.target.value;render();};$('count-success').textContent=D.counts.strict_success;$('count-no').textContent=D.counts.observed_non_success;$('count-partial').textContent=D.counts.unknown_or_partial;
const params=new URLSearchParams(location.search);if(byId[params.get('case')])state.selected=params.get('case');if(byId[params.get('with')])state.comparison=params.get('with');$('compare-case').value=state.comparison;render();
"""

SLIDE_CSS = r"""
body.deck{background:var(--paper)}.deck-header{max-width:1400px;margin:auto;padding:18px 34px;display:flex;justify-content:space-between;align-items:center;gap:18px;border-bottom:1px solid var(--line);font-size:.83rem}.deck-main{max-width:1360px;margin:auto}.slide{min-height:calc(100vh - 151px);padding:45px 58px 30px;display:none}.slide.current{display:block}.slide h1{font-size:clamp(2.3rem,4.1vw,4rem);max-width:24ch;margin-bottom:24px}.slide h2{font-size:clamp(2rem,3.2vw,3rem);max-width:31ch;margin-bottom:24px}.slide p{font-size:1.12rem}.slide .lead{font-size:1.35rem;line-height:1.5;max-width:61ch}.slide .small{font-size:.88rem}.slide .muted{color:var(--muted)}.title-layout{display:grid;grid-template-columns:1.2fr .8fr;gap:70px;align-items:center;min-height:440px}.title-layout h1{font-size:clamp(2.6rem,4.7vw,4.6rem)}.registered{border-top:1px solid var(--line);padding-top:17px;font-size:.87rem!important;line-height:1.55;max-width:none}.meeting-note{border-top:2px solid var(--accent);padding-top:18px}.meeting-note p{font-size:1rem}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:55px}.two-col>div{min-width:0}.plain-list{margin:0;padding-left:23px;font-size:1.14rem;line-height:1.6}.plain-list li{padding:8px 0}.path-diagram{margin:28px 0 30px;display:grid;grid-template-columns:1fr 50px 1fr 50px 1fr;align-items:center;gap:0}.path-step{padding:24px 18px;background:var(--surface);border:1px solid var(--line);min-height:150px}.path-step h3{font-family:Segoe UI,Arial,sans-serif;font-size:1.06rem;font-weight:650;line-height:1.4;margin-bottom:10px}.path-step p{font-size:.94rem;margin:0}.path-arrow{width:36px;height:30px;justify-self:center;color:var(--accent)}.path-arrow path{fill:none;stroke:currentColor;stroke-width:2}.route-band{display:grid;grid-template-columns:160px 1fr;gap:25px;border-top:1px solid var(--line);padding:14px 0;font-size:1rem}.route-band strong{font-weight:650}.contract{counter-reset:contract;list-style:none;margin:18px 0 26px;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:0 40px}.contract li{counter-increment:contract;padding:18px 0 18px 38px;border-top:1px solid var(--line);position:relative;font-size:1.1rem}.contract li:before{content:counter(contract);position:absolute;left:0;color:var(--accent);font-weight:600}.callout{background:var(--accent-soft);padding:18px 22px;font-size:1.08rem!important;margin:22px 0}.matrix{width:100%;border-collapse:collapse;font-size:.88rem;margin:12px 0 18px;font-variant-numeric:tabular-nums}.matrix th{text-align:left;font-weight:600;border-bottom:2px solid var(--ink);padding:10px 8px}.matrix td{border-bottom:1px solid var(--line);padding:9px 8px;vertical-align:top}.matrix td:first-child{white-space:nowrap}.matrix .status-tag{font-size:.78rem;max-width:none}.matrix caption{text-align:left;font-size:.84rem;color:var(--muted);padding:0 0 13px}.matrix-summary{display:flex;gap:20px;flex-wrap:wrap;font-size:1rem!important}.proof-pair{display:grid;grid-template-columns:1fr 1fr;gap:45px;margin:26px 0}.proof-pair .proof{border-top:2px solid var(--good);padding-top:17px}.proof-pair .gap{border-top:2px solid var(--warn);padding-top:17px}.proof-pair h3{font-size:1.6rem}.proof-pair p{font-size:1rem}.large-code{font-family:Consolas,monospace;font-size:1.1rem!important;background:var(--surface);padding:18px 22px;overflow-wrap:anywhere}.plan-table{margin-top:18px}.plan-table th{width:140px}.plan-table td,.plan-table th{padding:15px 10px;font-size:1rem}.decision-list{font-size:1.08rem;padding-left:22px;line-height:1.6}.decision-list li{padding:8px 0}.deck-footer{max-width:1400px;margin:auto;padding:15px 34px 20px;border-top:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:20px}.deck-controls{display:flex;gap:8px;align-items:center}.deck-controls button{font-size:.88rem}.slide-counter{font-variant-numeric:tabular-nums;min-width:50px;text-align:center;font-size:.88rem}.deck-footer .small{margin:0}.deck-progress{height:3px;background:var(--accent);width:12.5%;position:fixed;bottom:0;left:0}.deck .notes{display:none;margin-top:25px;border-top:1px dashed var(--line);padding-top:15px;font-size:.95rem}.deck.show-notes .notes{display:block}.deck:fullscreen{overflow:auto}.deck:fullscreen .deck-header{max-width:none}.deck:fullscreen .deck-main{max-width:1500px}.slide[data-slide='4'] h2{margin-bottom:16px}.slide[data-slide='4'] .matrix{font-size:.81rem}.slide[data-slide='4'] .matrix td{padding:7px 8px}
@media(max-width:900px){.slide{padding:30px 28px;min-height:calc(100vh - 170px)}.title-layout{gap:35px;min-height:350px}.two-col{gap:28px}.path-step{padding:16px 12px}.path-diagram{grid-template-columns:1fr 32px 1fr 32px 1fr}.path-arrow{width:25px}.proof-pair{gap:24px}.deck-header,.deck-footer{padding-left:22px;padding-right:22px}.deck-footer{flex-wrap:wrap;gap:10px}.slide p{font-size:1rem}.slide .lead{font-size:1.15rem}.plain-list{font-size:1rem}.contract li{font-size:1rem}.matrix{font-size:.79rem}}
@media(max-width:600px){.slide{padding:28px 20px}.title-layout,.two-col,.proof-pair{grid-template-columns:1fr;gap:23px;min-height:0}.slide h1{font-size:2.6rem}.slide h2{font-size:2.05rem}.deck-header{align-items:flex-start;flex-wrap:wrap;gap:8px}.deck-header .archive{font-size:.78rem}.contract{grid-template-columns:1fr}.path-diagram{grid-template-columns:1fr;gap:10px}.path-step{min-height:0}.path-arrow{transform:rotate(90deg)}.route-band{grid-template-columns:1fr;gap:5px}.table-wrap{overflow:auto}.matrix{min-width:630px}.plan-table{min-width:0}.plan-table th{width:84px}.plan-table th,.plan-table td{font-size:.9rem;padding:10px 6px}.deck-controls{flex-wrap:wrap}.meeting-note{margin-top:10px}.deck-header .brand{max-width:none}}
@media print{body.deck{background:white}.deck-header,.deck-footer,.deck-progress{display:none}.slide,.slide.current{display:block;min-height:0;padding:20px;break-after:page}.slide h2{font-size:2rem}.slide h1{font-size:2.5rem}.title-layout{min-height:0}.notes{display:none!important}.slide .matrix{font-size:.8rem}.table-wrap{overflow:visible}}
"""


def arrow() -> str:
    return '<svg class="path-arrow" viewBox="0 0 36 30" aria-hidden="true"><path d="M2 15H31M23 7l8 8-8 8"/></svg>'


def presentation() -> str:
    return r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Supervisor review · Agent interoperability</title><link rel="stylesheet" href="styles.css"><link rel="stylesheet" href="presentation.css"><script src="data.js" defer></script><script src="presentation.js" defer></script></head><body class="deck"><a href="#slides" class="skip">Skip to slides</a><header class="deck-header"><span class="brand">Agent interoperability / supervisor review</span><span class="archive">Recorded evidence · 27 Oct 2026</span><a href="index.html">Open case replay</a></header><main id="slides" class="deck-main">
<section class="slide current" data-slide="1" aria-label="1. Problem"><div class="title-layout"><div><h1>A completed message<br>is not a completed job.</h1><p class="lead">Measuring what survives when an agent crosses a protocol boundary.</p></div><div class="meeting-note"><h2>Work for review</h2><p><strong>31 October 2026</strong><br>Development evidence, a portable replay and the decisions needed to finish the study.</p><p class="small muted">Prepared 28 October. Browser presentation with eight slides; use the arrow keys.</p></div></div><p class="registered">Registered project: ''' + TITLE + r'''</p><p class="notes">Opening, about 45 seconds: explain that the implemented work checks continuation identity, origin task state, domain effect and capture boundaries. The study's broader method contribution remains open.</p></section>
<section class="slide" data-slide="2" aria-label="2. System path"><h2>Follow the request all the way to the effect.</h2><p class="lead">Fixed task: “Restart inventory.” The service asks for a structured confirmation before the guarded action.</p><div class="path-diagram"><div class="path-step"><h3>Caller</h3><p>Native SDK or MCP-facing client.<br>Only permitted public bindings.</p></div>''' + arrow() + r'''<div class="path-step"><h3>Protocol boundary</h3><p>Native A2A path, or MCP → A2A bridge.<br>Header, part shape and identity.</p></div>''' + arrow() + r'''<div class="path-step"><h3>AgentOps fixture</h3><p>Original task → confirmation.<br>SQLite inventory + audit effect.</p></div></div><div class="route-band"><strong>Native controls</strong><span>11 profile / representation cases establish matched request behavior.</span></div><div class="route-band"><strong>Bridge controls</strong><span>7 public-route and deployment cases retain the same bounded task.</span></div><p class="small muted">Reproduced original confirmation fixture with an upstream deterministic model double. Simulated domain effect; no live-model study.</p><p class="notes">About 60 seconds: identify the observer as a separate evidence collector. Its private IDs are never a permitted source for a caller continuation. The simulator's inventory update is real recorded SQLite state, but not a production restart.</p></section>
<section class="slide" data-slide="3" aria-label="3. Success contract"><h2>Success is a contract,<br>not a line of final text.</h2><ol class="contract"><li>Retain the original task and context.</li><li>Use a legal, publicly supplied continuation.</li><li>Reach the required completed origin state.</li><li>Produce exactly one attributed guarded effect.</li><li>Avoid early or unrelated domain changes.</li><li>Match the declared profile, with complete clean process evidence.</li></ol><p class="callout">The replay reports <strong>task completion</strong>, <strong>domain effect</strong>, <strong>evidence completeness</strong> and <strong>strict result</strong> separately.</p><p class="small muted">Synthetic A2A approval is not authenticated human approval. Unknown evidence is retained as unknown.</p><p class="notes">About 45 seconds: this contract prevents a terminal status or a reassuring response from replacing effect verification. The final clause is why B7 cannot be counted as strict success.</p></section>
<section class="slide" data-slide="4" aria-label="4. Matrix findings"><h2>The fixed matrix contains 18 executed cases.</h2><div class="table-wrap"><table class="matrix"><caption>27 October v10 evidence. Group status: failed. All planned cases accounted for; evidence is incomplete in three.</caption><thead><tr><th>Cases</th><th>Recorded continuation / route</th><th>Task / effect</th><th>Whole-case outcome</th></tr></thead><tbody id="slide-matrix"></tbody></table></div><p class="matrix-summary" id="slide-counts"></p><p class="small muted">Counts describe this development matrix. They do not estimate general success rates, prove whole-interface non-support, or qualify a second domain.</p><p class="notes">About 75 seconds: N3/N6/N9/N11 are the four strict native successes. B1–B4 are complete recorded non-successes. B5/B6 never attempted continuation after the public read failed. B7 reached the effect but remains partial.</p></section>
<section class="slide" data-slide="5" aria-label="5. B7 limitation"><h2>B7 reached the effect.<br>The evidence still stops short.</h2><p class="lead">The public factory was explicitly configured to send <code>A2A-Version: 1.0</code>. That intervention is distinct from the stock raw route.</p><div class="proof-pair"><div class="proof"><h3>What was observed</h3><ul class="plain-list"><li>Public confirmation binding became visible.</li><li>A DataPart continued the original task.</li><li>Task completed; inventory operational.</li><li>Exactly one attributed audit effect.</li></ul></div><div class="gap"><h3>What prevents a strict pass</h3><ul class="plain-list"><li>Python needed SIGTERM after the service routine stopped.</li><li>Required terminal snapshot is missing.</li><li>Cleanup errors remain in the record.</li><li>The cause of the surviving process is unknown.</li></ul></div></div><p class="callout">Whole-case result: <strong>unknown / partial</strong>. Archived-state consistency cannot recreate a missing historical boundary.</p><p class="notes">About 75 seconds: open the replay to B6 versus B7 if useful. B6 omitted the raw-read header and stopped without a confirmation binding. Do not describe B7 as a clean bridge success or claim that the later diagnostic is already a repair.</p></section>
<section class="slide" data-slide="6" aria-label="6. Built artifact"><h2>There is concrete work to inspect and reproduce.</h2><div class="two-col"><div><h3>Built and retained</h3><ul class="plain-list"><li>Native and bridge request controls.</li><li>Task / effect / process evidence checkers.</li><li>18 attempted cases, including partial captures.</li><li>Portable case replay and this presentation.</li></ul></div><div><h3>Traceable evidence</h3><ul class="plain-list"><li>Parent checker records 2,371 exported files checked.</li><li>Local request bodies and header captures.</li><li>Exact source report plus SHA-256 manifest.</li><li>Deterministic rebuild and package check.</li></ul></div></div><p class="large-code">python scripts/build_supervisor_demo_v1.py --check</p><p><a href="index.html?case=B6&amp;with=B7">Open B6 / B7 replay</a> · <a href="source-report.json">Source report</a> · <a href="manifest.json">Manifest</a></p><p class="small muted">The package check verifies these files and input hashes. It is not a fresh application run or independent scientific reproduction.</p><p class="notes">About 60 seconds: demonstrate the four separate result fields, then expand an actual request. The replay is offline and can be copied as a folder. The parent report's 2,371-file audit predates this presentation build.</p></section>
<section class="slide" data-slide="7" aria-label="7. Three-day plan"><h2>Use the next three days to make every claim reviewable.</h2><table class="matrix plan-table"><tbody><tr><th>28 Oct</th><td>Finish replay, presentation and manuscript in parallel. Prepare the bounded shutdown diagnostic; execute only after its prospective checks pass.</td></tr><tr><th>29 Oct</th><td>Inspect available diagnostic evidence. Resolve the strongest contribution objection and write a concrete method / fair-comparator statement.</td></tr><tr><th>30 Oct</th><td>Verify package figures and links, reproduce the demonstration from a clean launch, and rehearse the eight-minute explanation.</td></tr><tr><th>31 Oct</th><td>Supervisor review: record actual feedback, the reviewed versions and explicit contribution / validity decisions.</td></tr></tbody></table><p class="callout">Working completion date: <strong>1 November</strong>, interpreting this week as ending Sunday. Finish against the approved requirements; report any missing gate honestly.</p><p class="small muted">This schedule increases urgency. It does not create scientific results or approval.</p><p class="notes">About 45 seconds: these are planned outputs, not completed experiments. New diagnostic attempts must remain separately versioned and cannot overwrite v10. The three-day meeting deadline is firm; November 1 is the stated week-end assumption.</p></section>
<section class="slide" data-slide="8" aria-label="8. Supervisor decisions"><h2>The review needs decisions on contribution and validity.</h2><div class="two-col"><div><h3>Decisions to record</h3><ol class="decision-list"><li>What concrete extra method step and fair discriminator would establish the intended contribution?</li><li>Are the domain tasks, trajectories and grading contracts substantive and valid?</li><li>Which changes are essential before submission, and is any alternative contribution route explicitly approved?</li></ol></div><div><h3>Requirements still open</h3><p>A distinct method; two qualified domains; independently authored development, calibration and held-out tasks; two actual human task reviewers; frozen evaluation; independent reproduction; accountable manuscript review.</p><p class="callout">CP1 passed; CP2 in progress.<br><strong>5% verified deliverable credit.</strong></p><p class="small muted">This measures passed gates, not the amount of code written. A polished review package does not complete the benchmark or paper.</p></div></div><p class="notes">About 60 seconds: ask for exact, recorded feedback on these decisions. A presentation is not approval. Preserve the registered project and distinguish its intended method route from a proposed systems/artifact route.</p></section>
</main><footer class="deck-footer"><p class="small muted" id="slide-name">Problem · archived development evidence</p><div class="deck-controls"><button type="button" id="notes-toggle" aria-pressed="false">Speaker notes</button><button type="button" id="fullscreen">Fullscreen</button><button type="button" id="prev-slide" aria-label="Previous slide">Previous</button><span class="slide-counter" id="slide-counter" aria-live="polite">1 / 8</span><button type="button" class="primary" id="next-slide" aria-label="Next slide">Next</button></div></footer><div class="deck-progress" id="deck-progress" aria-hidden="true"></div><noscript><p class="noscript">Enable JavaScript for navigation. The presentation's complete text is also available in presentation.html.</p></noscript></body></html>'''


SLIDE_JS = r"""'use strict';
const data=window.SUPERVISOR_DATA, cases=Object.fromEntries(data.cases.map(c=>[c.case_id,c]));
const groups=[['N1, N2, N4, N5, N7, N8',['N1','N2','N4','N5','N7','N8'],'Literal or JSON text'],['N3, N6, N9',['N3','N6','N9'],'Native DataPart'],['N10',['N10'],'Raw DataPart; version header omitted'],['N11',['N11'],'Raw DataPart; version header 1.0'],['B1–B4',['B1','B2','B3','B4'],'Public typed routes; text continuation'],['B5, B6',['B5','B6'],'Raw read omitted header; no continuation'],['B7',['B7'],'Configured version header; DataPart']];
for(const [name,ids,route] of groups){const c=cases[ids[0]];if(!ids.every(id=>cases[id].outcome===c.outcome&&cases[id].task_completed===c.task_completed))throw Error('Slide grouping no longer matches source');const tr=document.createElement('tr');for(const text of [name,route,c.task_completed?'Completed / one effect':'input_required / unchanged']){const td=document.createElement('td');td.textContent=text;tr.append(td);}const td=document.createElement('td'),span=document.createElement('span');span.className='status-tag '+(c.strict_success?'status-good':c.complete?'status-no':'status-partial');span.textContent=c.strict_success?'Strict success':c.complete?'Complete non-success':'Unknown / partial';td.append(span);tr.append(td);document.getElementById('slide-matrix').append(tr);}
document.getElementById('slide-counts').textContent=`${data.counts.strict_success} strict successes · ${data.counts.observed_non_success} complete recorded non-successes · ${data.counts.unknown_or_partial} partial cases · 0 skipped / unexecuted`;
const slides=[...document.querySelectorAll('.slide')];let current=0;
const names=['Problem','System path','Success contract','Matrix findings','B7 limitation','Built artifact','Three-day plan','Supervisor decisions'];
function show(i){current=Math.max(0,Math.min(slides.length-1,i));slides.forEach((s,n)=>{s.classList.toggle('current',n===current);s.setAttribute('aria-hidden',String(n!==current));});document.getElementById('prev-slide').disabled=current===0;document.getElementById('next-slide').disabled=current===slides.length-1;document.getElementById('slide-counter').textContent=`${current+1} / ${slides.length}`;document.getElementById('slide-name').textContent=names[current]+' · archived development evidence';document.getElementById('deck-progress').style.width=`${100*(current+1)/slides.length}%`;history.replaceState(null,'',`#slide-${current+1}`);window.scrollTo(0,0);}
document.getElementById('prev-slide').onclick=()=>show(current-1);document.getElementById('next-slide').onclick=()=>show(current+1);document.getElementById('notes-toggle').onclick=e=>{const active=document.body.classList.toggle('show-notes');e.currentTarget.setAttribute('aria-pressed',String(active));};document.getElementById('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.body.requestFullscreen();}catch{document.getElementById('fullscreen').textContent='Use browser F11';}};document.addEventListener('fullscreenchange',()=>{document.getElementById('fullscreen').textContent=document.fullscreenElement?'Exit fullscreen':'Fullscreen';});document.addEventListener('keydown',e=>{if(e.target.closest('input,select,textarea'))return;if(e.key===' '&&e.target.closest('button,a'))return;if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();show(current+1);}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();show(current-1);}if(e.key==='Home'){e.preventDefault();show(0);}if(e.key==='End'){e.preventDefault();show(slides.length-1);}});const initial=Number(location.hash.replace('#slide-',''))-1;show(Number.isInteger(initial)&&initial>=0?initial:0);
"""

README = """# Supervisor review package · browser format

Open **index.html** in a current browser for the archived case replay. Open
**presentation.html** for the eight-slide presentation. Keep the entire folder
together when copying it to another computer. No server, install, network,
application run or model call is needed. JavaScript must be enabled.

## Suggested eight-minute walkthrough

1. Present slides 1–4: problem, path, strict success contract, fixed matrix.
2. On slide 5, open the replay's default B6 / B7 comparison. Read its four
   outcome fields separately. Expand B6's raw GetTask (sequence 5) and B7's
   raw GetTask (sequence 6) / DataPart SendMessage (sequence 7).
3. Select N11 as the comparison for a strict native baseline. Use route and
   outcome filters to inspect the remaining cases; filters affect the left
   selector, while the comparison selector retains all 18 cases.
4. Return to slides 6–8 for the artifact, schedule and supervisor decisions.

Presentation: Left/Right or PageUp/PageDown navigate; Home/End jump to first/last.
Space advances when focus is not on a control. Use the Fullscreen button (or
browser F11), and Escape to exit. Speaker notes toggles the editable notes.
The deck adapts to a narrow display; a desktop or projector is recommended.
Browser print includes all eight slides. This is HTML, not a PowerPoint file.

## Dates and evidence limits

Application experiment: **27 October 2026**. Package context: **28 October**.
Supervisor review: **31 October**. Working completion: **1 November**, assuming
the week ends Sunday. The unchanged registered title appears on slide 1.

This is archived replay, not a live demonstration. It uses a reproduced
AgentOps confirmation fixture, a deterministic model double and simulated
SQLite inventory. Synthetic protocol approval is not authenticated human
approval. It establishes neither a novel method nor a qualified second domain,
and the counts are not a population performance estimate.

The v10 report accounts for 18 cases: 4 strict native successes, 11 complete
recorded non-successes and 3 partial cases. B5/B6 attempted no continuation
after the public read failed. B7 reached the effect but lacks clean teardown
and its required terminal snapshot, so it remains partial. Task completion,
effect, evidence completeness and strict result are separate fields.

## Rebuild and verify

From the repository root, with Python 3.10 or later:

```text
python scripts/build_supervisor_demo_v1.py
python scripts/build_supervisor_demo_v1.py --check
node --check demo/supervisor-v1/app.js
node --check demo/supervisor-v1/presentation.js
```

The builder reads retained reports and wire captures and writes only this
package. It does not change any experiment or research outcome. Rebuilding
replaces only its generated files. `--check` verifies package/source hashes,
18-case accounting, exact checker fields, captured headers and local links.
It is not a rerun of the scientific checker or independent reproduction.
The manifest lists every source input, copied evidence path and SHA-256 hash;
its output hashes exclude the manifest itself. No fresh 2,371-file audit is
claimed by this presentation builder.

`data.json` is portable structured data; `data.js` provides the same data without
fetch so local-file browsers can run it. `source-report.json` is the exact
parent report. `gap-inspection.json` is the retained post-capture inspection.
`evidence/` contains the exact request body and exchange metadata for each RPC
shown. Full source responses, domain snapshots and process evidence remain in
the repository paths named by the report and manifest.

To edit the presentation or interface, change the template constants in
`scripts/build_supervisor_demo_v1.py`, rebuild, and repeat verification. Direct
edits to generated files are overwritten on the next build.
"""


def build() -> None:
    outputs: dict[str, bytes] = {}
    inputs: list[dict] = []

    def read(source: str, copy: str | None = None) -> bytes:
        raw = (ROOT / source).read_bytes()
        inputs.append({"path": source, "bytes": len(raw), "sha256": digest(raw), "copy": copy})
        if copy:
            outputs[copy] = raw
        return raw

    report = json.loads(read(REPORT, "source-report.json"))
    gaps = json.loads(read(GAPS, "gap-inspection.json"))
    read("scripts/build_supervisor_demo_v1.py")
    if report["schema_version"] != "agentops-bridge-group-check/1" or report["valid"] is not True:
        raise ValueError("Expected the verified v10 group report")
    if list(report["cases"]) != ORDER or report["counts"] != {"executed": 18, "skipped": 0, "unexecuted": 0}:
        raise ValueError("Case allocation changed; update the presentation explicitly")
    if report["files_checked"] != 2371 or report["all_evidence_complete"] is not False:
        raise ValueError("Source claim changed")
    case_data = []
    for case_id in ORDER:
        case = json.loads(json.dumps(report["cases"][case_id]))
        case["display_profile"] = BRIDGES.get(case_id) or f"{case['client']['profile']} / {case['client']['representation']}"
        requests = []
        for rpc in case["service"]["rpc_outcomes"]:
            seq = rpc["sequence"]
            source_dir = f"{RAW}/bridge-v1-{case_id}/service/wire/{seq:06d}"
            copy_dir = f"evidence/{case_id}/{seq:06d}"
            exchange = json.loads(read(f"{source_dir}/exchange.json", f"{copy_dir}/exchange.json"))
            body = json.loads(read(f"{source_dir}/request.body.bin", f"{copy_dir}/request.json"))
            if body.get("method") != rpc["method"] or body.get("id") != rpc["id"]:
                raise ValueError(f"RPC attribution mismatch: {case_id} / {seq}")
            if exchange["response_status"] != rpc["http_status"]:
                raise ValueError(f"HTTP status mismatch: {case_id} / {seq}")
            headers = [v for k, v in exchange["request_headers"] if k.lower() == "a2a-version"]
            send = next((s for s in case["service"]["send_profiles"] if s["sequence"] == seq), None)
            if send and (headers != send["version_headers"] or body.get("params", {}).get("message") != send["message"]):
                raise ValueError(f"Send profile mismatch: {case_id} / {seq}")
            requests.append({**rpc, "version_headers": headers, "body": body,
                             "message": send["message"] if send else None,
                             "role": "evaluator" if rpc["id"] == "evaluator-final" else "caller",
                             "request_copy": f"{copy_dir}/request.json", "exchange_copy": f"{copy_dir}/exchange.json"})
        case["requests"] = requests
        case_data.append(case)
    counts = {outcome: sum(c["outcome"] == outcome for c in case_data) for outcome in ["strict_success", "observed_non_success", "unknown_or_partial"]}
    if list(counts.values()) != [4, 11, 3]:
        raise ValueError("Outcome accounting changed")
    for case_id in ["B5", "B6", "B7"]:
        raw = next(c for c in case_data if c["case_id"] == case_id)
        for request in raw["requests"]:
            matched = next(r for r in gaps["cases"][case_id]["requests"] if r["sequence"] == request["sequence"])
            if request["version_headers"] != matched["version_headers"]:
                raise ValueError("Post-capture header inspection mismatch")
    data = {"schema_version": "supervisor-replay/1", "registered_title": TITLE,
            "experiment_date": "2026-10-27", "context_date": "2026-10-28",
            "supervisor_review_date": "2026-10-31", "working_completion_date": "2026-11-01",
            "mode": "archived_replay", "source_report": REPORT,
            "source_report_sha256": inputs[0]["sha256"], "counts": counts,
            "group_counts": report["counts"], "recorded_group_status": report["recorded_group_status"],
            "files_checked_by_source_report": report["files_checked"], "cases": case_data}
    outputs.update({"index.html": INDEX.encode(), "styles.css": CSS.encode(), "app.js": JS.encode(),
                    "data.json": encoded(data), "data.js": b"window.SUPERVISOR_DATA = " + encoded(data).rstrip() + b";\n",
                    "presentation.html": presentation().encode(), "presentation.css": SLIDE_CSS.encode(),
                    "presentation.js": SLIDE_JS.encode(), "README.md": README.encode()})
    manifest = {"schema_version": "supervisor-replay-manifest/1", "context_date": "2026-10-28",
                "build_command": "python scripts/build_supervisor_demo_v1.py",
                "fresh_application_run": False, "scientific_outcomes_changed": False,
                "inputs": inputs, "outputs": [{"path": path, "bytes": len(raw), "sha256": digest(raw)} for path, raw in sorted(outputs.items())]}
    outputs["manifest.json"] = encoded(manifest)
    # Strictly constrain all writes to this dedicated package, without deletion.
    target = OUT.resolve()
    target.relative_to((ROOT / "demo").resolve())
    for name, raw in outputs.items():
        path = (OUT / name).resolve()
        path.relative_to(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    check()


def check() -> None:
    manifest = json.loads((OUT / "manifest.json").read_bytes())
    for item in manifest["inputs"]:
        raw = (ROOT / item["path"]).read_bytes()
        if digest(raw) != item["sha256"] or len(raw) != item["bytes"]:
            raise ValueError(f"Source changed: {item['path']}; rebuild explicitly")
        if item.get("copy") and raw != (OUT / item["copy"]).read_bytes():
            raise ValueError(f"Source copy differs: {item['copy']}")
    for item in manifest["outputs"]:
        raw = (OUT / item["path"]).read_bytes()
        if digest(raw) != item["sha256"] or len(raw) != item["bytes"]:
            raise ValueError(f"Generated output changed: {item['path']}")
    report = json.loads((OUT / "source-report.json").read_bytes())
    data = json.loads((OUT / "data.json").read_bytes())
    if [c["case_id"] for c in data["cases"]] != ORDER:
        raise ValueError("Demo must retain all 18 cases in order")
    for case in data["cases"]:
        original = {k: v for k, v in case.items() if k not in {"requests", "display_profile"}}
        if original != report["cases"][case["case_id"]]:
            raise ValueError("Demo differs from original checker outcome")
        for request in case["requests"]:
            exchange = json.loads((OUT / request["exchange_copy"]).read_bytes())
            if request["version_headers"] != [v for k, v in exchange["request_headers"] if k.lower() == "a2a-version"]:
                raise ValueError("Demo header differs from captured exchange")
    for name in ["index.html", "presentation.html"]:
        text = (OUT / name).read_text(encoding="utf-8")
        for link in re.findall(r'(?:href|src)="([^"]+)"', text):
            if link.startswith("#"):
                continue
            if "://" in link or link.startswith("//"):
                raise ValueError("The package must not depend on a network URL")
            if not (OUT / link.split("?")[0].split("#")[0]).is_file():
                raise ValueError(f"Broken local link: {name} -> {link}")
    if (OUT / "data.js").read_bytes() != b"window.SUPERVISOR_DATA = " + encoded(data).rstrip() + b";\n":
        raise ValueError("Portable JSON and JavaScript disagree")
    print(json.dumps({"status": "passed", "cases": 18, "counts": data["counts"],
                      "input_files": len(manifest["inputs"]), "output_files": len(manifest["outputs"]) + 1,
                      "fresh_application_run": False, "output": str(OUT)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify existing package and source hashes without writing")
    args = parser.parse_args()
    check() if args.check else build()
