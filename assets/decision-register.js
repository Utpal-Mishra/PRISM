(() => {
  "use strict";
  const STORE_KEY="prism.decisions.v1", METHOD_VERSION="decision-register-1.0.0", CLASSIFICATION="organisational decision record; human-approved action; causal-not-established";
  let decisions=[];
  document.addEventListener("DOMContentLoaded",()=>setTimeout(init,0));
  function init(){
    const view=document.getElementById("view-decision"); if(!view)return;
    document.getElementById("createDecision")?.addEventListener("click",createDecision);
    document.getElementById("downloadDecisionRecord")?.addEventListener("click",downloadLatest);
    document.getElementById("clearDecisionRegister")?.addEventListener("click",clearAll);
    load(); render(); setTimeout(prefill,250);
  }
  function state(){return window.PRISM_STATE||window.prismState||null;} function rows(){return state()?.data||[];}
  function dataset(){const name=document.getElementById("datasetName")?.textContent?.trim()||"dataset";return{name,id:`DS-${slug(name).toUpperCase().slice(0,32)}`,rows:rows().length,source_mode:document.getElementById("datasetMode")?.textContent?.trim()||"Browser-local"};}
  function load(){try{const v=JSON.parse(localStorage.getItem(STORE_KEY)||"[]");decisions=Array.isArray(v)?v:[];}catch(_e){decisions=[];}}
  function save(){try{localStorage.setItem(STORE_KEY,JSON.stringify(decisions.slice(0,50)));}catch(_e){}}
  function strategy(){try{return JSON.parse(localStorage.getItem("prism.strategy.v2")||"null");}catch(_e){return null;}}
  function prefill(){const s=strategy();if(!s)return;set("decisionOwner",s.owner?.startsWith("Unassigned")?"":s.owner);set("decisionReview",s.review_date||"");set("decisionAction",s.recommended_action||"");set("decisionAlternative",s.alternatives?.[0]||"");set("decisionOutcome",s.expected_impact?.statement||"");const hint=document.getElementById("decisionStrategyHint");if(hint)hint.textContent=`Linked strategy available: ${s.strategy_id}. Review and approve the decision fields before recording.`;}
  function createDecision(){
    const s=strategy(), owner=value("decisionOwner"), action=value("decisionAction"), review=value("decisionReview"), outcome=value("decisionOutcome"), alternative=value("decisionAlternative");
    if(!owner||!action||!review){notice("Owner, selected action and review date are required. PRISM will not create an unaccountable decision record.");return;}
    if(!s){notice("Build a Strategy Engine 2.0 proposal first so the decision can retain strategy and evidence traceability.");return;}
    if(!s.strategy_id||!Array.isArray(s.evidence_ids)||!s.evidence_ids.length){notice("The linked strategy lacks evidence IDs. Rebuild the strategy proposal before recording a decision.");return;}
    const now=new Date(), d={decision_id:`DEC-${stamp(now)}-${slug(s.kpi_to_monitor||"decision").toUpperCase().slice(0,12)}`,dataset:dataset(),strategy_id:s.strategy_id,evidence_ids:s.evidence_ids,owner,alternatives_considered:[alternative||"No additional alternative recorded"],selected_action:action,expected_outcome:outcome||"Outcome not quantified; define through Scenario Studio or controlled validation.",kpi_to_monitor:s.kpi_to_monitor||null,status:"Approved for bounded validation — human owner recorded",review_date:review,decision_basis:{problem:s.problem,hypothesis:s.hypothesis,confidence:s.confidence,risk:s.risk,method_version:s.method_version,classification:s.classification},method_version:METHOD_VERSION,classification:CLASSIFICATION,assumptions:["The accountable owner has reviewed the linked strategy and evidence before recording this decision.","Expected outcome is a decision expectation, not proof of causal effect."],limitations:["Browser-local persistence is not a substitute for enterprise records management or access control.","PRISM does not verify the identity or authority of the named owner in the static edition.","Observed evidence and scenario sensitivity do not establish causal impact."],created_at:now.toISOString(),source_mode:dataset().source_mode};
    decisions.unshift(d);save();render();notice(`Decision ${d.decision_id} recorded locally with linked strategy and evidence.`);
  }
  function render(){const host=document.getElementById("decisionRegister");if(!host)return;if(!decisions.length){host.innerHTML='<div class="insight-item"><strong>No decisions recorded</strong><p>Create a reviewed Strategy Engine 2.0 proposal, then record the accountable decision here.</p></div>';return;}host.innerHTML=decisions.slice(0,12).map(d=>`<article class="strategy-card"><p class="eyebrow">${esc(d.decision_id)}</p><h3>${esc(d.kpi_to_monitor||"Decision")}</h3><p><strong>Action:</strong> ${esc(d.selected_action)}</p><p><strong>Owner:</strong> ${esc(d.owner)} · <strong>Review:</strong> ${esc(d.review_date)}</p><p><strong>Traceability:</strong> ${esc(d.strategy_id)} · ${esc(d.evidence_ids.join(", "))}</p><p><strong>Status:</strong> ${esc(d.status)}</p><small>${esc(d.classification)}</small></article>`).join("");}
  function downloadLatest(){if(!decisions.length){notice("Record a decision before downloading a Decision Record.");return;}const d=decisions[0],now=new Date(),name=`PRISM_DECISION_${slug(d.dataset.name)}_${fileStamp(now)}.json`;download(name,{prism_version:"1.2.0",artifact:"Decision Record",...d});}
  function clearAll(){decisions=[];save();render();notice("Browser-local Decision Register cleared.");}
  function notice(msg){const n=document.getElementById("notice");if(n){n.textContent=msg;n.classList.remove("hidden");setTimeout(()=>n.classList.add("hidden"),6000);}}
  function set(id,v){const e=document.getElementById(id);if(e&&!e.value)e.value=v;} function value(id){return(document.getElementById(id)?.value||"").trim();}
  function download(name,obj){const b=new Blob([JSON.stringify(obj,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(b);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
  function slug(v){return String(v||"dataset").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")||"dataset";} function stamp(d){return d.toISOString().replace(/[-:TZ.]/g,"").slice(0,14);} function fileStamp(d){const p=n=>String(n).padStart(2,"0");return`${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;} function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
})();
