const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const {webcrypto}=require('node:crypto');
const code=fs.readFileSync(require('node:path').join(__dirname,'../app/static/register.js'),'utf8');
class Element {
  constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.listeners={};this.value='';this.textContent='';}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
  get firstChild(){return this.children[0];}
  addEventListener(name,fn){this.listeners[name]=fn;}
  querySelectorAll(selector){const tags=selector.split(',');return this.children.flatMap(c=>[...(tags.includes(c.tagName)?[c]:[]),...c.querySelectorAll(selector)]);}
}
function harness(){
  const nodes=new Map(),requests=[];let fail=false;
  const task=n=>({id:'TASK-'+n,task_name:'Task '+n,status:'대기',status_detail:'Original',latest_instruction:'No dispatch',next_action:'Wait',blocker:'Needs user',completion_criteria:'Verified only',last_verified_at:'2026-01-01T00:00:00Z',verification_basis:{type:'synthetic'},priority_proposal:n===0?'최우선(사용자 확정)':''});
  const snapshot={source:{library_id:'libfile_synthetic',digest:'a'.repeat(64),version:5,imported_at:'2026-01-01T00:00:00Z'},document:{version:1,updated_at:'2026-01-01T00:00:00Z',status_definitions:{'대기':'wait','정지':'paused'},tasks:[task(0),task(1)]},proposals:[],events:[],warnings:[]};
  const $=s=>{if(!nodes.has(s))nodes.set(s,new Element('div'));return nodes.get(s);};
  class Data {constructor(form){this.form=form;}*[Symbol.iterator](){for(const e of this.form.querySelectorAll('input,textarea,select'))if(e.name&&!e.disabled)yield[e.name,e.value];}}
  const context=vm.createContext({document:{querySelector:$,createElement:t=>new Element(t),visibilityState:'visible'},Date,JSON,Set,FormData:Data,crypto:webcrypto,setTimeout:()=>0,
    fetch:async(url,options)=>{requests.push({url,options});if(options?.method!=='POST'&&fail)throw Error('injected GET failure');return{ok:true,json:async()=>options?.method==='POST'?{proposal_id:'synthetic-proposal',state:'pending',library_updated:false}:structuredClone(snapshot)};}});
  vm.runInContext(code.slice(0,code.indexOf("$('#status-filter').onchange")),context);context.sample=snapshot;vm.runInContext('board=sample;render()',context);
  return{nodes,$,context,requests,snapshot,run:s=>vm.runInContext(s,context),fail:()=>{fail=true;}};
}
test('failed refresh keeps rendered confirmation and exposes stale warning',async()=>{const h=harness(),cards=h.$('#register-tasks').children;h.fail();await h.run('refresh()');assert.equal(h.$('#register-tasks').children,cards);assert.match(h.$('#register-error').textContent,/이전 확인본/);assert.match(h.$('#source-status').textContent,/v5/);});
test('polling preserves dirty fields rather than recreating forms',async()=>{const h=harness(),form=h.$('#register-tasks').children[0].querySelectorAll('form')[0],input=form.querySelectorAll('textarea')[0];input.value='Unfinished explanation';form.listeners.input();await h.run('refresh()');assert.equal(h.$('#register-tasks').children[0].querySelectorAll('form')[0],form);assert.equal(input.value,'Unfinished explanation');});
test('saving one proposal preserves another unfinished form and source truth',async()=>{const h=harness(),forms=h.$('#register-tasks').children.map(c=>c.querySelectorAll('form')[0]);for(const f of forms)f.listeners.input();forms[1].querySelectorAll('textarea')[0].value='Unfinished second task';const controls=forms[0].querySelectorAll('textarea');controls.at(-1).value='Confirmed synthetic request';await forms[0].onsubmit({preventDefault(){}});assert.equal(forms[1].querySelectorAll('textarea')[0].value,'Unfinished second task');assert.equal(h.$('#register-tasks').children[1].querySelectorAll('form')[0],forms[1]);assert.match(h.$('#register-notice').textContent,/원본은 아직 변경되지/);assert.equal(h.snapshot.document.tasks[0].status,'대기');assert.equal(h.requests.filter(r=>r.options?.method==='POST').length,1);});
test('untrusted task text uses text nodes and keeps criteria visible in facts',()=>{const h=harness();h.snapshot.document.tasks[0].task_name='<img src=x onerror=alert(1)>';h.run('render()');const card=h.$('#register-tasks').children[0];assert.equal(card.children[1].textContent,'<img src=x onerror=alert(1)>');assert(card.querySelectorAll('dd').some(n=>n.textContent==='Verified only'));assert.match(h.$('#register-priorities').textContent,/TASK-0/);const provenance=h.$('#source-details').children.map(n=>n.textContent).join(' ');assert.match(provenance,/libfile_synthetic/);assert(provenance.includes('a'.repeat(64)));assert.match(provenance,/Library 보관 버전 5 JSON 문서 내부 버전 1/);});
