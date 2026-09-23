(() => {
  'use strict';

  const VERSION = '1.0';
  const STORAGE_KEY = 'prism.governance.v1';
  const ROLES = {
    Viewer: { view: true, analyse: false, propose: false, approve: false, administer: false },
    Analyst: { view: true, analyse: true, propose: true, approve: false, administer: false },
    Manager: { view: true, analyse: true, propose: true, approve: true, administer: false },
    Admin: { view: true, analyse: true, propose: true, approve: true, administer: true }
  };
  const CLASSIFICATIONS = ['Public', 'Internal', 'Confidential', 'Restricted / PII'];
  const APPROVALS = ['Draft', 'Pending review', 'Approved', 'Rejected'];

  const nowIso = () => new Date().toISOString();
  const id = prefix => `${prefix}-${Date.now().toString(36).toUpperCase()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeDataset = value => String(value || 'DATASET').replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').toUpperCase() || 'DATASET';
  const stamp = date => {
    const d = date || new Date();
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;
  };

  function load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || { events: [], controls: [] }; }
    catch (_) { return { events: [], controls: [] }; }
  }
  function save(state) { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }

  function evidence(control) {
    return {
      evidence_id: id('EVD-GOV'),
      classification: 'governance metadata; not analytical or causal evidence',
      method: 'PRISM static governance control capture',
      method_version: VERSION,
      assumptions: ['Role enforcement is simulated in the static edition.', 'Human approval is represented by an accountable recorded action.'],
      limitations: ['No SSO/RBAC backend is configured.', 'Browser-local audit events are not an immutable enterprise audit trail.', 'Data classification is user-supplied and requires organisational policy validation.'],
      source: control.control_id
    };
  }

  function canTransition(role, target) {
    if (target === 'Approved' || target === 'Rejected') return !!ROLES[role]?.approve;
    if (target === 'Pending review') return !!ROLES[role]?.propose;
    return !!ROLES[role]?.view;
  }

  function audit(state, actor, role, action, objectType, objectId, detail) {
    const event = {
      audit_id: id('AUD'), timestamp: nowIso(), actor, role, action,
      object_type: objectType, object_id: objectId, detail,
      source_mode: 'browser-local static edition',
      integrity_note: 'Local audit event; not tamper-evident or centrally attested.'
    };
    state.events.unshift(event);
    state.events = state.events.slice(0, 100);
    return event;
  }

  function createControl(input, state) {
    const role = input.role;
    if (!ROLES[role]) throw new Error('Choose a valid governance role.');
    if (!input.actor.trim()) throw new Error('An accountable actor is required.');
    if (!input.asset.trim()) throw new Error('Name the governed asset or decision.');
    if (!CLASSIFICATIONS.includes(input.classification)) throw new Error('Choose a valid data classification.');
    if (!APPROVALS.includes(input.approval)) throw new Error('Choose a valid approval state.');
    if (!canTransition(role, input.approval)) throw new Error(`${role} cannot set approval state to ${input.approval}. Manager or Admin approval is required.`);
    if (input.classification === 'Restricted / PII' && !input.piiBasis.trim()) throw new Error('Restricted / PII classification requires a handling or lawful-basis note.');

    const control = {
      control_id: id('GOV'),
      asset: input.asset.trim(), actor: input.actor.trim(), role,
      permissions: ROLES[role], approval_state: input.approval,
      data_classification: input.classification,
      pii_handling_basis: input.piiBasis.trim() || null,
      model_governance: {
        model_or_method: input.model.trim() || 'Not specified',
        intended_use: input.intendedUse.trim() || 'Not specified',
        risk_tier: input.riskTier,
        human_approval_required: true,
        causal_claims_permitted: false
      },
      created_at: nowIso(), source_mode: 'browser-local static edition'
    };
    control.evidence = evidence(control);
    state.controls.unshift(control);
    state.controls = state.controls.slice(0, 50);
    audit(state, control.actor, role, 'governance_control_recorded', 'governance_control', control.control_id, `${control.approval_state}; ${control.data_classification}`);
    save(state);
    return control;
  }

  function exportAudit(state, dataset) {
    const payload = {
      module: 'Enterprise Governance', version: VERSION,
      generated_at: nowIso(), dataset: safeDataset(dataset),
      execution_mode: 'Local', uploaded_data_transmitted: false,
      method: 'browser-local governance event capture',
      classification: 'governance/audit metadata; causal-not-established',
      controls: state.controls,
      audit_events: state.events,
      assumptions: ['Actors and classifications are user-entered in the static edition.'],
      limitations: ['This export is not an immutable audit ledger.', 'Role permissions are simulated until enterprise identity and policy enforcement are connected.'],
      security: { secrets_exported: false, uploaded_data_transmitted: false }
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `PRISM_AUDIT_${safeDataset(dataset)}_${stamp()}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 0);
  }

  function render() {
    const root = document.querySelector('[data-prism-governance]');
    if (!root) return;
    const state = load();
    const roleOptions = Object.keys(ROLES).map(x => `<option>${x}</option>`).join('');
    const classOptions = CLASSIFICATIONS.map(x => `<option>${x}</option>`).join('');
    const approvalOptions = APPROVALS.map(x => `<option>${x}</option>`).join('');
    root.innerHTML = `
      <section class="gov-card"><h2>Governance control</h2><p class="muted">Static-edition permission simulation and accountable approval capture. Material actions remain human-approved.</p>
        <div class="gov-grid">
          <label>Actor<input id="gov-actor" placeholder="Accountable person or role"></label>
          <label>Role<select id="gov-role">${roleOptions}</select></label>
          <label>Governed asset<input id="gov-asset" placeholder="Dataset, model, strategy or decision ID"></label>
          <label>Data classification<select id="gov-class">${classOptions}</select></label>
          <label>Approval state<select id="gov-approval">${approvalOptions}</select></label>
          <label>PII / handling basis<input id="gov-pii" placeholder="Required for Restricted / PII"></label>
          <label>Model / method<input id="gov-model" placeholder="Optional model or analytical method"></label>
          <label>Model risk tier<select id="gov-risk"><option>Low</option><option>Moderate</option><option>High</option></select></label>
          <label class="wide">Intended use<input id="gov-use" placeholder="What this model/method is approved to support"></label>
        </div>
        <div class="gov-actions"><button id="gov-record">Record governance control</button><button id="gov-download" class="secondary">Download Audit Log</button><button id="gov-clear" class="secondary">Clear local governance history</button></div>
        <p id="gov-status" role="status" aria-live="polite"></p>
      </section>
      <section class="gov-card"><h2>Role matrix</h2><div class="table-wrap"><table><thead><tr><th>Role</th><th>View</th><th>Analyse</th><th>Propose</th><th>Approve</th><th>Admin</th></tr></thead><tbody>${Object.entries(ROLES).map(([r,p]) => `<tr><td>${r}</td>${['view','analyse','propose','approve','administer'].map(k=>`<td>${p[k]?'✓':'—'}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section>
      <section class="gov-card"><h2>Recent controls</h2><div id="gov-controls"></div></section>
      <section class="gov-card"><h2>Audit events</h2><div id="gov-events"></div></section>`;

    const paint = () => {
      root.querySelector('#gov-controls').innerHTML = state.controls.length ? state.controls.map(c => `<article class="gov-item"><strong>${esc(c.control_id)} · ${esc(c.asset)}</strong><span>${esc(c.approval_state)} · ${esc(c.data_classification)}</span><small>${esc(c.actor)} (${esc(c.role)}) · ${esc(c.evidence.evidence_id)}</small></article>`).join('') : '<p class="muted">No governance controls recorded locally.</p>';
      root.querySelector('#gov-events').innerHTML = state.events.length ? state.events.slice(0,20).map(e => `<article class="gov-item"><strong>${esc(e.audit_id)} · ${esc(e.action)}</strong><span>${esc(e.actor)} (${esc(e.role)})</span><small>${esc(e.timestamp)} · ${esc(e.integrity_note)}</small></article>`).join('') : '<p class="muted">No local audit events yet.</p>';
    };
    paint();
    root.querySelector('#gov-record').onclick = () => {
      const status = root.querySelector('#gov-status');
      try {
        const c = createControl({ actor:root.querySelector('#gov-actor').value, role:root.querySelector('#gov-role').value, asset:root.querySelector('#gov-asset').value, classification:root.querySelector('#gov-class').value, approval:root.querySelector('#gov-approval').value, piiBasis:root.querySelector('#gov-pii').value, model:root.querySelector('#gov-model').value, riskTier:root.querySelector('#gov-risk').value, intendedUse:root.querySelector('#gov-use').value }, state);
        status.textContent = `Recorded ${c.control_id}. Governance metadata is not proof of analytical correctness or causality.`; paint();
      } catch (e) { status.textContent = e.message; }
    };
    root.querySelector('#gov-download').onclick = () => exportAudit(state, document.body.dataset.dataset || 'GOVERNANCE');
    root.querySelector('#gov-clear').onclick = () => { localStorage.removeItem(STORAGE_KEY); state.controls=[]; state.events=[]; paint(); root.querySelector('#gov-status').textContent='Local governance history cleared.'; };
  }

  window.PRISMGovernance = { ROLES, CLASSIFICATIONS, createControl, canTransition, exportAudit, load };
  document.addEventListener('DOMContentLoaded', render);
})();