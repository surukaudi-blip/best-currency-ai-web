(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('decision-alert-watch')) return;

  var style=document.createElement('style');
  style.textContent=
    '.daw{margin-top:12px;padding:15px;border-radius:14px;border:1px solid var(--border);background:rgba(7,11,20,.18);font-size:.76rem}' +
    '.daw-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}' +
    '.daw-eyebrow{font-size:.57rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted-2);font-weight:800}' +
    '.daw-title{margin-top:3px;font-size:1rem;font-weight:900;color:var(--text)}' +
    '.daw-sub{margin-top:4px;font-size:.62rem;line-height:1.45;color:var(--muted)}' +
    '.daw-badge{display:inline-flex;align-items:center;border-radius:999px;padding:5px 9px;font-size:.55rem;font-weight:900;letter-spacing:.04em;white-space:nowrap}' +
    '.daw-ok{background:var(--green-dim);color:var(--green)}' +
    '.daw-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.daw-bad{background:var(--red-dim);color:var(--red)}' +
    '.daw-muted{background:rgba(148,163,184,.09);color:var(--muted)}' +
    '.daw-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}' +
    '@media(min-width:760px){.daw-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
    '.daw-kpi{border:1px solid var(--border);border-radius:10px;padding:8px 9px;background:rgba(7,11,20,.22)}' +
    '.daw-k{font-size:.5rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted-2)}' +
    '.daw-v{margin-top:4px;font-size:.8rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.daw-n{margin-top:3px;font-size:.55rem;color:var(--muted);line-height:1.35}' +
    '.daw-panels{display:grid;grid-template-columns:1fr;gap:8px;margin-top:9px}' +
    '@media(min-width:760px){.daw-panels{grid-template-columns:1.2fr .8fr}}' +
    '.daw-panel{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.18)}' +
    '.daw-pt{font-size:.55rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);font-weight:800;margin-bottom:5px}' +
    '.daw-alert{border:1px solid var(--border);border-radius:9px;padding:8px 9px;margin-top:6px;background:rgba(7,11,20,.2)}' +
    '.daw-alert:first-child{margin-top:0}' +
    '.daw-row{display:flex;align-items:center;justify-content:space-between;gap:8px}' +
    '.daw-a-title{font-size:.63rem;font-weight:800;color:var(--text)}' +
    '.daw-a-detail{margin-top:4px;font-size:.57rem;line-height:1.4;color:var(--muted)}' +
    '.daw-sev{font-size:.48rem;font-weight:900;border-radius:999px;padding:3px 6px;white-space:nowrap}' +
    '.daw-line{font-size:.6rem;color:var(--muted);line-height:1.45;margin-top:4px}' +
    '.daw-line b{color:var(--text);font-weight:750}' +
    '.daw-foot{margin-top:9px;padding-top:8px;border-top:1px solid var(--border);font-size:.55rem;line-height:1.42;color:var(--muted-2)}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='decision-alert-watch';
  box.className='daw';
  box.innerHTML=
    '<div class="daw-head"><div><div class="daw-eyebrow">Decision Alert / Intelligence Watch</div><div class="daw-title">Alert Perubahan Material</div><div class="daw-sub">Memunculkan alert hanya ketika kondisi material perlu ditinjau. Layer ini tidak mengubah canonical signal atau decision logic.</div></div><span class="daw-badge daw-muted" id="daw-gate">MEMUAT</span></div>' +
    '<div class="daw-grid">' +
      '<div class="daw-kpi"><div class="daw-k">Canonical</div><div class="daw-v" id="daw-signal">—</div><div class="daw-n" id="daw-session">—</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Alert Aktif</div><div class="daw-v" id="daw-active">—</div><div class="daw-n">Open watch conditions</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">HIGH</div><div class="daw-v" id="daw-high">—</div><div class="daw-n">Perlu review sekarang</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">MODERATE</div><div class="daw-v" id="daw-mod">—</div><div class="daw-n">Pantau ketat</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Risk v0.2</div><div class="daw-v" id="daw-risk">—</div><div class="daw-n">Frozen production formula</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Final Reasoner</div><div class="daw-v" id="daw-final">—</div><div class="daw-n">Frozen decision logic</div></div>' +
    '</div>' +
    '<div class="daw-panels">' +
      '<div class="daw-panel"><div class="daw-pt">Active Alerts</div><div id="daw-list"></div></div>' +
      '<div class="daw-panel"><div class="daw-pt">Latest Alert Events</div><div id="daw-events"></div></div>' +
      '<div class="daw-panel"><div class="daw-pt">Current Context</div><div id="daw-context"></div></div>' +
      '<div class="daw-panel"><div class="daw-pt">Integrity Guardrail</div><div id="daw-guardrail"></div></div>' +
    '</div>' +
    '<div class="daw-foot">HIGH = review sekarang, MODERATE = pantau ketat, INFO = awareness. Severity alert bukan probabilitas rugi/profit dan tidak melakukan trade execution.</div>';

  var anchor=document.getElementById('final-intelligence-dashboard')||document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function score(x){return Number.isFinite(Number(x))?Number(x).toFixed(1).replace('.',','):'—';}
  function line(k,v){return '<div class="daw-line"><b>'+esc(k)+' · </b>'+esc(v)+'</div>';}
  function sevClass(s){return s==='HIGH'?'daw-bad':s==='MODERATE'?'daw-warn':'daw-muted';}
  function gateClass(g){return g==='REVIEW_NOW'?'daw-bad':g==='WATCH_CLOSELY'?'daw-warn':g==='STABLE'?'daw-ok':'daw-muted';}
  function gateText(g){return g==='REVIEW_NOW'?'REVIEW SEKARANG':g==='WATCH_CLOSELY'?'PANTAU KETAT':g==='STABLE'?'STABIL':g||'—';}
  function alertCard(a){return '<div class="daw-alert"><div class="daw-row"><div class="daw-a-title">'+esc(a.title||a.key)+'</div><span class="daw-sev '+sevClass(a.severity)+'">'+esc(a.severity||'INFO')+'</span></div><div class="daw-a-detail">'+esc(a.detail||'')+'</div><div class="daw-line">Sumber: '+esc(a.source||'—')+' · sejak '+esc(a.first_seen||'—')+'</div></div>';}

  function render(r){
    if(!r||r.status!=='DECISION_ALERT_WATCH_ACTIVE') throw new Error('alert watch unavailable');
    var s=r.summary||{}, c=r.current_watch||{}, gate=s.alert_gate||'STABLE';
    var badge=document.getElementById('daw-gate');badge.className='daw-badge '+gateClass(gate);badge.textContent=gateText(gate);
    document.getElementById('daw-signal').textContent=(c.pair||'—')+' '+(c.canonical_bias||'—');
    document.getElementById('daw-session').textContent=c.session_date?'ECB '+c.session_date:'Sesi —';
    document.getElementById('daw-active').textContent=String(s.active_total||0);
    document.getElementById('daw-high').textContent=String(s.high_active||0);
    document.getElementById('daw-mod').textContent=String(s.moderate_active||0);
    document.getElementById('daw-risk').textContent=c.risk?score(c.risk.score)+' · '+(c.risk.state||'—'):'—';
    document.getElementById('daw-final').textContent=c.final_reasoner?((c.final_reasoner.status||'—')+' · '+(c.final_reasoner.decision||'—')):'—';

    var active=Array.isArray(r.active_alerts)?r.active_alerts:[];
    document.getElementById('daw-list').innerHTML=active.length?active.slice(0,8).map(alertCard).join(''):'<div class="daw-line"><b>Tidak ada alert material aktif.</b> Struktur watch saat ini stabil.</div>';

    var events=Array.isArray(r.events)?r.events.slice(-8).reverse():[];
    document.getElementById('daw-events').innerHTML=events.length?events.map(function(e){return line((e.event_type||'EVENT')+' · '+(e.severity||'INFO'),(e.title||e.alert_key)+' — '+(e.detail||''));}).join(''):'<div class="daw-line">Belum ada alert event.</div>';

    var x=c.context||{};
    document.getElementById('daw-context').innerHTML=
      line('Actionability',c.actionability?score(c.actionability.score)+' · '+(c.actionability.state||'—'):'—')+
      line('Macro & Yield',x.macro_yield?score(x.macro_yield.score)+' · '+(x.macro_yield.state||'—'):'—')+
      line('Cross-Market',x.cross_market?score(x.cross_market.score)+' · '+(x.cross_market.state||'—'):'—')+
      line('News',x.news?score(x.news.score)+' · '+(x.news.state||'—')+' · event '+(x.news.event_risk||'—'):'—')+
      line('Counter-Thesis',c.counter_thesis?((c.counter_thesis.state||'—')+' · '+(c.counter_thesis.challenge_level||'—')):'—');

    var a=c.anchors||{};
    document.getElementById('daw-guardrail').innerHTML=
      line('Decision History',a.decision_history?a.decision_history.id:'—')+
      line('Fresh OOS',a.fresh_oos?a.fresh_oos.id:'—')+
      line('Alert event log','Append-only + SHA-256')+
      line('Model tuning','TIDAK')+
      line('Signal voting','TIDAK')+
      line('Trade execution','TIDAK');
  }

  fetch('./data/decision-alerts.json',{headers:{Accept:'application/json'},cache:'no-store'})
    .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
    .then(render)
    .catch(function(){var b=document.getElementById('daw-gate');if(b){b.className='daw-badge daw-muted';b.textContent='MENUNGGU DATA';}});
})();