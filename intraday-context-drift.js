(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('intraday-context-drift')) return;

  var style=document.createElement('style');
  style.textContent=
    '.icd{margin-top:12px;padding:15px;border-radius:14px;border:1px solid var(--border);background:rgba(7,11,20,.15);font-size:.76rem}' +
    '.icd-head{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}' +
    '.icd-eyebrow{font-size:.57rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted-2);font-weight:800}' +
    '.icd-title{margin-top:3px;font-size:.96rem;font-weight:850;color:var(--text)}' +
    '.icd-sub{margin-top:4px;font-size:.62rem;line-height:1.45;color:var(--muted)}' +
    '.icd-badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:.55rem;font-weight:850;letter-spacing:.04em;white-space:nowrap}' +
    '.icd-ok{background:var(--green-dim);color:var(--green)}' +
    '.icd-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.icd-bad{background:var(--red-dim);color:var(--red)}' +
    '.icd-muted{background:rgba(148,163,184,.09);color:var(--muted)}' +
    '.icd-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}' +
    '@media(min-width:760px){.icd-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
    '.icd-kpi{border:1px solid var(--border);border-radius:10px;padding:8px 9px;background:rgba(7,11,20,.22)}' +
    '.icd-k{font-size:.5rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted-2)}' +
    '.icd-v{margin-top:4px;font-size:.8rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.icd-n{margin-top:3px;font-size:.55rem;color:var(--muted);line-height:1.35}' +
    '.icd-panels{display:grid;grid-template-columns:1fr;gap:8px;margin-top:9px}' +
    '@media(min-width:760px){.icd-panels{grid-template-columns:1fr 1fr}}' +
    '.icd-panel{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.18)}' +
    '.icd-pt{font-size:.55rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);font-weight:800;margin-bottom:5px}' +
    '.icd-line{font-size:.6rem;color:var(--muted);line-height:1.45;margin-top:4px}' +
    '.icd-line b{color:var(--text);font-weight:750}' +
    '.icd-foot{margin-top:9px;padding-top:8px;border-top:1px solid var(--border);font-size:.55rem;line-height:1.42;color:var(--muted-2)}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='intraday-context-drift';
  box.className='icd';
  box.innerHTML=
    '<div class="icd-head"><div><div class="icd-eyebrow">Intraday Context Drift</div><div class="icd-title">Perubahan Konteks Dalam Sesi ECB</div><div class="icd-sub">Memantau perubahan News, Macro, Cross-Market, Risk, Counter-Thesis, dan Final Reasoner tanpa mengubah snapshot Decision History atau Fresh OOS.</div></div><span class="icd-badge icd-muted" id="icd-status">MEMUAT</span></div>' +
    '<div class="icd-grid">' +
      '<div class="icd-kpi"><div class="icd-k">ECB Session</div><div class="icd-v" id="icd-session">—</div><div class="icd-n">Sesi lengkap saat ini</div></div>' +
      '<div class="icd-kpi"><div class="icd-k">Capture</div><div class="icd-v" id="icd-captures">—</div><div class="icd-n">Dalam sesi yang sama</div></div>' +
      '<div class="icd-kpi"><div class="icd-k">News Δ</div><div class="icd-v" id="icd-news">—</div><div class="icd-n">Awal → terbaru</div></div>' +
      '<div class="icd-kpi"><div class="icd-k">Risk Δ</div><div class="icd-v" id="icd-risk">—</div><div class="icd-n">Bukan probability</div></div>' +
      '<div class="icd-kpi"><div class="icd-k">Final Reasoner</div><div class="icd-v" id="icd-final">—</div><div class="icd-n">Current intraday state</div></div>' +
      '<div class="icd-kpi"><div class="icd-k">Drift Events</div><div class="icd-v" id="icd-events">—</div><div class="icd-n">Dalam sesi saat ini</div></div>' +
    '</div>' +
    '<div class="icd-panels">' +
      '<div class="icd-panel"><div class="icd-pt">Latest Context</div><div id="icd-context"></div></div>' +
      '<div class="icd-panel"><div class="icd-pt">Latest Drift Events</div><div id="icd-drift-list"></div></div>' +
      '<div class="icd-panel"><div class="icd-pt">Frozen Anchors</div><div id="icd-anchors"></div></div>' +
      '<div class="icd-panel"><div class="icd-pt">Capture Window</div><div id="icd-window"></div></div>' +
    '</div>' +
    '<div class="icd-foot">Drift level adalah severity perubahan konteks secara deskriptif, bukan Risk v0.2 dan bukan probabilitas profit/loss. Monitor ini tidak melakukan voting atau tuning model.</div>';

  var analytics=document.getElementById('decision-change-analytics');
  var timeline=document.getElementById('intelligence-timeline');
  var anchor=analytics||timeline||document.getElementById('final-intelligence-dashboard')||document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function score(x){return Number.isFinite(Number(x))?Number(x).toFixed(1).replace('.',','):'—';}
  function signed(x){if(!Number.isFinite(Number(x)))return'—';var n=Number(x);return(n>0?'+':'')+n.toFixed(1).replace('.',',');}
  function line(k,v){return '<div class="icd-line"><b>'+esc(k)+' · </b>'+esc(v)+'</div>';}
  function cls(level){return level==='HIGH'?'icd-bad':level==='MODERATE'?'icd-warn':level==='LOW'?'icd-warn':level==='NONE'?'icd-ok':'icd-muted';}
  function ctx(layer){return layer&&layer.available?score(layer.score)+' · '+(layer.state||'—'):'TIDAK TERSEDIA';}

  function render(m){
    if(!m||m.status!=='INTRADAY_CONTEXT_DRIFT_ACTIVE') throw new Error('monitor unavailable');
    var s=m.current_session||{}, latest=(m.captures||[]).slice(-1)[0]||{}, x=latest.snapshot||{};
    var drift=latest.drift_level||s.current_drift_level||'BASELINE';
    var st=document.getElementById('icd-status');
    st.className='icd-badge '+cls(drift);st.textContent=drift==='BASELINE'?'BASELINE':('DRIFT '+drift);
    document.getElementById('icd-session').textContent=s.session_date||x.session_date||'—';
    document.getElementById('icd-captures').textContent=String(s.captures||0);
    document.getElementById('icd-news').textContent=signed(s.first_to_latest&&s.first_to_latest.news_score_delta);
    document.getElementById('icd-risk').textContent=signed(s.first_to_latest&&s.first_to_latest.risk_score_delta);
    document.getElementById('icd-final').textContent=x.final_reasoner?((x.final_reasoner.status||'—')+' · '+(x.final_reasoner.decision||'—')):'—';
    document.getElementById('icd-events').textContent=String(s.total_drift_events||0);

    var c=x.context||{};
    document.getElementById('icd-context').innerHTML=
      line('Macro & Yield',ctx(c.macro_yield))+
      line('Cross-Market',ctx(c.cross_market))+
      line('News',ctx(c.news)+' · event '+((c.news&&c.news.event_risk)||'—'))+
      line('Risk',x.risk?score(x.risk.score)+' · '+(x.risk.state||'—'):'—')+
      line('Counter-Thesis',x.counter_thesis?((x.counter_thesis.state||'—')+' · '+(x.counter_thesis.challenge_level||'—')):'—');

    var ev=latest.drift_vs_previous||[];
    document.getElementById('icd-drift-list').innerHTML=ev.length
      ? ev.slice(0,8).map(function(e){return line((e.severity||'NONE')+' · '+(e.label||e.key),(e.from==null?'—':e.from)+' → '+(e.to==null?'—':e.to)+(e.delta==null?'':' · Δ '+signed(e.delta)));}).join('')
      : '<div class="icd-line">Belum ada perubahan material.</div>';

    var a=latest.frozen_anchors||{};
    document.getElementById('icd-anchors').innerHTML=
      line('Decision History',a.decision_history?a.decision_history.id:'Belum tersedia')+
      line('Fresh OOS',a.fresh_oos?a.fresh_oos.id:'Belum tersedia')+
      '<div class="icd-line">Anchor hanya referensi; hash snapshot/prediction tidak ditulis ulang.</div>';

    document.getElementById('icd-window').innerHTML=
      line('Capture pertama',s.first_capture_at||'—')+
      line('Capture terbaru',s.last_capture_at||'—')+
      line('Macro Δ',signed(s.first_to_latest&&s.first_to_latest.macro_score_delta))+
      line('Cross-Market Δ',signed(s.first_to_latest&&s.first_to_latest.cross_market_score_delta))+
      line('News state',s.first_to_latest&&s.first_to_latest.news_state||'—')+
      line('Risk state',s.first_to_latest&&s.first_to_latest.risk_state||'—');
  }

  fetch('./data/intraday-context-drift.json',{headers:{Accept:'application/json'},cache:'no-store'})
    .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
    .then(render)
    .catch(function(){var st=document.getElementById('icd-status');if(st){st.className='icd-badge icd-muted';st.textContent='MENUNGGU DATA';}});
})();