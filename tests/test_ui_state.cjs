// State regressions for the real UI functions, with a small DOM/network double.
// Run: node --test tests/test_ui_state.cjs
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

const source = fs.readFileSync(path.join(__dirname, '../app/static/app.js'), 'utf8');
const functions = source.slice(0, source.indexOf("$('#record-form').addEventListener"));

function harness({refreshFails = false, operation = 'artifact'} = {}) {
  const stored = {id:'record-1', title:'Stored title', brief:'Stored brief',
    next_action:'Stored action', area:'상품·상세페이지', route_id:'gpt',
    priority:'P1', deadline:'', sku:'', intake_stage:'planned', revision:1,
    artifacts:[], handoffs:[]};
  if (operation === 'review') stored.intake_stage = 'review';
  const saved = {...structuredClone(stored), revision:2};
  if (operation === 'artifact') saved.intake_stage = 'review';
  if (operation === 'review') saved.intake_stage = 'blocked';
  const elements = new Map(), storage = new Map(), calls = [];
  function form(values) {
    const fields = Object.fromEntries(Object.entries(values).map(([name, value]) => [name, {value}]));
    return {fields, elements:{namedItem:name => fields[name] || null},
      reset() { for (const field of Object.values(fields)) field.value = ''; }};
  }
  elements.set('#record-form', form(Object.fromEntries(Object.entries(stored).filter(([,v]) => typeof v === 'string'))));
  elements.set('#artifact-form', form({label:'', url:'', version_note:''}));
  elements.set('#handoff-form', form({note:'', url:''}));
  elements.set('#record-dialog', {open:true, close(){this.open=false;}, showModal(){this.open=true;}});
  function element(selector) {
    if (!elements.has(selector)) elements.set(selector, {hidden:false, innerHTML:'', textContent:''});
    return elements.get(selector);
  }
  class FormDataDouble {
    constructor(form) { this.form = form; }
    entries() { return Object.entries(this.form.fields).map(([name, field]) => [name, field.value])[Symbol.iterator](); }
  }
  const context = vm.createContext({Intl, Date, structuredClone, crypto:webcrypto,
    // No real timers, browser, database, or outbound requests.
    setTimeout:()=>0, clearTimeout:()=>{}, FormData:FormDataDouble,
    document:{querySelector:element},
    sessionStorage:{getItem:key=>storage.get(key)||null,
      setItem:(key,value)=>storage.set(key,value), removeItem:key=>storage.delete(key)},
    fetch:async(url, options) => {
      calls.push({url, options});
      if (options?.method === 'POST') return {ok:true, json:async()=>({operation, data:saved})};
      if (refreshFails) throw new Error('Injected board GET failure');
      return {ok:true, json:async()=>({records:[saved]})};
    }});
  vm.runInContext(functions, context);
  context.stored = stored;
  vm.runInContext('state.board={records:[stored]}; render=()=>{};', context);
  return {context, stored, saved, calls, storage, element,
    run:code=>vm.runInContext(code, context)};
}

for (const [operation, stage] of [['artifact', 'review'], ['review', 'blocked']]) {
  test(`${operation} save keeps the server stage when the user did not change it`, async () => {
    const h = harness({operation});
    h.run('state.selected=structuredClone(stored)');
    h.context.event = {preventDefault(){}, target:operation === 'artifact' ?
      h.element('#artifact-form') : {fields:{note:{value:'Review note'}}}, submitter:{disabled:false}};
    await h.run(`submitForm(event, '/api/${operation}', {id:'record-1', expected_revision:1})`);
    assert.equal(h.element('#record-form').fields.intake_stage.value, stage,
      'A later main-form save must not overwrite the stage changed by the auxiliary save');
  });
}

test('committed create remains successful and closes dialog when board refresh fails', async () => {
  const h = harness({refreshFails:true, operation:'create'});
  h.context.event = {preventDefault(){}, target:h.element('#record-form'), submitter:{disabled:false}};
  await h.run("submitForm(event, '/api/records', {title:'Stored title'})");
  assert.equal(h.element('#record-dialog').open, false);
  assert.equal(h.storage.size, 0);
  assert.equal(h.calls.filter(c=>c.options?.method === 'POST').length, 1);
  assert.equal(h.run('state.board.records[0].revision'), 2);
});

for (const operation of ['artifact', 'handoff', 'review']) {
  test(`${operation} save preserves unfinished fields in other forms`, async () => {
    const h = harness({operation});
    h.run("state.selected=structuredClone(stored)");
    h.element('#record-form').fields.brief.value = 'Unfinished new brief';
    h.element('#record-form').fields.next_action.value = 'Unfinished next action';
    h.element('#record-form').fields.route_id.value = 'mac_orca';
    h.element('#artifact-form').fields.label.value = 'Unfinished result label';
    h.element('#handoff-form').fields.note.value = 'Unfinished handoff';
    const submitted = operation === 'artifact' ? h.element('#artifact-form') :
      operation === 'handoff' ? h.element('#handoff-form') : {fields:{note:{value:'Review note'}}};
    h.context.event = {preventDefault(){}, target:submitted, submitter:{disabled:false}};
    await h.run(`submitForm(event, '/api/${operation}', {id:'record-1', expected_revision:1})`);
    assert.equal(h.element('#record-form').fields.brief.value, 'Unfinished new brief');
    assert.equal(h.element('#record-form').fields.next_action.value, 'Unfinished next action');
    assert.equal(h.element('#record-form').fields.route_id.value, 'mac_orca');
    if (operation !== 'artifact') assert.equal(h.element('#artifact-form').fields.label.value, 'Unfinished result label');
    if (operation !== 'handoff') assert.equal(h.element('#handoff-form').fields.note.value, 'Unfinished handoff');
    assert.equal(h.run('state.selected.revision'), 2);
    assert.equal(h.context.event.submitter.disabled, false);
  });
}
