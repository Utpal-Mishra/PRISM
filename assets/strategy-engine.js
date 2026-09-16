(() => {
  "use strict";

  const METHOD_VERSION = "strategy-2.0.0";
  const CLASSIFICATION = "decision-support synthesis; causal-not-established";
  const STORE_KEY = "prism.strategy.v2";
  let latest = null;

  document.addEventListener("DOMContentLoaded", () => setTimeout(init, 0));

  function init() {
    const view = document.getElementById("view-strategy");
    if (!view) return;
    const intro = view.querySelector(".section-intro");
    if (intro) intro.innerHTML = `<div><p class="eyebrow">DECIDE</p><h2>Strategy Engine 2.0</h2><p>Convert observed analytical evidence and scenario sensitivity into an auditable strategy proposal. PRISM supports accountable decisions; it does not establish causal effects.</p></div><button id="downloadStrategyPack" class="secondary-button" type="button">Download Strategy Pack</button>`;
    const host = document.getElementById("strategyCards");
    if (host) host.outerHTML = `<div id="strategyV2"><article class="panel"><div class="control-row three strategy-v2-controls"><label>Primary KPI<select id="strategyMetric"></select></label><label>Decision owner<input id="strategyOwner" type="text" placeholder="Accountable owner" maxlength="80"/></label><label>Review date<input id="strategyReview" type="date"/></label><button id="buildStrategy" class="primary-button" type="button">Build strategy proposal</button></div><div id="strategySummary" class="metric-grid small"></div><div id="strategyProposal" class="strategy-grid"></div></article></div>`;
    document.getElementById("buildStrategy")?.addEventListener("click", build);
    document.getElementById("downloadStrategyPack")?.addEventListener("click", download);
    populate();
    setTimeout(populate, 400);
  }

  function appState() { return window.PRISM_STATE || window.prismState || null; }
  function data() { const s=appState(); return s?.data || []; }
  function profile() { return appState()?.profile || null; }
  function numericColumns() { return profile()?.numericColumns || inferNumeric(data()); }
  function inferNumeric(rows) { if(!rows.length)return[]; return Object.keys(rows[0]).filter(k=>rows.filter(r=>Number.isFinite(Number(r[k]))).length>=Math.max(5,rows.length*.6)); }
  function populate() {
    const sel=document.getElementById("strategyMetric"); if(!sel)return;
    const cols=numericColumns(); if(!cols.length){sel.innerHTML="<option>No usable KPI</option>";return;}
    const current=sel.value; sel.innerHTML=cols.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join(""); if(cols.includes(current))sel.value=current;
    const review=document.getElementById("strategyReview"); if(review&&!review.value){const d=new Date();d.setDate(d.getDate()+30);review.value=d.toISOString().slice(0,10);}
  }
  function build() {
    populate(); const rows=data(), metric=document.getElementById("strategyMetric")?.value;
    if(!metric||rows.length<8){renderEmpty("At least 8 records and one usable numerical KPI are required to create a strategy proposal.");return;}
    const vals=rows.map(r=>Number(r[metric])).filter(Number.isFinite); if(vals.length<8){renderEmpty("The selected KPI does not contain enough usable observations.");return;}
    const mean=vals.reduce((a,b)=>a+b,0)/vals.length, recent=vals.slice(-Math.max(3,Math.floor(vals.length*.2))), recentMean=recent.reduce((a,b)=>a+b,0)/recent.length;
    const movement=mean===0?null:(recentMean-mean)/Math.abs(mean)*100;
    const owner=(document.getElementById("strategyOwner")?.value||"").trim()||"Unassigned — human owner required";
    const review=document.getElementById("strategyReview")?.value||null;
    const now=new Date(), dataset=datasetMeta(), id=`STR-${stamp(now)}-${slug(metric).slice(0,12).toUpperCase()}`;
    const evidenceId=`EVD-${stamp(now)}-${slug(metric).slice(0,12).toUpperCase()}`;
    const direction=movement===null?"requires baseline review":movement<0?"is below its full-dataset baseline":"is above its full-dataset baseline";
    const magnitude=movement===null?"not estimable":`${Math.abs(movement).toFixed(1)}%`;
    const problem=`${metric} ${direction}; observed recent-vs-baseline movement is ${magnitude}.`;
    const hypothesis=`The observed movement may be concentrated in identifiable segments or operating drivers. This is a testable hypothesis, not a causal conclusion.`;
    const action=`Review the strongest PRISM investigation/driver evidence for ${metric}, select one controllable intervention, and validate it through a bounded pilot before wider rollout.`;
    const alternative=`Maintain the current operating approach while collecting another review period and testing whether the observed movement persists.`;
    const risk=Math.abs(movement||0)>=20?"High":Math.abs(movement||0)>=8?"Medium":"Low–Medium";
    const confidence=vals.length>=100?"Moderate":vals.length>=30?"Low–Moderate":"Low";
    latest={strategy_id:id,dataset,evidence_ids:[evidenceId],problem,evidence:{evidence_id:evidenceId,metric,sample_size:vals.length,full_dataset_mean:mean,recent_window_mean:recentMean,recent_window_records:recent.length,observed_movement_pct:movement,method:"Recent-window descriptive comparison against full-dataset mean",classification:"descriptive; causal-not-established"},hypothesis,recommended_action:action,alternatives:[alternative],expected_impact:{statement:"Impact is not asserted from observational data. Quantify expected impact with Scenario Studio or a controlled validation before approval.",value:null},confidence,risk,cost_effort_proxy:"Medium — analyst review, domain-owner validation and bounded pilot",dependencies:["Validated source data","Relevant driver/investigation evidence","Accountable domain owner","Pilot measurement plan"],kpi_to_monitor:metric,owner,review_date:review,status:"Proposed — human review required",method_version:METHOD_VERSION,classification:CLASSIFICATION,assumptions:["Recent records are sufficiently comparable to the broader dataset for descriptive screening.","No causal effect is inferred from the observed movement."],limitations:["Row order may not represent time unless the source is chronologically ordered.","Expected impact requires scenario or experimental evidence.","Domain constraints and implementation cost are not inferred automatically."],generated_at:now.toISOString(),source_mode:dataset.source_mode};
    try{localStorage.setItem(STORE_KEY,JSON.stringify(latest));}catch(_e){}
    render();
  }
  function renderEmpty(msg){latest=null;document.getElementById("strategySummary").innerHTML="";document.getElementById("strategyProposal").innerHTML=`<article class="strategy-card"><p>${esc(msg)}</p></article>`;}
  function render(){if(!latest)return;const s=latest;document.getElementById("strategySummary").innerHTML=[card("Strategy ID",s.strategy_id,"auditable proposal"),card("Confidence",s.confidence,"evidence strength"),card("Risk",s.risk,"screening indicator"),card("Status",s.status,"accountability")].join("");
    const fields=[["Problem",s.problem],["Evidence",`${s.evidence.metric}: ${fmt(s.evidence.observed_movement_pct)}% recent-vs-baseline movement · n=${s.evidence.sample_size} · ${s.evidence.evidence_id}`],["Hypothesis",s.hypothesis],["Recommended action",s.recommended_action],["Alternative",s.alternatives[0]],["Expected impact",s.expected_impact.statement],["Cost / effort",s.cost_effort_proxy],["Dependencies",s.dependencies.join(" · ")],["KPI to monitor",s.kpi_to_monitor],["Owner",s.owner],["Review date",s.review_date||"Not set"],["Method & limitation",`${s.method_version} · ${s.classification}. ${s.limitations[1]}`]];
    document.getElementById("strategyProposal").innerHTML=fields.map(([k,v])=>`<article class="strategy-card"><p class="eyebrow">${esc(k)}</p><p>${esc(v)}</p></article>`).join("");
  }
  function download(){if(!latest){build();if(!latest)return;}const now=new Date(),name=`PRISM_STRATEGY_${slug(latest.dataset.name)}_${fileStamp(now)}.json`;const blob=new Blob([JSON.stringify({prism_version:"1.1.0",artifact:"Strategy Pack",...latest},null,2)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
  function datasetMeta(){const name=document.getElementById("datasetName")?.textContent?.trim()||"dataset";return{name,id:`DS-${slug(name).toUpperCase().slice(0,32)}`,rows:data().length,source_mode:document.getElementById("datasetMode")?.textContent?.trim()||"Browser-local"};}
  function card(label,value,note){return `<div class="metric-card"><span>${esc(label)}</span><strong>${esc(String(value))}</strong><small>${esc(note)}</small></div>`;}
  function fmt(v){return Number.isFinite(v)?v.toFixed(1):"n/a";} function slug(v){return String(v||"dataset").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")||"dataset";} function stamp(d){return d.toISOString().replace(/[-:TZ.]/g,"").slice(0,14);} function fileStamp(d){const p=n=>String(n).padStart(2,"0");return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`;} function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
})();
