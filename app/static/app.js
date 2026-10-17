'use strict';
const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const stageLabels = {planned: '등록 대기', blocked: '막힘', review: '검토 대기', archived: '보관'};
const state = {board: null, view: 'today', filter: 'all', selected: null};
const localDate = () => new Intl.DateTimeFormat('sv-SE', {timeZone: 'Asia/Seoul'}).format(new Date());
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const route = id => state.board.routes.find(r => r.id === id);
const pendingKey = 'haar-pending-command';
let toastTimer;
function toast(message) { $('#toast').textContent = message; $('#toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').hidden = true, 4200); }
function error(message) { $('#error-banner').textContent = message; $('#error-banner').hidden = false; toast(message); }
function pending() { try { return JSON.parse(sessionStorage.getItem(pendingKey)); } catch { return null; } }
function showPending() { $('#pending-banner').hidden = !pending(); }
async function post(path, data, retry = false) {
  const old = pending();
  if (old && !retry) throw new Error('이전 저장 결과를 먼저 확인해 주세요. 화면 위의 같은 요청 재확인 버튼을 눌러 주세요.');
  const command = retry ? old : {path, data: {...data, idempotency_key: crypto.randomUUID()}};
  if (!command) return;
  sessionStorage.setItem(pendingKey, JSON.stringify(command)); showPending();
  let response;
  try { response = await fetch(command.path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(command.data)}); }
  catch { throw new Error('저장 응답을 확인하지 못했어요. 같은 요청 재확인으로 결과를 확인해 주세요.'); }
  let result;
  try { result = await response.json(); } catch { throw new Error('저장 응답이 불명확해요. 같은 요청으로 다시 확인해 주세요.'); }
  if (!response.ok) {
    if (response.status < 500) { sessionStorage.removeItem(pendingKey); showPending(); }
    if (response.status === 409) await load();
    throw new Error(result.error?.message || '요청을 처리하지 못했어요');
  }
  sessionStorage.removeItem(pendingKey); showPending(); $('#error-banner').hidden = true;
  // A committed command stays successful even if refreshing the projection fails.
  if (state.board && result.data?.id) {
    const index = state.board.records.findIndex(r => r.id === result.data.id);
    if (index >= 0) state.board.records[index] = result.data; else state.board.records.unshift(result.data);
  }
  if (state.board && result.operation === 'focus') state.board.focus = result.data;
  try { await load(); } catch {
    if(state.board) render();
    error('저장은 완료됐지만 최신 목록 조회에 실패했어요. 새로고침으로 확인해 주세요.');
  }
  return result;
}
async function load() {
  const response = await fetch('/api/board?date=' + localDate());
  if (!response.ok) throw new Error('작업실을 불러오지 못했어요. SSH 연결과 새로고침을 확인해 주세요.');
  state.board = await response.json();
  $('#loading').hidden = true; $('#content').hidden = false;
  render();
}
const iconPaths = {
  today:'<rect x="3" y="4" width="18" height="17" rx="3"/><path d="M7 2v4m10-4v4M3 10h18m-13 5 3 3 5-5"/>',
  list:'<path d="M9 5h12M9 12h12M9 19h12"/><circle cx="4" cy="5" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="19" r="1"/>',
  review:'<path d="M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-2"/><rect x="8" y="2" width="8" height="4" rx="1"/><path d="m8 14 3 3 5-6"/>',
  agents:'<rect x="4" y="6" width="16" height="14" rx="3"/><path d="M12 2v4m-5 7h.01M17 13h.01M9 17h6M1 11v5m22-5v5"/>',
  external:'<path d="M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  pin:'<path d="m16 3 5 5-4 1-3 5 1 3-2 2-4-4-6 6m3-9 2-2 3 1 5-3 1-4"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 7a7 7 0 0 1 11-2l3 3M4 16l3 3a7 7 0 0 0 11-2"/>',
  lock:'<rect x="4" y="10" width="16" height="12" rx="3"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 15v3"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10h.01"/>',
  copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M8 13h8m-8 4h5"/>'
};
function icon(name) { return `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.file}</svg>`; }
function sampleBadge(r) { return r.sample ? '<span class="sample-label">가상 예시</span>' : ''; }
function priority(r) { return `<span class="priority ${r.priority.toLowerCase()}"><span class="priority-bars" aria-hidden="true"><i></i><i></i><i></i></span>${r.priority}</span>`; }
function stage(r) { return `<span class="stage ${r.intake_stage}"><i aria-hidden="true"></i>${stageLabels[r.intake_stage]}</span>`; }
function focusButton(r) { const selected = state.board.focus.ids.includes(r.id); return `<button class="focus-toggle ${selected ? 'selected' : ''}" data-focus="${r.id}" aria-label="${selected ? '집중 해제' : '오늘 집중에 추가'}: ${esc(r.title)}" aria-pressed="${selected}">${icon('pin')}</button>`; }
function deadline(r) { if (!r.deadline) return '<span class="date-unset">미정</span>'; return `<span class="${r.deadline < localDate() ? 'overdue' : ''}">${esc(r.deadline.slice(5).replace('-', '.'))}${r.deadline < localDate() ? ' 지남' : ''}</span>`; }
function card(r, index) {
  return `<article class="focus-card"><span class="focus-number" aria-label="집중 순서 ${index + 1}">${index + 1}</span><div class="focus-content"><div class="focus-title-line">${priority(r)}<button class="card-title" data-open="${r.id}">${esc(r.title)}</button></div><p class="next-action">${esc(r.next_action || '다음 행동을 정해 주세요')}</p><div class="card-meta"><span>${esc(route(r.route_id).name)}</span><span class="meta-divider">·</span>${deadline(r)}${sampleBadge(r)}<span class="mobile-stage">${stage(r)}</span></div></div><div class="focus-controls">${stage(r)}${focusButton(r)}</div></article>`;
}
function row(r) {
  return `<article class="record-row">${focusButton(r)}<button class="record-main" data-open="${r.id}"><span class="row-title">${priority(r)}<strong>${esc(r.title)}</strong></span><span class="row-detail"><span>${esc(r.area)}</span>${r.sku ? '<span>· ' + esc(r.sku) + '</span>' : ''}${sampleBadge(r)}</span></button>${stage(r)}<span class="row-agent">${esc(route(r.route_id).name)}</span><span class="row-deadline">${deadline(r)}</span></article>`;
}
function render() {
  const b = state.board, records = b.records;
  const active = records.filter(r => r.intake_stage !== 'archived');
  const reviewed = active.filter(r => r.artifacts.length && r.artifacts.at(-1).review !== 'pending').length;
  const count = stage => active.filter(r => r.intake_stage === stage).length;
  $('#stat-active').textContent = active.length; $('#stat-review').textContent = count('review'); $('#stat-blocked').textContent = count('blocked');
  $('#stat-due').textContent = active.filter(r => r.deadline && r.deadline <= localDate()).length;
  $('#nav-count').textContent = active.length; $('#nav-review').textContent = count('review');
  const focus = b.focus.ids.map(id => active.find(r => r.id === id)).filter(Boolean);
  $('#focus-count').textContent = `${focus.length} / 3`;
  $('#focus-list').innerHTML = focus.map(card).join('') + Array.from({length: 3 - focus.length}, (_, i) => `<div class="focus-placeholder"><span class="focus-number">${focus.length + i + 1}</span><div><strong>집중할 작업을 선택하세요</strong><p>작업 목록의 핀을 누르면 여기에 표시됩니다.</p></div>${icon("pin")}</div>`).join('');
  let visible = records.filter(r => state.filter === 'all' ? r.intake_stage !== 'archived' : r.intake_stage === state.filter);
  if (state.view === 'review') visible = records.filter(r => r.intake_stage === 'review');
  visible.sort((a,b) => a.priority.localeCompare(b.priority) || (a.deadline || '9999').localeCompare(b.deadline || '9999'));
  $('#list-count').textContent = visible.length;
  $('#record-list').innerHTML = visible.length ? visible.map(row).join('') : `<div class="empty-state">${icon("list")}<strong>${state.view === 'review' ? '검토를 기다리는 결과가 없어요' : '작업을 위한 여백이 생겼어요'}</strong><p>${state.view === 'review' ? '항목을 열고 결과 링크를 등록해 보세요.' : '새 작업을 정리하거나 예시 항목으로 시작해 보세요.'}</p></div>`;
  const pct = active.length ? Math.round(reviewed / active.length * 100) : 0;
  $('#progress-percent').textContent = pct + '%';
  $('#progress-ring').style.setProperty('--progress', pct + '%');
  $('#progress-legend').innerHTML = [['planned','등록 대기'],['review','검토 대기'],['blocked','막힘']].map(([key,label]) => `<div><span class="legend-dot ${key}"></span><span>${label}</span><strong>${count(key)}</strong></div>`).join('') + `<div><span class="legend-dot archived"></span><span>보관된 항목</span><strong>${records.filter(r => r.intake_stage === 'archived').length}</strong></div>`;
  $('#compact-agents').innerHTML = b.routes.map(r => `<div class="compact-agent"><span class="agent-avatar ${r.id}">${icon("agents")}</span><div><strong>${esc(r.name)}</strong><small>${esc(r.location)}</small></div><span class="connection-state"><i></i>미연결</span></div>`).join('');
  $('#agent-grid').innerHTML = b.routes.map(r => `<article class="panel agent-card"><div class="agent-card-head"><span class="agent-avatar ${r.id}">${icon("agents")}</span><div><h3>${esc(r.name)}</h3><p>${esc(r.location)}</p></div><span class="tag neutral">미연결</span></div><p class="agent-observation">${esc(r.observation)}</p><dl><div><dt>사용자 지침</dt><dd>${r.instructions}</dd></div><div><dt>스킬 버전</dt><dd>${r.skill_version}</dd></div><div><dt>MCP 권한</dt><dd>${r.mcp_permissions}</dd></div><div><dt>마지막 adapter 연결</dt><dd>없음</dd></div><div><dt>실행 가능</dt><dd>아직 불가</dd></div></dl><p class="form-note">설치 관측: 2026.10.17 · 실시간 heartbeat 미연결</p></article>`).join('');
  $('#sync-time').textContent = '저장소 조회 ' + new Date(b.fetched_at).toLocaleTimeString('ko-KR', {timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit'}) + ' KST';
  if (!$('#area-select').children.length) $('#area-select').innerHTML = b.areas.map(a => `<option>${esc(a)}</option>`).join('');
  if (!$('#route-select').children.length) $('#route-select').innerHTML = b.routes.map(r => `<option value="${r.id}">${esc(r.name)} · ${esc(r.location)} (미연결)</option>`).join('');
  $('#load-demo').disabled = records.some(r => r.sample);
  $('#load-demo').textContent = records.some(r => r.sample) ? '예시 항목 추가됨' : '예시 항목 추가';
  setView(state.view, false);
}
function setView(view, rerender = true) {
  state.view = view;
  const labels = {today:'오늘의 작업', all:'모든 항목', review:'결과 검토', agents:'AI 작업실'};
  const titles = {today:'오늘의 작업', all:'모든 항목', review:'결과 검토', agents:'AI 작업실'};
  $('#page-label').textContent = labels[view]; $('#page-title').textContent = titles[view];
  document.title = labels[view] + ' · HAAR Workspace';
  $$('.nav-item').forEach(n => { n.classList.toggle('active', n.dataset.view === view); n.setAttribute('aria-current', n.dataset.view === view ? 'page' : 'false'); });
  $('#agents-view').hidden = view !== 'agents'; $('#today-view').hidden = view === 'agents';
  $('.focus-section').hidden = view !== 'today'; $('.right-column').hidden = view !== 'today';
  $('.dashboard-grid').classList.toggle('single', view !== 'today');
  $('.filter-bar').hidden = view === 'review'; $('#all-link').hidden = view !== 'today';
  if (rerender && state.board) render();
}
function openRecord(id = null) {
  const record = state.board.records.find(r => r.id === id);
  state.selected = record ? structuredClone(record) : null;
  $('#record-form').reset(); $('#artifact-form').reset(); $('#handoff-form').reset();
  $('#dialog-title').textContent = record ? record.title : '새 작업 정리';
  $('#detail-extra').hidden = !record; $('#stage-field').hidden = !record;
  if (record) {
    for (const [key,value] of Object.entries(record)) { const el = $('#record-form').elements.namedItem(key); if (el) el.value = value; }
    renderDetails(record);
  }
  if (!$('#record-dialog').open) $('#record-dialog').showModal();
}
function renderDetails(record) {
  $('#artifact-list').innerHTML = record.artifacts.map((a, index) => `<article class="artifact"><div><span class="tag neutral">v${index+1}</span><a href="${esc(a.url)}" target="_blank" rel="noreferrer noopener">${esc(a.label)} ${icon("external")}</a><span class="tag ${a.review === 'approved' ? 'approved' : 'neutral'}">${{pending:'검토 대기',approved:'내용 확인',changes_requested:'수정 요청'}[a.review]}</span></div><p>${esc(a.version_note)}</p>${a.review_note ? `<p>검토 메모: ${esc(a.review_note)}</p>` : ''}${index === record.artifacts.length-1 && a.review === 'pending' ? `<form class="review-form" data-version="${a.version_id}"><label>검토 메모<input name="note" required maxlength="1000" placeholder="확인한 내용이나 필요한 수정을 남겨 주세요"></label><div><button class="secondary" name="decision" value="changes_requested">수정 요청</button><button class="primary" name="decision" value="approved">내용 확인 완료</button></div></form>` : ''}</article>`).join('') || '<p class="form-note">아직 연결한 결과물이 없어요.</p>';
  $('#handoff-list').innerHTML = record.handoffs.map(h => `<article class="handoff"><span class="tag neutral">직접 인계 기록 · 자동 전송 없음</span><p>${esc(h.note)}</p>${h.url ? `<a target="_blank" rel="noreferrer noopener" href="${esc(h.url)}">참고 자료 ${icon("external")}</a>` : ''}</article>`).join('') || '<p class="form-note">결정과 다음 행동을 남기면 이어서 일하기 쉬워져요.</p>';
}
function formData(form) { return Object.fromEntries(new FormData(form).entries()); }
function selectedData() { if (!state.selected) throw new Error('항목을 다시 열어 주세요'); return {id: state.selected.id, expected_revision: state.selected.revision}; }
async function submitForm(event, path, data) {
  event.preventDefault(); const button = event.submitter; if(button) button.disabled = true;
  // Saving one section must not discard unfinished text in another section.
  const keep = ['record-form', 'artifact-form', 'handoff-form']
    .filter(id => $('#' + id) !== event.target).map(id => {
      const values = formData($('#' + id));
      // Restore only dirty main fields; keep new server stage/revision from the receipt.
      const keepValues = id === 'record-form' && state.selected
        ? Object.fromEntries(Object.entries(values).filter(([key, value]) => value !== String(state.selected[key] ?? '')))
        : values;
      return [id, keepValues];
    });
  try {
    const result = await post(path, data);
    if(state.selected) {
      openRecord(result.data.id);
      for (const [id, values] of keep) for (const [key, value] of Object.entries(values)) {
        const field = $('#' + id).elements.namedItem(key); if(field) field.value = value;
      }
    } else $('#record-dialog').close();
    toast('VPS 초안 저장소에 저장했어요 · AI 전송 없음');
  }
  catch(e) { error(e.message); }
  finally { if(button) button.disabled = false; }
}
$('#record-form').addEventListener('submit', event => {
  const data = formData(event.currentTarget);
  if (!state.selected) delete data.intake_stage;
  submitForm(event, state.selected ? '/api/records/edit' : '/api/records', {...data, ...(state.selected ? selectedData() : {})});
});
$('#artifact-form').addEventListener('submit', e => submitForm(e, '/api/artifacts', {...formData(e.currentTarget), ...selectedData()}));
$('#handoff-form').addEventListener('submit', e => submitForm(e, '/api/handoffs', {...formData(e.currentTarget), ...selectedData()}));
$('#artifact-list').addEventListener('submit', e => { if(e.target.matches('.review-form')) submitForm(e, '/api/reviews', {...selectedData(), version_id:e.target.dataset.version, note:formData(e.target).note, decision:e.submitter.value}); });
document.addEventListener('click', async event => {
  const close = event.target.closest('[data-close]'); if(close) $('#' + close.dataset.close).close();
  const nav = event.target.closest('[data-view]'); if(nav) setView(nav.dataset.view);
  const opener = event.target.closest('[data-open]'); if(opener) openRecord(opener.dataset.open);
  const filter = event.target.closest('[data-filter]'); if(filter) { state.filter = filter.dataset.filter; $$('.chip').forEach(c => c.classList.toggle('active', c===filter)); render(); }
  const focus = event.target.closest('[data-focus]');
  if(focus) {
    const ids = state.board.focus.ids.filter(id => state.board.records.some(r => r.id === id && r.intake_stage !== 'archived'));
    const index = ids.indexOf(focus.dataset.focus); if(index >= 0) ids.splice(index,1); else ids.push(focus.dataset.focus);
    try { await post('/api/focus', {local_date:localDate(), ids, expected_revision:state.board.focus.revision}); toast('오늘 집중 목록을 저장했어요'); } catch(e) { error(e.message); }
  }
});
$('#new-record').onclick = () => openRecord();
$('#all-link').onclick = () => setView('all'); $('#agents-link').onclick = () => setView('agents');
$('#refresh').onclick = async () => { try { await load(); toast('최신 내용을 불러왔어요'); } catch(e) { error(e.message); } };
$('#load-demo').onclick = async () => { try { await post('/api/demo', {}); toast('가상 예시 3개를 추가했어요'); } catch(e) { error(e.message); } };
$('#retry-pending').onclick = async () => { try { const result = await post(null,null,true); toast('저장 결과를 확인했어요'); if(result?.data?.id && $('#record-dialog').open) openRecord(result.data.id); } catch(e) { error(e.message); } };
$('#copy-handoff').onclick = async () => {
  const r=state.selected, text = `[HAAR 인계 초안 · AI 자동 전송 아님]\n${r.title}\nSKU: ${r.sku || '미정'}\n목표/완료조건: ${r.brief}\n다음 행동: ${r.next_action}\n담당: ${route(r.route_id).name}\n외부 게시·발송·광고비 변경은 별도 승인 필요`;
  try { await navigator.clipboard.writeText(text); toast('인계 초안을 복사했어요. 담당 AI에게 직접 전달해 주세요.'); } catch { error('클립보드를 사용할 수 없어요. 지시 초안을 직접 선택해 복사해 주세요.'); }
};
$$('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
$$('[data-close]').forEach(el => { if(el.classList.contains('icon-button')) el.innerHTML = icon('close'); });
$('#today-date').textContent = new Intl.DateTimeFormat('ko-KR', {timeZone:'Asia/Seoul',month:'long',day:'numeric',weekday:'long'}).format(new Date()) + ' · KST';
showPending(); load().catch(e => { $('#loading').textContent = '작업실 연결을 확인해 주세요.'; error(e.message); });
