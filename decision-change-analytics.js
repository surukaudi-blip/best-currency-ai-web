(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('decision-change-analytics')) return;

  var style=document.createElement('style');
  style.textContent=
    '.dca{margin-top:12px;padding:15px;border-radius:14px;border:1px solid var(--border);background:rgba(7,11,20,.16);font-size:.76rem}' +
    '.dca-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}' +
    '.dca-eyebrow{font-size:.57rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted-2);font-weight:800}' +
    '.dca-title{margin-top:3px;font-size:.96rem;font-weight:850;color:var(--text)}' +
    '.dca-sub{margin-top:4px;font-size:.62rem;line-height:1.45;color:var(--muted)}' +
    '.dca-badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:.55rem;font-weight:850;letter-spacing:.04em;white-space:nowrap}' +
    '.dca-ok{background:var(--green-dim);color:var(--green)}' +
    '.dca-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.dca-muted{background:rgba(148,163,184,.09);color:var(--muted)}' +
    '.dca-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}' +
    '@media(min-width:760px){.dca-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
    '.dca-kpi{border:1px solid var(--border);border-radius:10px;padding:8px 9px;background:rgba(7,11,20,.22)}' +
    '.dca-k{font-size:.5rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted-2)}' +
    '.dca-v{margin-top:4px;font-size:.8rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.dca-n{margin-top:3px;font-size:.55rem;color:var(--muted);line-height:1.35}' +
    '.dca-panels{display:grid;grid-template-columns:1fr;gap:8px;margin-top:9px}' +
    '@media(min-width:760px){.dca-panels{grid-template-columns:1fr 1fr}}' +
    '.dca-panel{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.18)}' +
    '.dca-pt{font-size:.55rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);font-weight:800;margin-bottom:5px}' +
    '.dca-line{font-size:.6rem;color:var(--muted);line-height:1.45;margin-top:4px}' +
    '.dca-line b{color:var(--text);font-weight:750}' +
    '.dca-foot{margin-top:9px;padding-top:8px;border-top:1px solid var(--border);font-size:.55rem;line-height:1.42;color:var(--muted-2)}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='decision-change-analytics';
  box.className='dca';
  box.innerHTML=
    '<div class="dca-head"><div><div class="dca-eyebrow">Decision Change Analytics</div><div class="dca-title">Perubahan Keputusan & Stabilitas Sinyal</div><div class="dca-sub">Mengukur streak, perubahan state, signal flip, dan perubahan Final Reasoner dari Decision History prospective.</div></div><span class="dca-badge dca-muted" id="dca-status">MEMUAT</span></div>' +
    '<div class="dca-grid">' +
      '<div class="dca-kpi"><div class="dca-k">Sesi</div><div class="dca-v" id="dca-sessions">—</div><div class="dca-n">Snapshot immutable</div></div>' +
      '<div class="dca-kpi"><div class="dca-k">Transisi</div><div class="dca-v" id="dca-transitions">—</div><div class="dca-n">Perubahan antar sesi</div></div>' +
      '<div class="dca-kpi"><div class="dca-k">Sinyal Bertahan</div><div class="dca-v" id="dca-signal-streak">—</div><div class="dca-n" id="dca-signal-note">—</div></div>' +
      '<div class="dca-kpi"><div class="dca-k">Risk Bertahan</div><div class="dca-v" id="dca-risk-streak">—</div><div class="dca-n" id="dca-risk-note">—</div></div>' +
      '<div class="dca-kpi"><div class="dca-k">Signal Flip</div><div class="dca-v" id="dca-flips">—</div><div class="dca-n">Pair/bias berubah</div></div>' +
      '<div class="dca-kpi"><div class="dca-k">Fresh OOS Settled</div><div class="dca-v" id="dca-oos">—</div><div class="dca-n">Outcome-only linkage</div></div>' +
    '</div>' +
    '<div class="dca-panels">' +
      '<div class="dca-panel"><div class="dca-pt">Transition Monitor</div><div id="dca-transition-list"></div></div>' +
      '<div class="dca-panel"><div class="dca-pt">Final Reasoner Change Precursors</div><div id="dca-precursors"></div></div>' +
      '<div class="dca-panel"><div class="dca-pt">Signal Flip Diagnostics</div><div id="dca-flip-list"></div></div>' +
      '<div class="dca-panel"><div class="dca-pt">Fresh OOS Linkage</div><div id="dca-oos-summary"></div></div>' +
    '</div>' +
    '<div class="dca-foot">Deskriptif saja: analytics ini tidak mengubah Currency Strength, Actionability, Risk v0.2, Counter-Thesis, atau Final Reasoner. Tidak ada threshold/bobot yang dituning dari timeline ini.</div>';

  var timeline=document.getElementById('intelligence-timeline');
  var anchor=timeline||document.getElementById('final-intelligence-dashboard')||document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function pct(x){return Number.isFinite(Number(x))?Number(x).toFixed(1).replace('.',',')+'%':'—';}
  function line(label,value){return '<div class="dca-line"><b>'+esc(label)+' · </b>'+esc(value)+'</div>';}

  function render(a){
    if(!a||a.status!=='DECISION_CHANGE_ANALYTICS_ACTIVE') throw new Error('analytics unavailable');
    var gate=a.sample&&a.sample.analytics_gate||'COLLECTING_TRANSITIONS';
    var st=document.getElementById('dca-status');
    st.className='dca-badge '+(gate==='MATURE_DESCRIPTIVE_SAMPLE'?'dca-ok':gate==='EARLY_DESCRIPTIVE_SAMPLE'?'dca-warn':'dca-muted');
    st.textContent=gate==='MATURE_DESCRIPTIVE_SAMPLE'?'DESKRIPTIF MATANG':gate==='EARLY_DESCRIPTIVE_SAMPLE'?'SAMPEL AWAL':'MENGUMPULKAN TRANSISI';

    document.getElementById('dca-sessions').textContent=String(a.sample.captured_sessions||0);
    document.getElementById('dca-transitions').textContent=String(a.sample.transitions||0);
    var ss=a.current_streaks&&a.current_streaks.canonical_signal||{};
    document.getElementById('dca-signal-streak').textContent=(ss.value||'—')+' · '+(ss.sessions||0)+' sesi';
    document.getElementById('dca-signal-note').textContent=ss.start_session?'Sejak '+ss.start_session:'Belum tersedia';
    var rs=a.current_streaks&&a.current_streaks.risk_state||{};
    document.getElementById('dca-risk-streak').textContent=(rs.value||'—')+' · '+(rs.sessions||0)+' sesi';
    document.getElementById('dca-risk-note').textContent=rs.start_session?'Sejak '+rs.start_session:'Belum tersedia';
    document.getElementById('dca-flips').textContent=String(a.transition_counts&&a.transition_counts.canonical_signal_changes||0);
    document.getElementById('dca-oos').textContent=String(a.sample.settled_oos_links||0);

    var c=a.transition_counts||{};
    document.getElementById('dca-transition-list').innerHTML=
      line('Leadership berubah',(c.leadership_changes||0)+'x')+
      line('Actionability state berubah',(c.actionability_state_changes||0)+'x')+
      line('Macro / Cross / News',(c.macro_state_changes||0)+' / '+(c.cross_market_state_changes||0)+' / '+(c.news_state_changes||0)+'x')+
      line('Risk state berubah',(c.risk_state_changes||0)+'x')+
      line('Final decision berubah',(c.final_decision_changes||0)+'x');

    var freq=a.final_change_precursor_frequency||{};
    var keys=Object.keys(freq).sort(function(x,y){return freq[y]-freq[x];});
    document.getElementById('dca-precursors').innerHTML=keys.length
      ? keys.slice(0,6).map(function(k){return line(k.replace(/_/g,' '),freq[k]+' perubahan Final');}).join('')
      : '<div class="dca-line">Belum ada perubahan Final Reasoner untuk dianalisis.</div>';

    var flips=Array.isArray(a.signal_flip_diagnostics)?a.signal_flip_diagnostics:[];
    document.getElementById('dca-flip-list').innerHTML=flips.length
      ? flips.slice(-4).reverse().map(function(x){return line(x.to_session,x.from_signal+' → '+x.to_signal+' · Risk sebelum '+(x.risk_before_flip.score==null?'—':x.risk_before_flip.score)+' '+x.risk_before_flip.state);}).join('')
      : '<div class="dca-line">Belum ada canonical signal flip dalam sample prospective.</div>';

    var o=a.settled_oos_descriptive||{};
    document.getElementById('dca-oos-summary').innerHTML=
      line('Matched sessions',String((a.fresh_oos_links||[]).length))+
      line('Settled pre-outcome',String(o.n||0))+
      line('Hit rate',pct(o.hit_rate))+
      line('Avg directional return',pct(o.avg_directional_return_pct))+
      '<div class="dca-line">Decision History dan Fresh OOS tetap dua capture immutable yang terpisah.</div>';
  }

  fetch('./data/decision-change-analytics.json',{headers:{Accept:'application/json'},cache:'no-store'})
    .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
    .then(render)
    .catch(function(){var st=document.getElementById('dca-status');if(st){st.className='dca-badge dca-muted';st.textContent='MENUNGGU DATA';}});
})();