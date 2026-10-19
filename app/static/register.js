'use strict';
let board = null, dirty = false, busy = false;
const dirtyForms = new Set();
let displayedFilter = '';
let polling=false,lastCursor=-1;
const $ = s => document.querySelector(s);
const el = (tag, text, cls) => {const n=document.createElement(tag); if(text!==undefined)n.textContent=text; if(cls)n.className=cls; return n;};
const showError = message => {$('#register-error').textContent=message;$('#register-error').hidden=!message;};
const dateText = value => value ? new Date(value).toLocaleString('ko-KR',{timeZoneName:'short'}) : '미확인';
async function api(path, body) {
  const r=await fetch(path,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
  const d=await r.json();if(!r.ok)throw Error(d.error?.message||'요청에 실패했습니다.');return d;
}
async function refresh() {
  if(busy)return;
  try {
    const next=await api('/api/register');
    if(dirty){$('#register-notice').textContent='입력을 보존하기 위해 자동 화면 갱신을 보류했습니다. 저장 시 원본 버전을 다시 확인합니다.';return;}
    board=next;lastCursor=board.events[0]?.id||0;render();showError('');
  }catch(e){showError('최신 조회 실패: '+e.message+(board?' 이전 확인본을 유지합니다.':' 아직 표시할 확인본이 없습니다.'));}
}
async function pollChanges() {
  if(polling||busy)return;polling=true;
  try {
    const next=await api('/api/register/revision');
    if(!board||next.revision!==board.source.version||next.cursor!==lastCursor)await refresh();
    else{Object.assign(board.source,next);renderSource();showError('');}
  }catch(e){showError('변경 연결 끊김: 이전 확인본을 유지합니다. '+e.message);}
  finally{polling=false;}
}
function renderSource() {
  const source=board.source,doc=board.document,live=source.bridge==='parent_events';
  $('#source-status').textContent=doc?(live?'운영 revision '+source.version:'Library v'+source.version)+' · '+doc.tasks.length+'개 · 갱신 '+dateText(source.imported_at)+(live?(source.publisher_offline?' · 게시자 연결 미확인':' · 부모 이벤트 연결')+' · 전송 대기 '+(source.pending_delivery||0)+' / 충돌 '+(source.blocked_delivery||0):' · 실시간 변경 미확인')+(source.last_error?' · 검증 실패, 이전 확인본 유지':''):'아직 초기 원본을 가져오지 않았습니다.';
  $('#source-boundary').textContent='5초마다 변경 확인 · Library 상시 수집 미연결'+(live?' · 운영 단일 원본: VPS 대장':' · 부모 이벤트 대기');
  $('#source-details').replaceChildren(...[['Library 초기 출처 ID',source.library_id||'미연결'],['SHA-256',source.digest||'미확인'],['Library 보관 버전',source.library_version||source.version||'미확인'],['JSON 문서 내부 버전',doc?.version||'미확인'],['원본 수정 시각',dateText(doc?.updated_at)],['게시자 마지막 접촉',dateText(source.publisher_last_seen)]].flatMap(([name,value])=>[el('dt',name),el('dd',String(value))]));
}
function field(form,name,label,value,multiline=false) {
  const wrap=el('label',label),input=el(multiline?'textarea':'input');input.name=name;input.value=value||'';input.maxLength=multiline?2000:1000;if(multiline)input.rows=3;wrap.append(input);form.append(wrap);return input;
}
function renderTask(task) {
  const article=el('article',undefined,'register-task');article.dataset.taskId=task.id;
  article.id=task.id;article.append(el('span',task.id+' · '+task.status,'tag neutral'),el('h2',task.task_name),el('p',task.status_detail));if(task.priority_proposal)article.append(el('p','우선순위: '+task.priority_proposal+(task.priority_reason?' · '+task.priority_reason:'')));
  const dl=el('dl');for(const [label,value] of [['최신 지시',task.latest_instruction],['다음 행동',task.next_action],['블로커',task.blocker||'기록 없음'],['완료 기준',task.completion_criteria],['마지막 확인',dateText(task.last_verified_at)],['확인 근거',task.verification_basis||task.evidence?JSON.stringify(task.verification_basis||{evidence:task.evidence}):'원본에 미기록 · 확인 필요'],['담당 작업',task.owner_task_id||'미확인'],['결과 Library ID',(task.result_library_ids||[]).join(', ')||'기록 없음']])dl.append(el('dt',label),el('dd',value));const facts=el('details');facts.append(el('summary','근거·블로커·완료 기준'),dl);article.append(facts);
  for(const p of board.proposals.filter(p=>p.task_id===task.id)) {
    const box=el('section',undefined,'register-proposal');box.append(el('strong','제안 '+p.state+' · 원본 v'+p.base_version),el('p',p.changes.status+' · '+p.changes.status_detail),el('p','Library 원본 반영 '+(p.state==='confirmed'?'확인':'미확인')+' · 실제 실행 권한 없음'));
    if(p.state==='pending') {
      const download=el('button','JSON·MD 반영 묶음 내보내기','secondary');download.type='button';download.onclick=async()=>{download.disabled=true;try{const data=await api('/api/register/export',{proposal_id:p.id});const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='HAAR-register-proposal-'+p.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('#register-notice').textContent='내보낸 묶음은 Library 반영 완료가 아닙니다. 권한 있는 소비자가 원본 버전을 확인하고 교체한 뒤 다시 가져와야 합니다.';}catch(e){showError(e.message);}finally{download.disabled=false;}};
      const cancel=el('button','제안 취소','secondary');cancel.type='button';cancel.onclick=async()=>{cancel.disabled=true;try{await api('/api/register/cancel',{proposal_id:p.id,idempotency_key:crypto.randomUUID()});await refresh();}catch(e){showError(e.message);cancel.disabled=false;}};if(board.source.bridge==='parent_events')box.append(el('p','부모 검토가 필요합니다. Library 후보 내보내기는 중지됐습니다.'),cancel);else box.append(download,cancel);
    }article.append(box);
  }
  const details=el('details'),summary=el('summary','상태 변경 제안');details.append(summary);
  const form=el('form'),wrap=el('label','제안 상태'),select=el('select');select.name='status';for(const status of Object.keys(board.document.status_definitions)){const option=el('option',status);option.value=status;select.append(option);}select.value=task.status;wrap.append(select);form.append(wrap);
  field(form,'status_detail','현재 상태 설명',task.status_detail,true);field(form,'next_action','다음 행동',task.next_action,true);field(form,'blocker','블로커',task.blocker,true);const time=field(form,'last_verified_at','실제로 확인한 시각 (시간대 포함 ISO8601)',task.last_verified_at);time.required=true;
  const evidence=field(form,'verification_note','이번 확인의 근거',null,true);evidence.required=true;
  form.append(el('p','원본 상태·완료 기준은 즉시 바뀌지 않습니다. 이 제안으로 실제 작업을 재개·중지하거나 광고·게시 권한을 부여하지 않습니다.','form-note'));
  const button=el('button','반영 대기 제안 저장','primary');button.type='submit';form.append(button);let request=null;
  form.addEventListener('input',()=>{dirtyForms.add(form);dirty=true;request=null;});form.onsubmit=async event=>{event.preventDefault();if(busy)return;busy=true;button.disabled=true;
    try{if(!request)request={...Object.fromEntries(new FormData(form)),task_id:task.id,expected_source_version:board.source.version,idempotency_key:crypto.randomUUID()};const receipt=await api('/api/register/proposals',request);dirtyForms.delete(form);dirty=dirtyForms.size>0;const message='반영 대기 제안을 저장했습니다. 운영 원본은 아직 변경되지 않았습니다. 기록 ID: '+receipt.proposal_id;$('#register-notice').textContent=message;details.append(el('p',message));for(const control of form.querySelectorAll('input,select,textarea,button'))control.disabled=true;busy=false;if(!dirty)await refresh();}
    catch(e){showError(e.message+' 입력은 보존됩니다. 응답이 불확실하면 같은 내용으로 다시 저장하세요.');}finally{busy=false;button.disabled=false;}
  };details.append(form);article.append(details);
  const raw=el('details');raw.append(el('summary','원본 전체 필드'),el('pre',JSON.stringify(task,null,2)));article.append(raw);return article;
}
function render() {
  const source=board.source,doc=board.document;
  renderSource();
  $('#register-priorities').textContent=doc?'사용자 확정 최우선: '+(doc.tasks.filter(t=>t.priority_proposal==='최우선(사용자 확정)').map(t=>t.id).join(' / ')||'원본에 지정 없음')+(board.warnings?.length?' · 근거 미기록 '+board.warnings.length+'개':''):'';
  const filter=$('#status-filter'),selected=filter.value;filter.replaceChildren(el('option','전체'));filter.firstChild.value='';if(doc)for(const key of Object.keys(doc.status_definitions)){const n=el('option',key);n.value=key;filter.append(n);}filter.value=selected;
  displayedFilter=filter.value;
  const tasks=doc?doc.tasks.filter(t=>!filter.value||t.status===filter.value):[];$('#register-count').textContent='표시 '+tasks.length+' / 원본 '+(doc?.tasks.length||0)+' · 반영 대기 '+board.proposals.filter(p=>p.state==='pending').length;
  $('#register-tasks').replaceChildren(...tasks.map(renderTask));$('#register-events').replaceChildren(...board.events.map(e=>el('li',dateText(e.occurred_at)+' · '+e.kind+' · '+(e.task_id||'원본')+' · '+JSON.stringify(e.body))));
}
$('#status-filter').onchange=()=>{if(dirty){$('#status-filter').value=displayedFilter;$('#register-notice').textContent='작성 중인 제안을 먼저 저장하거나 페이지를 다시 열어 주세요.';return;}render();};
$('#refresh-register').onclick=refresh;
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')pollChanges();});
setInterval(()=>{if(document.visibilityState==='visible')pollChanges();},5000);
refresh();
