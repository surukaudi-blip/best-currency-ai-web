(function(){
  if(window.__BC_STOCKS_DECISION_LAYER__) return;
  window.__BC_STOCKS_DECISION_LAYER__=true;
  if((location.pathname.split('/').pop()||'')!=='stocks.html') return;

  const css=`
    .stock10c-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:12px}.stock10c-head h2{margin:0;font-size:1.14rem}.stock10c-head p{margin:5px 0 0;color:#97a5ba;font-size:.73rem}.stock10c-badge{display:inline-flex;align-items:center;border:1px solid rgba(240,163,47,.22);border-radius:999px;padding:6px 9px;color:#f0a32f;background:rgba(240,163,47,.10);font:800 .57rem Inter,system-ui}.stock10c-badge.ready{color:#3bd69a;background:rgba(59,214,154,.10);border-color:rgba(59,214,154,.2)}
    .stock10c-tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}.stock10c-tab{appearance:none;border:1px solid rgba(148,163,184,.15);background:#0d1420;color:#97a5ba;border-radius:999px;padding:7px 10px;font:800 .62rem Inter;cursor:pointer}.stock10c-tab.active{background:#2fd3ee;color:#04121a;border-color:transparent}
    .stock10c-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.stock10c-card{border:1px solid rgba(148,163,184,.15);border-radius:12px;padding:12px;background:rgba(17,26,41,.52)}.stock10c-card .l{font-size:.54rem;color:#97a5ba;text-transform:uppercase;letter-spacing:.07em}.stock10c-card .v{font-size:1rem;font-weight:900;margin-top:4px;color:#e7ecf4}.stock10c-card .n{font-size:.58rem;color:#68788f;margin-top:4px}.stock10c-card .score{font-size:.65rem;color:#2fd3ee;font-weight:800}.stock10c-two{display:grid;grid-template-columns:1fr;gap:10px;margin-top:10px}.stock10c-panel{border:1px solid rgba(148,163,184,.15);border-radius:12px;padding:13px;background:rgba(13,20,32,.72)}.stock10c-panel h3{font-size:.72rem;margin:0 0 8px}.stock10c-list{display:grid;gap:7px}.stock10c-item{font-size:.63rem;color:#97a5ba;line-height:1.45;padding:8px 9px;border:1px solid rgba(148,163,184,.12);border-radius:9px;background:rgba(17,26,41,.42)}.stock10c-item b{color:#dce5f1}.stock10c-item.high b{color:#f26d6d}.stock10c-item.moderate b{color:#f0a32f}.stock10c-guard{margin-top:10px;padding:11px;border:1px solid rgba(47,211,238,.22);border-radius:11px;color:#97a5ba;font-size:.64rem;line-height:1.55}.stock10c-guard b{color:#2fd3ee}.stock10c-empty{padding:22px;border:1px dashed rgba(148,163,184,.28);border-radius:13px;color:#97a5ba;font-size:.72rem;text-align:center}.state-supportive{color:#3bd69a!important}.state-pressured{color:#f26d6d!important}.state-mixed,.state-moderate{color:#f0a32f!important}.state-high{color:#f26d6d!important}.state-low{color:#3bd69a!important}
    @media(min-width:760px){.stock10c-grid{grid-template-columns:repeat(6,minmax(0,1fr))}.stock10c-two{grid-template-columns:1fr 1fr}}
  `;
  const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);

  const anchor=document.getElementById('stocks-market-layer');
  const section=document.createElement('section');section.id='stocks-decision-layer';
  section.innerHTML=`<div class="wrap"><div class="stock10c-head"><div><h2>Stocks Decision Intelligence · Stage 10C</h2><p>SEC official evidence + daily market context combined through a transparent pre-validation reasoning layer.</p></div><span class="stock10c-badge" id="stock10cBadge">EXPERIMENTAL · PRE-VALIDATION</span></div><div class="stock10c-tabs" id="stock10cTabs"></div><div class="card"><div id="stock10cPane" class="stock10c-empty">Run <b>Refresh Stocks Decision Intelligence</b> after Stage 10A and 10B are ready. Stage 10C does not generate BUY/SELL or profit probability.</div></div></div>`;
  if(anchor) anchor.insertAdjacentElement('afterend',section); else document.querySelector('main').appendChild(section);

  const badge=document.getElementById('stock10cBadge');const tabs=document.getElementById('stock10cTabs');const pane=document.getElementById('stock10cPane');
  let artifact=null;let selected=null;
  const pct=v=>v==null?'—':Number(v).toFixed(1)+'%';
  const score=v=>v==null?'—':Number(v).toFixed(0)+'/100';
  const clean=v=>String(v||'—').replaceAll('_',' ');
  const cls=v=>{const s=String(v||'').toLowerCase();if(s.includes('supportive')||s==='low')return 'state-supportive';if(s.includes('pressured')||s==='high')return 'state-pressured';if(s.includes('mixed')||s.includes('moderate')||s.includes('conditional'))return 'state-mixed';return ''};

  function patchRoadmap(ready){
    document.querySelectorAll('.step').forEach(step=>{const key=step.querySelector('.stepN')&&step.querySelector('.stepN').textContent.trim();const status=step.querySelector('.status');if(!status)return;if(key==='10A')status.textContent='COMPLETE';if(key==='10B')status.textContent='COMPLETE';if(key==='10C')status.textContent=ready?'PRE-VALIDATION READY':'READY TO ACTIVATE';});
  }

  function renderTabs(){const symbols=artifact&&artifact.symbols||[];tabs.innerHTML=symbols.map(s=>`<button class="stock10c-tab ${s.ticker===selected?'active':''}" data-t="${s.ticker}">${s.ticker}</button>`).join('');}

  function driverItems(s){
    const items=[];const mc=(s.market_structure&&s.market_structure.components)||{};Object.entries(mc).forEach(([k,v])=>{if(v==null)return;if(v>=65)items.push({label:clean(k),text:'supports the current market structure',score:v});else if(v<=35)items.push({label:clean(k),text:'pressures the current market structure',score:v});});
    const fc=(s.fundamental_evidence&&s.fundamental_evidence.components)||{};Object.entries(fc).forEach(([k,v])=>{if(!v||v.score==null)return;if(v.score>=65)items.push({label:clean(k),text:`comparable SEC change ${v.change_percent>0?'+':''}${Number(v.change_percent).toFixed(1)}%`,score:v.score});else if(v.score<=35)items.push({label:clean(k),text:`comparable SEC change ${Number(v.change_percent).toFixed(1)}%`,score:v.score});});
    return items.sort((a,b)=>Math.abs(b.score-50)-Math.abs(a.score-50)).slice(0,5);
  }

  function render(){
    const s=(artifact.symbols||[]).find(x=>x.ticker===selected);if(!s){pane.className='stock10c-empty';pane.innerHTML='No decision-intelligence record is available.';return;}
    const m=s.market_structure||{},f=s.fundamental_evidence||{},r=s.decision_readiness||{},rk=s.decision_risk||{},ai=s.ai_decision_reasoner||{},ct=s.counter_thesis||{};const drivers=driverItems(s);const ctf=ct.factors||[];
    pane.className='';pane.innerHTML=`<div class="companyHead"><div class="companyTitle"><h2>${s.ticker} · ${s.name||''}</h2><p>${s.exchange||'—'} · Market session ${s.market_session||'—'} · SEC filing ${s.latest_sec_filing_date||'—'}</p></div><span class="stock10c-badge">MODEL NOT FROZEN</span></div>
    <div class="stock10c-grid" style="margin-top:13px">
      <div class="stock10c-card"><div class="l">Market View</div><div class="v ${cls(m.state)}">${clean(m.state)}</div><div class="score">${score(m.score)}</div></div>
      <div class="stock10c-card"><div class="l">Fundamental Evidence</div><div class="v ${cls(f.state)}">${clean(f.state)}</div><div class="score">${score(f.score)} · ${pct(f.comparable_coverage_percent)} coverage</div></div>
      <div class="stock10c-card"><div class="l">Decision Readiness</div><div class="v ${cls(r.state)}">${score(r.score)}</div><div class="n">${clean(r.state)}</div></div>
      <div class="stock10c-card"><div class="l">Decision Risk</div><div class="v ${cls(rk.state)}">${score(rk.score)}</div><div class="n">${clean(rk.state)}</div></div>
      <div class="stock10c-card"><div class="l">Alignment</div><div class="v ${cls(s.cross_layer_alignment)}" style="font-size:.82rem">${clean(s.cross_layer_alignment)}</div><div class="n">SEC vs market evidence</div></div>
      <div class="stock10c-card"><div class="l">AI Reasoner</div><div class="v" style="font-size:.78rem">${clean(ai.status)}</div><div class="n">Priority: ${clean(ai.decision)}</div></div>
    </div>
    <div class="stock10c-two"><div class="stock10c-panel"><h3>Why this view?</h3><div class="stock10c-list">${drivers.length?drivers.map(d=>`<div class="stock10c-item"><b>${d.label}</b> · ${d.text} · component ${Number(d.score).toFixed(0)}/100</div>`).join(''):'<div class="stock10c-item">No single component dominates the current view; evidence is balanced or incomplete.</div>'}</div></div><div class="stock10c-panel"><h3>Counter-Thesis · ${clean(ct.strength)}</h3><div class="stock10c-list">${ctf.length?ctf.map(x=>`<div class="stock10c-item ${String(x.severity||'').toLowerCase()}"><b>${clean(x.severity)}</b> · ${x.text}</div>`).join(''):'<div class="stock10c-item">No material opposing factor crossed the current pre-validation thresholds.</div>'}</div></div></div>
    <div class="stock10c-guard"><b>10C guardrail:</b> Market View is an explainable evidence state, not BUY/SELL. Decision Readiness is not profit probability. This model is <b>EXPERIMENTAL_PREVALIDATION</b>, its weights have not been tuned on outcomes, and Stage 10D must freeze the logic before prospective validation begins. Trade execution remains OFF.</div>`;renderTabs();
  }

  tabs.addEventListener('click',e=>{const b=e.target.closest('.stock10c-tab');if(!b)return;selected=b.dataset.t;render();});
  fetch('./data/stocks-decision-intelligence.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(data=>{artifact=data;const symbols=Array.isArray(data.symbols)?data.symbols:[];const ready=symbols.length>0&&(data.status==='STOCKS_DECISION_INTELLIGENCE_READY'||data.status==='PARTIAL');patchRoadmap(ready);if(!ready){badge.textContent=clean(data.status||'DECISION INTELLIGENCE NOT RUN');return;}badge.textContent=data.status==='STOCKS_DECISION_INTELLIGENCE_READY'?'PRE-VALIDATION INTELLIGENCE READY':'PARTIAL INTELLIGENCE';badge.classList.add('ready');selected=symbols[0].ticker;renderTabs();render();}).catch(()=>{badge.textContent='DECISION DATA UNAVAILABLE';patchRoadmap(false)});
})();
