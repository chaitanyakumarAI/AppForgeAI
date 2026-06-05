// AppForge AI — Frontend JS
const API = '';
let currentResult = null;
let successChart = null;
let latencyChart = null;

const EXAMPLES = {
  crm: "Build a CRM with login, contacts, deal pipeline, dashboard, role-based access (admin/sales/viewer), and premium Stripe payments. Admins see full analytics.",
  lms: "Create a Learning Management System where instructors create courses with video lessons and quizzes. Students enroll, track progress, and get certificates.",
  ecom: "Build a multi-vendor marketplace. Sellers list products and manage inventory. Buyers browse, cart, checkout with Stripe. Admin takes 10% commission.",
  vague: "build an app"
};

// Tab switching
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'history') loadHistory();
    if (btn.dataset.tab === 'eval') renderTestCases();
  });
});

// Output subtabs
document.querySelectorAll('.out-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.out-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.out-section').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('os-' + btn.dataset.out).classList.add('active');
  });
});

// Mode pills
document.querySelectorAll('.mode-pill').forEach(pill => {
  pill.addEventListener('click', () => {
    document.querySelectorAll('.mode-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    updateCostEstimate(pill.dataset.mode);
  });
});

// Examples
Object.keys(EXAMPLES).forEach(key => {
  const el = document.getElementById('ex-' + key);
  if (el) el.addEventListener('click', () => {
    document.getElementById('prompt-input').value = EXAMPLES[key];
    updateCharCount();
  });
});

// Char count
const promptInput = document.getElementById('prompt-input');
if (promptInput) {
  promptInput.addEventListener('input', updateCharCount);
}
function updateCharCount() {
  const countEl = document.getElementById('char-count');
  if (countEl && promptInput) {
    countEl.textContent = promptInput.value.length;
  }
}

// Cost estimate
async function updateCostEstimate(mode) {
  try {
    const r = await fetch(`${API}/api/cost-estimate?mode=${mode}`);
    const d = await r.json();
    document.getElementById('cost-latency').textContent = d.latency_s + 's';
    document.getElementById('cost-price').textContent = '$' + d.cost_usd;
    document.getElementById('cost-model').textContent = d.model;
  } catch(e) {}
}
updateCostEstimate('balanced');

// Pipeline stage state
function setStage(stageId, state, text) {
  const el = document.getElementById('ps-' + stageId);
  if (!el) return;
  el.className = 'pipe-stage ' + state;
  const s = el.querySelector('.pipe-status');
  if (s) {
    s.className = 'pipe-status ' + state;
    s.textContent = text;
  }
}

function resetStages() {
  ['stage1_intent','stage2_design','stage3_schema','stage4_refinement','validation','runtime_simulation'].forEach(s => {
    setStage(s, 'idle', '—');
  });
}

// Generate
const genBtn = document.getElementById('generate-btn');
if (genBtn) {
  genBtn.addEventListener('click', generate);
}

async function generate() {
  const prompt = promptInput.value.trim();
  if (!prompt) { promptInput.focus(); return; }
  const mode = document.querySelector('.mode-pill.active')?.dataset.mode || 'balanced';

  // UI state
  const btn = document.getElementById('generate-btn');
  btn.disabled = true;
  btn.querySelector('.btn-text').textContent = 'Generating...';
  btn.querySelector('.btn-loader').classList.remove('hidden');
  btn.querySelector('.btn-icon').classList.add('hidden');
  document.getElementById('status-dot').className = 'status-dot busy';
  document.getElementById('status-text').textContent = 'Running pipeline...';
  document.getElementById('output-empty').classList.remove('hidden');
  document.getElementById('output-content').classList.add('hidden');
  resetStages();

  try {
    const response = await fetch(`${API}/api/generate/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, mode })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const ev = JSON.parse(line.slice(6));
            handleEvent(ev);
          } catch(e) {}
        }
      }
    }
  } catch(err) {
    alert('Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-text').textContent = 'Generate Schema';
    btn.querySelector('.btn-loader').classList.add('hidden');
    btn.querySelector('.btn-icon').classList.remove('hidden');
    document.getElementById('status-dot').className = 'status-dot';
    document.getElementById('status-text').textContent = 'Ready';
  }
}

function handleEvent(ev) {
  if (!ev.event) return;
  switch(ev.event) {
    case 'stage_start':
      setStage(ev.data.stage, 'active', '⟳ Running');
      document.getElementById('status-text').textContent = ev.data.stage.replace(/_/g,' ');
      break;
    case 'stage_complete':
      const ms = ev.data.metrics?.latency_ms;
      setStage(ev.data.stage, 'success', ms ? `✓ ${ms}ms` : '✓ Done');
      break;
    case 'validation_result':
      setStage('validation', ev.data.passed ? 'success' : 'active',
        ev.data.passed ? `✓ ${ev.data.checks_run} checks` : `⚠ ${ev.data.error_count} errors`);
      break;
    case 'repair_start':
      document.getElementById('status-text').textContent = `Repairing ${ev.data.layer}...`;
      break;
    case 'repair_complete':
      document.getElementById('status-text').textContent = `Repaired ${ev.data.layer}`;
      break;
    case 'complete':
      setStage('runtime_simulation', 'success', '✓ Done');
      currentResult = ev.data;
      renderResult(ev.data);
      break;
    case 'error':
      setStage(ev.data.stage, 'error', '✗ Error');
      break;
  }
}

function renderResult(data) {
  document.getElementById('output-empty').classList.add('hidden');
  document.getElementById('output-content').classList.remove('hidden');

  const m = data.metrics || {};
  const vr = data.validation_report || {};
  const er = data.execution_report || {};
  const s = data.app_schema || {};

  // Metrics bar
  const statusColors = { success: '#10b981', failed: '#ef4444', repaired: '#f59e0b' };
  const mc = document.getElementById('mc-status');
  mc.querySelector('.mc-icon-svg').style.color = statusColors[data.status] || '#10b981';
  document.getElementById('mc-status-text').textContent = data.status || '—';
  document.getElementById('mc-latency').textContent = m.total_latency_ms ? m.total_latency_ms + 'ms' : '—';
  document.getElementById('mc-cost').textContent = m.estimated_cost_usd ? '$' + m.estimated_cost_usd : '—';
  document.getElementById('mc-repairs').textContent = (m.repair_attempts || 0) + ' repairs';
  document.getElementById('mc-model').textContent = m.model_used || '—';

  // Status icon logic
  let statusIcon = 'check-circle-2';
  let statusColorClass = 'text-green';
  if (data.status === 'repaired') {
    statusIcon = 'alert-triangle';
    statusColorClass = 'text-yellow';
  } else if (data.status === 'failed') {
    statusIcon = 'x-circle';
    statusColorClass = 'text-red';
  }

  // Overview
  const og = document.getElementById('overview-grid');
  og.innerHTML = `
    <div class="ov-status-card">
      <div class="ov-status-icon ${statusColorClass}"><i data-lucide="${statusIcon}"></i></div>
      <div class="ov-status-text">
        <h3>${s.app_name || 'Generated App'}</h3>
        <p>${data.intent?.description || ''}</p>
      </div>
    </div>
    ${ovCard(s.db_schema?.length||0,'DB Tables','database')}
    ${ovCard(s.api_schema?.length||0,'API Endpoints','link-2')}
    ${ovCard(s.ui_schema?.length||0,'UI Pages','smartphone')}
    ${ovCard(s.auth_schema?.length||0,'Auth Roles','lock')}
    ${ovCard(vr.checks_run||0,'Checks Run','shield-check')}
    ${ovCard(er.components_verified||0,'Components Verified','server')}
    ${ovCard(m.repair_attempts||0,'Repairs Made','wrench')}
  `;

  // DB
  renderDB(s.db_schema || []);
  // API
  renderAPI(s.api_schema || []);
  // UI
  renderUI(s.ui_schema || []);
  // Auth
  renderAuth(s.auth_schema || [], s.business_logic || {});
  // Business Logic
  renderLogic(s.business_logic || {});
  // Validation
  renderValidation(vr);
  // Execution
  renderExecution(er);
  // Raw JSON
  document.getElementById('raw-json-view').textContent = JSON.stringify(data.app_schema, null, 2);

  // Copy/Download
  document.getElementById('copy-btn').onclick = () => {
    navigator.clipboard.writeText(JSON.stringify(data.app_schema, null, 2));
  };
  document.getElementById('download-btn').onclick = () => {
    const blob = new Blob([JSON.stringify(data.app_schema, null, 2)], {type:'application/json'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = (s.app_name||'schema').replace(/\s+/g,'_').toLowerCase() + '.json';
    a.click();
  };

  // Re-run Lucide replacement for newly created elements
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function ovCard(num, label, icon) {
  return `<div class="ov-card"><div class="ov-num">${num}</div><div class="ov-label"><i data-lucide="${icon}" class="ov-icon"></i> ${label}</div></div>`;
}

function renderDB(tables) {
  const el = document.getElementById('db-viewer');
  el.innerHTML = tables.map(t => `
    <div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="database" class="sc-icon-svg"></i>
        <span class="sc-title">${t.name}</span>
        <span class="sc-badge">${t.columns?.length||0} cols</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${(t.columns||[]).map(c => `
            <div class="field-row">
              <span class="field-name">${c.name}</span>
              <span class="field-type">${c.type}</span>
              <span class="field-flags">
                ${c.primary_key?'<span class="flag flag-pk">PK</span>':''}
                ${c.foreign_key?`<span class="flag flag-fk">FK→${c.foreign_key}</span>`:''}
                ${!c.nullable&&!c.primary_key?'<span class="flag flag-req">NOT NULL</span>':''}
                ${c.unique?'<span class="flag flag-uniq">UNIQUE</span>':''}
              </span>
            </div>`).join('')}
        </div>
        ${t.description?`<p style="font-size:12px;color:var(--muted);margin-top:10px">${t.description}</p>`:''}
      </div>
    </div>`).join('');
}

function renderAPI(endpoints) {
  const el = document.getElementById('api-viewer');
  const groups = {};
  endpoints.forEach(e => {
    const parts = e.path.split('/'); const key = parts[2] || 'root';
    if(!groups[key]) groups[key]=[];
    groups[key].push(e);
  });
  el.innerHTML = Object.entries(groups).map(([grp, eps]) => `
    <div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="link-2" class="sc-icon-svg"></i>
        <span class="sc-title">/${grp}</span>
        <span class="sc-badge">${eps.length} endpoints</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${eps.map(e=>`
            <div class="endpoint-row">
              <span class="method-badge method-${e.method}">${e.method}</span>
              <span class="ep-path">${e.path}</span>
              <span class="ep-roles">${(e.roles||[]).join(', ')}</span>
              ${e.auth_required?'<span class="ep-auth" title="Auth required"><i data-lucide="lock" style="width:12px;height:12px"></i></span>':''}
            </div>`).join('')}
        </div>
      </div>
    </div>`).join('');
}

function renderUI(pages) {
  const el = document.getElementById('ui-viewer');
  el.innerHTML = pages.map(p => `
    <div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="smartphone" class="sc-icon-svg"></i>
        <span class="sc-title">${p.name}</span>
        <span class="sc-badge">${p.route}</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div style="font-size:12px;color:var(--muted);margin-bottom:8px; display:flex; gap:6px; align-items:center;">
          <i data-lucide="users" style="width:13px; height:13px"></i> Roles: ${(p.accessible_by||[]).join(', ')||'all'}
        </div>
        <div class="field-list">
          ${(p.components||[]).map(c=>`
            <div class="field-row">
              <span class="field-name">${c.id}</span>
              <span class="field-type">${c.type}</span>
              <span style="font-size:11px;color:var(--muted)">${c.entity||''} ${c.api_endpoint||''}</span>
            </div>`).join('')}
        </div>
      </div>
    </div>`).join('');
}

function renderAuth(roles, logic) {
  const el = document.getElementById('auth-viewer');
  el.innerHTML = roles.map(r => `
    <div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="lock" class="sc-icon-svg"></i>
        <span class="sc-title">${r.name}</span>
        <span class="sc-badge">${(r.permissions||[]).length} perms</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${(r.permissions||[]).map(p=>`<div class="field-row"><span class="field-name">${p}</span></div>`).join('')}
        </div>
        ${r.inherits?`<p style="font-size:12px;color:var(--muted);margin-top:8px; display:flex; gap:6px; align-items:center;">
          <i data-lucide="git-merge" style="width:13px;height:13px"></i> Inherits: ${r.inherits}
        </p>`:''}
      </div>
    </div>`).join('');
}

function renderLogic(logic) {
  const el = document.getElementById('logic-viewer');
  const gates = logic.gates||[];
  const triggers = logic.triggers||[];
  el.innerHTML = `
    ${gates.length?`<div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="git-commit" class="sc-icon-svg text-purple"></i>
        <span class="sc-title">Business Gates</span>
        <span class="sc-badge">${gates.length}</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${gates.map(g=>`<div class="field-row">
            <span class="field-name">${g.name}</span>
            <span style="font-size:12px;color:var(--muted);flex:1">${g.condition}</span>
          </div>`).join('')}
        </div>
      </div></div>`:''}
    ${triggers.length?`<div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="zap" class="sc-icon-svg text-yellow"></i>
        <span class="sc-title">Triggers</span>
        <span class="sc-badge">${triggers.length}</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${triggers.map(t=>`<div class="field-row">
            <span class="field-name">${t.event}</span>
            <span style="font-size:12px;color:var(--muted)">${t.action}</span>
          </div>`).join('')}
        </div>
      </div></div>`:''}`;
}

function renderValidation(vr) {
  const el = document.getElementById('validation-viewer');
  const issues = vr.issues||[];
  const warnings = vr.warnings||[];
  const statusIcon = vr.passed ? 'check-circle-2' : 'x-circle';
  const statusClass = vr.passed ? 'text-green' : 'text-red';
  el.innerHTML = `
    <div class="schema-card">
      <div class="schema-card-header">
        <i data-lucide="${statusIcon}" class="sc-icon-svg ${statusClass}"></i>
        <span class="sc-title">Validation ${vr.passed?'Passed':'Failed'}</span>
        <span class="sc-badge">${vr.checks_run||0} checks</span>
      </div>
    </div>
    ${issues.length?`<div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="x-circle" class="sc-icon-svg text-red"></i>
        <span class="sc-title">Errors (${issues.length})</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${issues.map(i=>`<div class="check-row">
            <i data-lucide="minus-circle" class="check-icon-svg text-red"></i>
            <span class="check-text"><strong>[${i.layer}]</strong> ${i.message}</span>
          </div>`).join('')}
        </div>
      </div></div>`:''}
    ${warnings.length?`<div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="alert-triangle" class="sc-icon-svg text-yellow"></i>
        <span class="sc-title">Warnings (${warnings.length})</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${warnings.map(w=>`<div class="check-row">
            <i data-lucide="alert-circle" class="check-icon-svg text-yellow"></i>
            <span class="check-text"><strong>[${w.layer}]</strong> ${w.message}</span>
          </div>`).join('')}
        </div>
      </div></div>`:''}`;
}

function renderExecution(er) {
  const el = document.getElementById('execution-viewer');
  const checks = er.checks||[];
  const pass = checks.filter(c=>c.status==='pass').length;
  const fail = checks.filter(c=>c.status==='fail').length;
  const warn = checks.filter(c=>c.status==='warn').length;
  const statusIcon = er.executable ? 'check-circle-2' : 'x-circle';
  const statusClass = er.executable ? 'text-green' : 'text-red';
  el.innerHTML = `
    <div class="schema-card">
      <div class="schema-card-header">
        <i data-lucide="${statusIcon}" class="sc-icon-svg ${statusClass}"></i>
        <span class="sc-title">Runtime Simulation ${er.executable?'Passed':'Failed'}</span>
        <span class="sc-badge">${er.components_verified||0} verified</span>
      </div>
    </div>
    <div style="display:flex;gap:8px;margin:8px 0">
      <div class="ov-card" style="flex:1;padding:12px"><div class="ov-num text-green">${pass}</div><div class="ov-label">Pass</div></div>
      <div class="ov-card" style="flex:1;padding:12px"><div class="ov-num text-yellow">${warn}</div><div class="ov-label">Warn</div></div>
      <div class="ov-card" style="flex:1;padding:12px"><div class="ov-num text-red">${fail}</div><div class="ov-label">Fail</div></div>
    </div>
    <div class="schema-card">
      <div class="schema-card-header" onclick="toggleCard(this)">
        <i data-lucide="server" class="sc-icon-svg"></i>
        <span class="sc-title">All Checks</span>
        <span class="sc-toggle"><i data-lucide="chevron-down"></i></span>
      </div>
      <div class="schema-card-body">
        <div class="field-list">
          ${checks.map(c=>{
            let cIcon = 'check-circle';
            let cClass = 'text-green';
            if (c.status === 'warn') { cIcon = 'alert-triangle'; cClass = 'text-yellow'; }
            else if (c.status === 'fail') { cIcon = 'x-circle'; cClass = 'text-red'; }
            return `<div class="check-row">
              <i data-lucide="${cIcon}" class="check-icon-svg ${cClass}"></i>
              <span class="check-text"><strong>${c.component}</strong><br><span style="color:var(--muted)">${c.detail}</span></span>
            </div>`;
          }).join('')}
        </div>
      </div>
    </div>`;
}

function toggleCard(header) {
  const body = header.nextElementSibling;
  const tog = header.querySelector('.sc-toggle');
  body.classList.toggle('open');
  header.classList.toggle('open');
  if(tog) tog.classList.toggle('open');
}

// History
async function loadHistory() {
  const el = document.getElementById('history-grid');
  el.innerHTML = '<div class="loading-msg">Loading...</div>';
  try {
    const r = await fetch(`${API}/api/runs`);
    const runs = await r.json();
    if(!runs.length){el.innerHTML='<div class="loading-msg">No runs yet.</div>';return;}
    el.innerHTML = runs.map(run=>{
      const hClass = run.status === 'success' ? 'bg-green' : (run.status === 'repaired' ? 'bg-yellow' : 'bg-red');
      return `
      <div class="history-card">
        <div class="hc-top">
          <div class="hc-status ${hClass}"></div>
          <div class="hc-prompt">${run.prompt}</div>
        </div>
        <div class="hc-meta">
          <span>${run.status}</span>
          <span>${run.mode} mode</span>
          <span>${run.total_latency_ms||0}ms</span>
          <span>${run.repair_attempts||0} repairs</span>
          <span>$${(run.estimated_cost_usd||0).toFixed(5)}</span>
        </div>
        <div style="font-size:11px;color:var(--muted); margin-top: 4px;">${run.created_at?.substring(0,19).replace('T',' ')||''}</div>
      </div>`;
    }).join('');
  } catch(e){el.innerHTML='<div class="loading-msg">Error loading history.</div>';}
}

document.getElementById('refresh-history').addEventListener('click', loadHistory);

// Eval test cases render
function renderTestCases() {
  const CASES = [
    {id:'real_01',cat:'CRM',prompt:'CRM with login, contacts, deals, RBAC, payments'},
    {id:'real_02',cat:'LMS',prompt:'LMS with courses, video lessons, quizzes, certificates'},
    {id:'real_03',cat:'HR Tool',prompt:'HR system with employees, leave, payroll, reviews'},
    {id:'real_04',cat:'E-commerce',prompt:'Multi-vendor marketplace with Stripe checkout'},
    {id:'real_05',cat:'Project Mgmt',prompt:'Jira-like with sprints, kanban, time tracking'},
    {id:'real_06',cat:'Invoicing',prompt:'Invoice SaaS with recurring billing and reports'},
    {id:'real_07',cat:'Healthcare',prompt:'Telemedicine with appointments, video, prescriptions'},
    {id:'real_08',cat:'Events',prompt:'Event platform with tickets, QR codes, attendees'},
    {id:'real_09',cat:'Inventory',prompt:'Warehouse management with stock alerts, POs'},
    {id:'real_10',cat:'Analytics',prompt:'SaaS analytics with custom dashboards and KPIs'},
    {id:'edge_01',cat:'vague',prompt:'build an app'},
    {id:'edge_02',cat:'conflicting',prompt:'Private and public social network simultaneously'},
    {id:'edge_03',cat:'incomplete',prompt:'a dashboard'},
    {id:'edge_04',cat:'circular',prompt:'Admins managed by super-admins managed by admins'},
    {id:'edge_05',cat:'no-entities',prompt:'users do things, admins manage stuff, some reporting'},
    {id:'edge_06',cat:'scale',prompt:'Simple 1-page app for 1 billion concurrent users'},
    {id:'edge_07',cat:'jargon',prompt:'CQRS event-driven microservices for a todo app'},
    {id:'edge_08',cat:'impossible',prompt:'App that generates revenue with zero users'},
    {id:'edge_09',cat:'emoji',prompt:'🏋️📊💪📱🔔💰'},
    {id:'edge_10',cat:'overload',prompt:'CRM + LMS + e-commerce + AI chatbot + blockchain + AR'},
  ];
  const el = document.getElementById('test-cases-grid');
  el.innerHTML = CASES.map(c=>`
    <div class="tc-item">
      <span class="tc-id">${c.id}</span>
      <span class="tc-cat">${c.cat}</span>
      <span class="tc-prompt">${c.prompt}</span>
    </div>`).join('');
}

document.getElementById('run-eval-btn').addEventListener('click', async () => {
  const mode = document.getElementById('eval-mode').value;
  const n = parseInt(document.getElementById('eval-cases').value);
  const btn = document.getElementById('run-eval-btn');
  btn.innerHTML = '<i class="btn-loader-eval"></i> Running...'; btn.disabled = true;
  try {
    const r = await fetch(`${API}/api/eval/run?max_cases=${n}&mode=${mode}`, {method:'POST'});
    const d = await r.json();
    renderEvalResults(d);
  } catch(e){alert('Eval error: '+e.message);}
  finally{btn.innerHTML='<i data-lucide="play" class="btn-icon"></i> Run Evaluation'; btn.disabled=false; if(window.lucide){window.lucide.createIcons();}}
});

function renderEvalResults(d) {
  const summary = document.getElementById('eval-summary');
  summary.innerHTML = `
    <div class="em-stat"><div class="em-num">${(d.success_rate*100).toFixed(0)}%</div><div class="em-lbl">Success Rate</div></div>
    <div class="em-stat"><div class="em-num">${d.avg_latency_ms||0}ms</div><div class="em-lbl">Avg Latency</div></div>
    <div class="em-stat"><div class="em-num">${d.avg_retries||0}</div><div class="em-lbl">Avg Retries</div></div>
    <div class="em-stat"><div class="em-num">${((d.avg_completeness||0)*100).toFixed(0)}%</div><div class="em-lbl">Completeness</div></div>`;

  const cats = Object.keys(d.by_category||{});
  const rates = cats.map(c=>(d.by_category[c].success_rate*100).toFixed(0));
  const lats  = (d.results||[]).map(r=>r.latency_ms);

  if(successChart) successChart.destroy();
  if(latencyChart) latencyChart.destroy();

  const ctxS = document.getElementById('chart-success').getContext('2d');
  successChart = new Chart(ctxS, {
    type:'bar',
    data:{labels:cats,datasets:[{label:'Success %',data:rates,backgroundColor:'rgba(124,58,237,0.6)',borderColor:'#7c3aed',borderWidth:1}]},
    options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,max:100,ticks:{color:'#64748b'}},x:{ticks:{color:'#64748b'}}},responsive:true}
  });

  const ctxL = document.getElementById('chart-latency').getContext('2d');
  latencyChart = new Chart(ctxL, {
    type:'line',
    data:{labels:(d.results||[]).map(r=>r.test_id),datasets:[{label:'ms',data:lats,borderColor:'#a855f7',backgroundColor:'rgba(168,85,247,0.1)',tension:0.4,fill:true}]},
    options:{plugins:{legend:{display:false}},scales:{y:{ticks:{color:'#64748b'}},x:{ticks:{color:'#64748b',maxRotation:45}}},responsive:true}
  });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  renderTestCases();
  if (window.lucide) {
    window.lucide.createIcons();
  }
});
