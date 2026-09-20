(() => {
  "use strict";
  const KEY = "prism_connector_config_v1";
  const ADAPTERS = {
    local: { label: "Local file", mode: "Local", fields: [] },
    sql: { label: "SQL pattern", mode: "Connected", fields: ["host", "database", "schema"] },
    rest: { label: "REST API pattern", mode: "Connected", fields: ["base_url", "resource"] },
    cloud_file: { label: "Cloud file pattern", mode: "Connected", fields: ["provider", "path"] }
  };
  const now = () => new Date().toISOString();
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  const safeDataset = () => ((document.getElementById("datasetName")?.textContent || "DATASET").replace(/[^a-z0-9]+/gi,"_").replace(/^_|_$/g,"").toUpperCase() || "DATASET");
  const stamp = () => { const d=new Date(), p=n=>String(n).padStart(2,"0"); return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`; };
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {adapter:"local", refresh:"manual", config:{}, last_checked:null}; } catch { return {adapter:"local",refresh:"manual",config:{},last_checked:null}; } };
  const save = x => localStorage.setItem(KEY, JSON.stringify(x));
  const redact = obj => Object.fromEntries(Object.entries(obj || {}).filter(([k]) => !/(password|secret|token|key|credential|auth)/i.test(k)));
  const evidence = state => ({
    evidence_id:`EVD-CONN-${Date.now().toString(36).toUpperCase()}`,
    classification:"provenance/configuration evidence; not analytical or causal evidence",
    method:"PRISM connector adapter contract v1",
    source_mode:ADAPTERS[state.adapter].mode,
    adapter:state.adapter,
    assumptions:["Connectivity is simulated in the static edition unless an explicit connector runtime is configured.","Health reflects configuration readiness, not remote-system availability."],
    limitations:["No secrets are persisted or exported by this module.","Mock SQL/REST/cloud-file adapters do not transmit uploaded data or make remote requests."],
    generated_at:now()
  });
  function health(state){
    if(state.adapter === "local") return {status:"Local ready", detail:"Browser-local file processing; no remote connection configured."};
    const required=ADAPTERS[state.adapter].fields, missing=required.filter(f=>!String(state.config?.[f]||"").trim());
    return missing.length ? {status:"Needs configuration",detail:`Missing: ${missing.join(", ")}.`} : {status:"Configuration ready",detail:"Required non-secret fields are present. Remote connectivity is not tested in the static edition."};
  }
  function renderFields(state){
    const box=document.getElementById("connectorFields"); if(!box) return;
    const fields=ADAPTERS[state.adapter].fields;
    box.innerHTML = fields.length ? fields.map(f=>`<label>${esc(f.replace(/_/g," "))}<input data-connector-field="${esc(f)}" value="${esc(state.config?.[f]||"")}" placeholder="${esc(f)}" autocomplete="off"/></label>`).join("") : `<p class="tag muted">No remote configuration required. Uploaded files remain in this browser.</p>`;
  }
  function render(){
    const state=load(), a=ADAPTERS[state.adapter], h=health(state);
    const sel=document.getElementById("connectorAdapter"), mode=document.getElementById("connectorMode"), status=document.getElementById("connectorHealth"), meta=document.getElementById("connectorMeta");
    if(sel) sel.value=state.adapter; if(mode) mode.textContent=`${a.mode} mode`; if(status) status.innerHTML=`<strong>${esc(h.status)}</strong><small>${esc(h.detail)}</small>`;
    if(meta) meta.innerHTML=`<div><span class="eyebrow">REFRESH</span><strong>${esc(state.refresh||"manual")}</strong></div><div><span class="eyebrow">LAST CHECKED</span><strong>${esc(state.last_checked ? new Date(state.last_checked).toLocaleString() : "Not checked")}</strong></div><div><span class="eyebrow">PROVENANCE</span><strong>${esc(a.label)}</strong></div>`;
    renderFields(state);
  }
  function collect(){
    const state=load(); state.adapter=document.getElementById("connectorAdapter")?.value || "local"; state.refresh=document.getElementById("connectorRefresh")?.value || "manual"; state.config={};
    document.querySelectorAll("[data-connector-field]").forEach(i=>state.config[i.dataset.connectorField]=i.value.trim()); state.last_checked=now(); return state;
  }
  function download(){
    const state=collect(); save(state); const ev=evidence(state), h=health(state);
    const payload={prism_version:"1.4.0",module:"Enterprise Data Connectors Foundation",dataset:safeDataset(),adapter_contract_version:"1.0",adapter:state.adapter,execution_mode:ADAPTERS[state.adapter].mode,configuration:redact(state.config),refresh:{cadence:state.refresh,last_checked:state.last_checked},health:h,provenance:{adapter_label:ADAPTERS[state.adapter].label,configured_locally:true},evidence:ev,security:{secrets_exported:false,secrets_persisted:false,uploaded_data_transmitted:false},generated_at:now()};
    const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"}), url=URL.createObjectURL(blob), link=document.createElement("a"); link.href=url; link.download=`PRISM_CONNECTOR_${safeDataset()}_${stamp()}.json`; link.click(); setTimeout(()=>URL.revokeObjectURL(url),500);
  }
  function init(){
    if(!document.getElementById("view-connectors")) return;
    const state=load(), sel=document.getElementById("connectorAdapter"), refresh=document.getElementById("connectorRefresh");
    if(sel){ sel.innerHTML=Object.entries(ADAPTERS).map(([k,v])=>`<option value="${k}">${v.label}</option>`).join(""); sel.value=state.adapter; sel.addEventListener("change",()=>{const s=load();s.adapter=sel.value;s.config={};save(s);render();}); }
    if(refresh){refresh.value=state.refresh||"manual";refresh.addEventListener("change",()=>{const s=load();s.refresh=refresh.value;save(s);render();});}
    document.getElementById("saveConnector")?.addEventListener("click",()=>{const s=collect();save(s);render();});
    document.getElementById("downloadConnector")?.addEventListener("click",download);
    render();
  }
  window.PRISMConnectorAdapters={contractVersion:"1.0",adapters:ADAPTERS,health};
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded",init) : init();
})();