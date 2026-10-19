'use strict';
const $=s=>document.querySelector(s),el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const taskId=new URLSearchParams(location.search).get('task')||'';
let pages=[],session,timer,searchTimer,retryDelay=1000,pendingCreate=null,creating=false,navigationToken=0,loadingPage=false,recoveredDraft=null;
const showError=message=>{$('#notes-error').textContent=message||'';$('#notes-error').hidden=!message;};
async function api(path,body){const response=await fetch(path,{cache:'no-store',...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});const data=await response.json();if(!response.ok){const error=Error(data.error?.message||'VPS 요청에 실패했습니다.');error.status=response.status;throw error;}return data;}
function newBlock(type,id=crypto.randomUUID()){return type==='table'?{id,type,cells:[['',''],['','']]}:type==='check'?{id,type,text:'',checked:false}:{id,type,text:''};}
function stateChanged(s){
  clearTimeout(timer);
  $('#save-status').textContent=s.conflict?'저장 충돌 · 내 입력 보존':s.error?'VPS 저장 실패 · 이 탭에 입력 보존':s.saving?'VPS 저장 중…':s.dirty?'변경 사항 저장 대기':'VPS 저장됨 · revision '+s.revision;
  $('#save-recovery').hidden=!s.error&&!recoveredDraft;if(s.error)showError(s.error.message+' 입력은 현재 탭에 보존됩니다.');else if(s.pageId)showError('');$('#recover-server').hidden=!s.conflict;$('#new-child').disabled=!s.pageId||s.dirty||s.saving||creating||loadingPage;
  if(s.error)$('#recovery-draft').value=JSON.stringify(s.value,null,2);
  if(s.dirty&&!s.saving&&!s.conflict&&!s.invalid){const delay=s.error?retryDelay:800;timer=setTimeout(()=>s.flush(),delay);if(s.error)retryDelay=Math.min(30000,retryDelay*2);}else if(!s.dirty)retryDelay=1000;
}
session=new NoteState.NoteSession(async request=>{const receipt=await api('/api/notes/save',request);loadList().catch(()=>{});return receipt;},stateChanged);
function edit(mutator,rerender=false){const value=structuredClone(session.value);mutator(value);session.edit(value);if(rerender)renderEditor();}
function depth(page){let n=0,parent=page.parent_id;while(parent&&n<8){n++;parent=pages.find(p=>p.id===parent)?.parent_id;}return n;}
async function loadList(){
  const query=$('#note-search').value;const data=await api('/api/notes?task_id='+encodeURIComponent(taskId)+'&q='+encodeURIComponent(query));
  if(query!==$('#note-search').value)return;
  pages=data.pages;$('#notes-task-label').textContent=data.task.id+' · '+data.task.title;
  const select=$('#page-select');select.replaceChildren();$('#page-list').replaceChildren();
  for(const page of pages){const option=el('option',page.title||'제목 없는 노트');option.value=page.id;select.append(option);const button=el('button',page.title||'제목 없는 노트','page-link'+(page.id===session.pageId?' active':''));button.type='button';button.dataset.depth=String(depth(page));button.onclick=()=>switchPage(page.id);$('#page-list').append(button);}
  select.value=session.pageId||'';$('#page-count').textContent=pages.length?'노트 '+pages.length+'개':'검색된 노트가 없습니다.';return data;
}
async function loadPage(id){
  const navigation=++navigationToken;loadingPage=true;$('#editor-body').disabled=true;$('#new-note').disabled=true;$('#new-child').disabled=true;
  try{
  const page=await api('/api/notes/page?page_id='+encodeURIComponent(id));if(navigation!==navigationToken)return;if(page.task_id!==taskId)throw Error('이 작업에 연결된 노트를 선택하세요.');
  session.load(page);$('#note-title').value=page.title;$('#notes-empty').hidden=true;$('#editor-body').hidden=false;$('#new-child').disabled=false;renderEditor();showError('');
  const url=new URL(location);url.searchParams.set('page',id);history.replaceState(null,'',url);await loadList();
  }finally{if(navigation===navigationToken){loadingPage=false;$('#editor-body').disabled=false;$('#new-note').disabled=creating;$('#new-child').disabled=creating||!session.pageId||session.dirty;}}
}
async function switchPage(id){try{if(session.dirty&&!(await session.flush())){$('#page-select').value=session.pageId;showError('저장되지 않은 입력을 먼저 확인하세요. 다른 페이지로 이동하지 않았습니다.');return;}await loadPage(id);}catch(e){showError(e.message);}}
async function createPage(parent){
  if(creating||loadingPage)return;
  if(session.dirty&&!(await session.flush())){showError('현재 입력을 저장한 뒤 새 페이지를 만드세요.');return;}
  if(pendingCreate&&pendingCreate.parent_id!==parent){showError('이전 생성 요청을 같은 버튼으로 다시 확인하세요.');return;}
  if(!pendingCreate)pendingCreate={task_id:taskId,parent_id:parent,title:parent?'새 하위 페이지':'새 노트',idempotency_key:crypto.randomUUID()};
  creating=true;$('#new-note').disabled=true;$('#new-child').disabled=true;
  try{const receipt=await api('/api/notes/pages',pendingCreate);pendingCreate=null;await loadPage(receipt.page_id);$('#note-title').focus();}
  catch(e){showError('노트 생성 결과를 확인하지 못했습니다. 같은 버튼으로 재시도하면 중복 생성을 방지합니다. '+e.message);}
  finally{creating=false;$('#new-note').disabled=false;$('#new-child').disabled=!session.pageId||session.dirty;}
}
function renderEditor(){
  const blocks=session.value.blocks,host=$('#note-blocks');host.replaceChildren();
  blocks.forEach((block,index)=>{
    const wrap=el('section',undefined,'note-block');wrap.dataset.blockId=block.id;
    const tools=el('div',undefined,'block-tools'),names={paragraph:'문단',heading:'제목',check:'체크리스트',table:'표'};tools.append(el('span',(index+1)+' · '+names[block.type]));
    for(const [label,delta] of [['위로',-1],['아래로',1],['삭제',0]]){const button=el('button',label);button.type='button';button.setAttribute('aria-label',(index+1)+'번 블록 '+label);button.disabled=delta===-1&&index===0||delta===1&&index===blocks.length-1;button.onclick=()=>edit(value=>{const i=value.blocks.findIndex(b=>b.id===block.id);if(delta===0)value.blocks.splice(i,1);else[value.blocks[i],value.blocks[i+delta]]=[value.blocks[i+delta],value.blocks[i]];},true);tools.append(button);}wrap.append(tools);
    if(block.type==='table'){
      const scroll=el('div',undefined,'note-table-scroll'),table=el('table',undefined,'note-table');table.setAttribute('aria-label',(index+1)+'번 표');
      block.cells.forEach((row,r)=>{const tr=el('tr');row.forEach((cell,c)=>{const td=el('td'),input=el('input');input.value=cell;input.maxLength=2000;input.setAttribute('aria-label',(index+1)+'번 표 '+(r+1)+'행 '+(c+1)+'열');input.oninput=()=>edit(v=>v.blocks.find(b=>b.id===block.id).cells[r][c]=input.value);td.append(input);tr.append(td);});table.append(tr);});scroll.append(table);wrap.append(scroll);
      const actions=el('div',undefined,'table-actions');for(const [label,fn,disabled] of [['행 추가',b=>b.cells.push(b.cells[0].map(()=>'')),block.cells.length>=30],['열 추가',b=>b.cells.forEach(row=>row.push('')),block.cells[0].length>=6],['마지막 행 삭제',b=>b.cells.pop(),block.cells.length<=1],['마지막 열 삭제',b=>b.cells.forEach(row=>row.pop()),block.cells[0].length<=1]]){const button=el('button',label,'secondary');button.type='button';button.disabled=disabled;button.onclick=()=>edit(v=>fn(v.blocks.find(b=>b.id===block.id)),true);actions.append(button);}wrap.append(actions);
    }else{
      const input=el('textarea');input.rows=block.type==='heading'?2:3;input.value=block.text;input.maxLength=10000;input.className=block.type==='heading'?'heading-input':'';input.setAttribute('aria-label',(index+1)+'번 '+names[block.type]+' 내용');input.placeholder=block.type==='paragraph'?'기록을 남기거나 /로 블록 선택':'';
      const menu=el('div',undefined,'slash-menu');menu.hidden=true;menu.setAttribute('role','menu');
      const showSlash=()=>{menu.replaceChildren();menu.hidden=!input.value.startsWith('/')||input.value.length>20;if(menu.hidden)return;const query=input.value.slice(1).trim();for(const [type,name] of Object.entries(names)){if(query&&!name.includes(query))continue;const button=el('button',name);button.type='button';button.setAttribute('role','menuitem');button.onclick=()=>{edit(v=>{const i=v.blocks.findIndex(b=>b.id===block.id);v.blocks[i]=newBlock(type,block.id);},true);$('#note-blocks').querySelector('[data-block-id="'+block.id+'"] textarea, [data-block-id="'+block.id+'"] input')?.focus();};menu.append(button);}};
      input.oninput=()=>{edit(v=>v.blocks.find(b=>b.id===block.id).text=input.value);showSlash();};input.onkeydown=event=>{if(event.key==='Escape'){menu.hidden=true;return;}if(!menu.hidden&&(event.key==='ArrowDown'||event.key==='Enter')){const button=menu.querySelector('button');if(button){event.preventDefault();button.focus();}}};
      menu.onkeydown=event=>{if(event.key==='Escape'){menu.hidden=true;input.focus();}if(event.key==='ArrowDown'||event.key==='ArrowUp'){event.preventDefault();const buttons=[...menu.querySelectorAll('button')],i=buttons.indexOf(document.activeElement);buttons[(i+(event.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus();}};
      if(block.type==='check'){const row=el('div',undefined,'check-row'),check=el('input');check.type='checkbox';check.checked=block.checked;check.setAttribute('aria-label',(index+1)+'번 체크 완료');check.onchange=()=>edit(v=>v.blocks.find(b=>b.id===block.id).checked=check.checked);const target=el('label',undefined,'check-target');target.append(check);row.append(target,input);wrap.append(row);}else wrap.append(input);wrap.append(menu);
    }
    host.append(wrap);
  });
}
$('#note-title').oninput=()=>edit(v=>v.title=$('#note-title').value);
$('#new-note').onclick=()=>createPage(null);$('#new-child').onclick=()=>createPage(session.pageId);
$('#add-block').onclick=()=>{edit(v=>v.blocks.push(newBlock('paragraph')),true);$('#note-blocks .note-block:last-child textarea')?.focus();};
$('#page-select').onchange=()=>switchPage($('#page-select').value);
$('#note-search').oninput=()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadList().catch(e=>showError(e.message)),300);};
$('#retry-save').onclick=()=>session.flush();
$('#recover-server').onclick=async()=>{try{const draft=JSON.stringify(session.value,null,2);await loadPage(session.pageId);recoveredDraft=draft;$('#recovery-draft').value=draft;$('#save-recovery').hidden=false;$('#recover-server').hidden=true;}catch(e){showError(e.message);}};
window.addEventListener('beforeunload',event=>{if(session.dirty||pendingCreate){event.preventDefault();event.returnValue='';}});
window.addEventListener('online',()=>{if(session.dirty)session.flush();else if(session.pageId)loadPage(session.pageId).catch(e=>showError(e.message));});
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible'&&session.dirty)session.flush();});
(async()=>{try{const data=await loadList();const requested=new URLSearchParams(location.search).get('page');if(requested&&data.pages.some(p=>p.id===requested))await loadPage(requested);else if(data.pages.length)await loadPage(data.pages[0].id);else $('#save-status').textContent='VPS 연결됨 · 저장할 노트를 만드세요.';}catch(e){$('#save-status').textContent='VPS 연결 확인 실패';showError(e.message);$('#new-note').disabled=true;}})();
