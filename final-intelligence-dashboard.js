(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('final-intelligence-dashboard')) return;

  var style=document.createElement('style');
  style.textContent=
    '.fid{margin-top:12px;padding:15px;border-radius:14px;border:1px solid rgba(47,211,238,.28);background:linear-gradient(180deg,rgba(47,211,238,.055),rgba(7,11,20,.2));font-size:.78rem}' +
    '.fid-head{display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px;align-items:flex-start;margin-bottom:11px}' +
    '.fid-eyebrow{font-size:.58rem;letter-spacing:.09em;text-transform:uppercase;color:var(--muted-2);font-weight:800}' +
    '.fid-title{margin-top:3px;font-size:1.04rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.fid-sub{margin-top:4px;font-size:.64rem;line-height:1.45;color:var(--muted)}' +
    '.fid-status{display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end}' +
    '.fid-badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:.56rem;font-weight:850;letter-spacing:.04em;white-space:nowrap}' +
    '.fid-ok{background:var(--green-dim);color:var(--green)}' +
    '.fid-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.fid-bad{background:var(--red-dim);color:var(--red)}' +
    '.fid-muted{background:rgba(148,163,184,.09);color:var(--muted)}' +
    '.fid-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}' +
    '@media(min-width:760px){.fid-kpis{grid-template-columns:repeat(4,minmax(0,1fr))}}' +
    '.fid-kpi{border:1px solid var(--border);border-radius:10px;padding:9px 10px;background:rgba(7,11,20,.24);min-width:0}' +
    '.fid-k{font-size:.54rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2)}' +
    '.fid-v{margin-top:4px;font-size:.88rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.fid-n{margin-top:3px;font-size:.58rem;color:var(--muted);line-height:1.35}' +
    '.fid-context{display:grid;grid-template-columns:1fr;gap:7px;margin-top:8px}' +
    '@media(min-width:620px){.fid-context{grid-template-columns:repeat(3,minmax(0,1fr))}}' +
    '.fid-context-card{border:1px solid var(--border);border-radius:10px;padding:9px 10px;background:rgba(7,11,20,.16)}' +
    '.fid-context-top{display:flex;justify-content:space-between;gap:7px;align-items:center}' +
    '.fid-context-name{font-size:.59rem;font-weight:800;color:var(--text)}' +
    '.fid-context-score{font-size:.72rem;font-weight:850;color:var(--text)}' +
    '.fid-context-note{margin-top:5px;font-size:.58rem;color:var(--muted);line-height:1.38}' +
    '.fid-summary{display:grid;grid-template-columns:1fr;gap:8px;margin-top:8px}' +
    '@media(min-width:760px){.fid-summary{grid-template-columns:1fr 1fr}}' +
    '.fid-panel{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.18);min-width:0}' +
    '.fid-panel-title{font-size:.56rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);font-weight:800;margin-bottom:6px}' +
    '.fid-line{font-size:.61rem;color:var(--muted);line-height:1.45;margin-top:4px}' +
    '.fid-line b{color:var(--text);font-weight:750}' +
    '.fid-assessment{margin-top:8px;padding:10px 11px;border-radius:10px;background:rgba(47,211,238,.045);border:1px solid rgba(47,211,238,.2)}' +
    '.fid-assessment-title{font-size:.56rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);font-weight:800}' +
    '.fid-assessment-text{margin-top:5px;font-size:.65rem;line-height:1.5;color:var(--text)}' +
    '.fid-foot{margin-top:8px;font-size:.56rem;line-height:1.42;color:var(--muted-2)}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='final-intelligence-dashboard';
  box.className='fid';
  box.innerHTML=
    '<div class="fid-head">' +
      '<div><div class="fid-eyebrow">Final Intelligence Dashboard</div><div class="fid-title" id="fid-title">Memuat ringkasan keputusan…</div><div class="fid-sub" id="fid-sub">Menggabungkan Currency Strength, Actionability, konteks eksternal, Risk, Counter-Thesis, dan Final Reasoner.</div></div>' +
      '<div class="fid-status"><span class="fid-badge fid-muted" id="fid-status">MEMUAT</span><span class="fid-badge fid-muted" id="fid-decision">—</span></div>' +
    '</div>' +
    '<div class="fid-kpis">' +
      '<div class="fid-kpi"><div class="fid-k">Actionability</div><div class="fid-v" id="fid-action">—</div><div class="fid-n" id="fid-action-note">—</div></div>' +
      '<div class="fid-kpi"><div class="fid-k">Context Coverage</div><div class="fid-v" id="fid-coverage">—</div><div class="fid-n" id="fid-coverage-note">—</div></div>' +
      '<div class="fid-kpi"><div class="fid-k">Risk v0.2</div><div class="fid-v" id="fid-risk">—</div><div class="fid-n" id="fid-risk-note">—</div></div>' +
      '<div class="fid-kpi"><div class="fid-k">Counter-Thesis</div><div class="fid-v" id="fid-counter">—</div><div class="fid-n" id="fid-counter-note">—</div></div>' +
    '</div>' +
    '<div class="fid-context">' +
      '<div class="fid-context-card" id="fid-macro"></div>' +
      '<div class="fid-context-card" id="fid-cross"></div>' +
      '<div class="fid-context-card" id="fid-news"></div>' +
    '</div>' +
    '<div class="fid-summary">' +
      '<div class="fid-panel"><div class="fid-panel-title">Evidence For</div><div id="fid-for"></div></div>' +
      '<div class="fid-panel"><div class="fid-panel-title">Evidence Against</div><div id="fid-against"></div></div>' +
      '<div class="fid-panel"><div class="fid-panel-title">Key Risk</div><div id="fid-key-risk"></div></div>' +
      '<div class="fid-panel"><div class="fid-panel-title">Invalidation / Monitoring</div><div id="fid-invalidation"></div></div>' +
    '</div>' +
    '<div class="fid-assessment"><div class="fid-assessment-title">Final Assessment</div><div class="fid-assessment-text" id="fid-assessment">Menunggu Final Reasoner…</div></div>' +
    '<div class="fid-foot">Dashboard ini hanya merangkum output production yang ada. Ia tidak mengubah sinyal ECB, Actionability, Risk v0.2, Counter-Thesis, ataupun decision logic Final Reasoner yang sedang dibekukan selama Fresh OOS.</div>';

  var anchor=document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function score(n){return Number.isFinite(Number(n))?Number(n).toFixed(1).replace('.',','):null;}
  function labelBias(b){return b==='BUY'?'BELI':b==='SELL'?'JUAL':'TUNGGU';}
  function decisionLabel(x){return ({EVALUATE_SETUP:'EVALUASI SETUP',REVIEW_SELECTIVELY:'TINJAU SELEKTIF',DEPRIORITIZE:'TURUNKAN PRIORITAS',WAIT_FOR_CONTEXT:'TUNGGU KONTEKS'})[x]||String(x||'—').replace(/_/g,' ');}
  function stateLabel(x){return ({CONTEXT_CONFIRMED:'KONTEKS TERKONFIRMASI',CONTEXT_CONTRADICTED:'KONTEKS BERTENTANGAN',MIXED_CONTEXT:'KONTEKS CAMPURAN',RISK_CONSTRAINED:'DIBATASI RISIKO',INSUFFICIENT_EXTERNAL_EVIDENCE:'BUKTI KONTEKS KURANG',UNAVAILABLE:'TIDAK TERSEDIA'})[x]||String(x||'—').replace(/_/g,' ');}
  function badgeClass(x){
    var s=String(x||'').toUpperCase();
    if(['SUPPORTS','LOW','ACTIONABLE','CONTEXT_CONFIRMED'].includes(s)) return 'fid-ok';
    if(['OPPOSES','HIGH','FILTERED','CONTEXT_CONTRADICTED','RISK_CONSTRAINED'].includes(s)) return 'fid-bad';
    if(['MIXED','NEUTRAL','MODERATE','SELECTIVE','MIXED_CONTEXT'].includes(s)) return 'fid-warn';
    return 'fid-muted';
  }
  function contextLabel(state){return ({SUPPORTS:'MENDUKUNG',OPPOSES:'MENENTANG',MIXED:'CAMPURAN',NEUTRAL:'NETRAL',UNAVAILABLE:'TIDAK TERSEDIA'})[String(state||'UNAVAILABLE').toUpperCase()]||String(state||'—');}
  function contextCard(el,layer,name){
    if(!el) return;
    if(!layer||!layer.available){el.innerHTML='<div class="fid-context-top"><div class="fid-context-name">'+esc(name)+'</div><span class="fid-badge fid-muted">TIDAK TERSEDIA</span></div><div class="fid-context-note">Fail-closed: bukti tidak diasumsikan.</div>';return;}
    var note=Array.isArray(layer.evidence)&&layer.evidence.length?layer.evidence[0]:(layer.note||'Bukti tersedia.');
    el.innerHTML='<div class="fid-context-top"><div class="fid-context-name">'+esc(name)+'</div><span class="fid-badge '+badgeClass(layer.state)+'">'+esc(contextLabel(layer.state))+'</span></div><div class="fid-context-score">'+(score(layer.score)!==null?score(layer.score)+'/100':'—')+'</div><div class="fid-context-note">'+esc(note)+'</div>';
  }
  function evidenceLines(items,max){
    if(!Array.isArray(items)||!items.length) return '<div class="fid-line">Belum ada bukti terstruktur.</div>';
    return items.slice(0,max||3).map(function(x){return '<div class="fid-line"><b>'+esc((x.source||x.category||'Bukti').replace(/_/g,' '))+' · </b>'+esc(x.statement||'—')+'</div>';}).join('');
  }

  function render(data){
    var intel=data&&data.intelligence_layer;
    var layers=intel&&intel.layers||{};
    var f=layers.final_reasoner||{};
    var r=layers.risk||{};
    var c=layers.counter_thesis||{};
    var a=data&&data.actionability_score&&(data.actionability_score.current||data.actionability_score.timeframes&&data.actionability_score.timeframes.daily)||intel&&intel.upstream_actionability||{};
    var pair=f.pair||intel&&intel.current_pair||a&&a.signal&&a.signal.pair||'—';
    var bias=f.canonical_bias||intel&&intel.canonical_bias||a&&a.signal&&a.signal.bias||'—';

    document.getElementById('fid-title').textContent=(pair&&pair.length===6?pair.slice(0,3)+' / '+pair.slice(3):pair)+' · '+labelBias(bias);
    document.getElementById('fid-sub').textContent='Regime '+(f.regime||a.regime||'—')+' · Final Reasoner '+(f.version?'v'+f.version:'—')+' · Decision logic '+(f.decision_logic_version||'—');

    var st=document.getElementById('fid-status');
    st.className='fid-badge '+badgeClass(f.status);
    st.textContent=stateLabel(f.status);
    var dec=document.getElementById('fid-decision');
    dec.className='fid-badge '+(f.decision==='EVALUATE_SETUP'?'fid-ok':f.decision==='DEPRIORITIZE'?'fid-bad':'fid-warn');
    dec.textContent=decisionLabel(f.decision);

    document.getElementById('fid-action').textContent=(score(a.score)!==null?score(a.score)+'/100':'—')+' · '+String(a.state||'—').replace(/_/g,' ');
    document.getElementById('fid-action-note').textContent='Regime '+(f.regime||'—')+(a.primary_limiter?' · Pembatas '+String(a.primary_limiter).replace(/_/g,' '):'');
    document.getElementById('fid-coverage').textContent=(Number.isFinite(Number(f.contextual_coverage_percent))?f.contextual_coverage_percent:'0')+'% · '+((f.context_counts&&f.context_counts.available)||0)+'/'+((f.context_counts&&f.context_counts.expected)||3);
    document.getElementById('fid-coverage-note').textContent='Support '+((f.context_counts&&f.context_counts.supports)||0)+' · Oppose '+((f.context_counts&&f.context_counts.opposes)||0)+' · Mixed/Netral '+((f.context_counts&&f.context_counts.mixed_or_neutral)||0);
    document.getElementById('fid-risk').textContent=(score(r.score)!==null?score(r.score)+'/100':'—')+' · '+String(r.state||'—');
    document.getElementById('fid-risk-note').textContent=r.primary_drivers&&r.primary_drivers.length?'Utama: '+r.primary_drivers[0].label+' +'+score(r.primary_drivers[0].contribution):'Baseline konservatif';
    document.getElementById('fid-counter').textContent=String(c.challenge_level||'—')+' · '+String(c.state||'—');
    document.getElementById('fid-counter-note').textContent=c.primary_objection&&c.primary_objection.source_layer?'Utama: '+String(c.primary_objection.source_layer).replace(/_/g,' '):'Belum ada primary objection';

    contextCard(document.getElementById('fid-macro'),layers.macro_yield,'Macro & Yield');
    contextCard(document.getElementById('fid-cross'),layers.cross_market,'Cross-Market');
    contextCard(document.getElementById('fid-news'),layers.news,'News');

    document.getElementById('fid-for').innerHTML=evidenceLines(f.evidence_for,3);
    document.getElementById('fid-against').innerHTML=evidenceLines(f.evidence_against,3);
    var kr=f.key_risk||{};
    document.getElementById('fid-key-risk').innerHTML='<div class="fid-line"><b>'+esc(kr.label||'Risk')+(score(kr.contribution)!==null?' +'+score(kr.contribution):'')+' · </b>'+esc(kr.reason||'Risiko utama belum tersedia.')+'</div><div class="fid-line">Risk '+esc(r.state||'—')+(score(r.score)!==null?' · '+score(r.score)+'/100':'')+'</div>';

    var inv=Array.isArray(f.invalidation_conditions)?f.invalidation_conditions:[];
    var active=inv.filter(function(x){return x&&x.triggered;});
    var chosen=active.length?active.slice(0,3):inv.slice(0,3);
    document.getElementById('fid-invalidation').innerHTML=chosen.length?chosen.map(function(x){return '<div class="fid-line"><b>'+(x.triggered?'AKTIF':'PANTAU')+' · </b>'+esc(x.condition||x.label||'—')+'</div>';}).join(''):'<div class="fid-line">Belum ada kondisi invalidasi terstruktur.</div>';
    document.getElementById('fid-assessment').textContent=f.final_assessment||f.explanation||'Final assessment belum tersedia.';
  }

  function load(){
    fetch('./data/currency-strength.json?v=f016e702ab',{headers:{Accept:'application/json'},cache:'no-store'})
      .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
      .then(function(payload){render(payload&&payload.data?payload.data:payload);})
      .catch(function(){var s=document.getElementById('fid-status');if(s){s.className='fid-badge fid-bad';s.textContent='GAGAL MEMUAT';}});
  }

  var refresh=document.getElementById('live-refresh');
  if(refresh) refresh.addEventListener('click',function(){setTimeout(load,350);});
  load();
  setInterval(load,60000);
})();
