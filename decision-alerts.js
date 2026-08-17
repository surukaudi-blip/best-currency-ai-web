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
    '<div class="daw-head"><div><div class="daw-eyebrow">Decision Alert / Intelligence Watch</div><div class="daw-title">Alert Perubahan Material</div><div class="daw-sub">Raw alert tetap diaudit, sementara Stability & Noise Control melakukan persistence confirmation, A→B→A oscillation filter, dan cooldown sebelum alert dianggap layak eskalasi.</div></div><span class="daw-badge daw-muted" id="daw-gate">MEMUAT</span></div>' +
    '<div class="daw-grid">' +
      '<div class="daw-kpi"><div class="daw-k">Canonical</div><div class="daw-v" id="daw-signal">—</div><div class="daw-n" id="daw-session">—</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Confirmed</div><div class="daw-v" id="daw-active">—</div><div class="daw-n" id="daw-raw-note">Raw —</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Pending</div><div class="daw-v" id="daw-pending">—</div><div class="daw-n">Menunggu persistence</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Suppressed</div><div class="daw-v" id="daw-suppressed">—</div><div class="daw-n">Noise/cooldown filter</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Risk v0.2</div><div class="daw-v" id="daw-risk">—</div><div class="daw-n">Frozen production formula</div></div>' +
      '<div class="daw-kpi"><div class="daw-k">Final Reasoner</div><div class="daw-v" id="daw-final">—</div><div class="daw-n">Frozen decision logic</div></div>' +
    '</div>' +
    '<div class="daw-panels">' +
      '<div class="daw-panel"><div class="daw-pt">Confirmed Alerts</div><div id="daw-list"></div></div>' +
      '<div class="daw-panel"><div class="daw-pt">Stability & Noise Control</div><div id="daw-stability"></div></div>' +
      '<div class="daw-panel"><div class="daw-pt">Latest Raw Alert Events</div><div id="daw-events"></div></div>' +
      '<div class="daw-panel"><div class="daw-pt">Integrity Guardrail</div><div id="daw-guardrail"></div></div>' +
    '</div>' +
    '<div class="daw-foot">Stable gate mengontrol eskalasi notifikasi saja. Raw alert, Fresh OOS, Decision History, Risk v0.2, dan Final Reasoner tidak diubah. Severity bukan probabilitas rugi/profit.</div>';

  var anchor=document.getElementById('final-intelligence-dashboard')||document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function score(x){return Number.isFinite(Number(x))?Number(x).toFixed(1).replace('.',','):'—';}
  function line(k,v){return '<div class="daw-line"><b>'+esc(k)+' · </b>'+esc(v)+'</div>';}
  function sevClass(s){return s==='HIGH'?'daw-bad':s==='MODERATE'?'daw-warn':'daw-muted';}
  function gateClass(g){return g==='REVIEW_NOW'?'daw-bad':g==='WATCH_CLOSELY'?'daw-warn':g==='STABLE'?'daw-ok':'daw-muted';}
  function gateText(g){return g==='REVIEW_NOW'?'REVIEW SEKARANG':g==='WATCH_CLOSELY'?'PANTAU KETAT':g==='STABLE'?'STABIL':g||'—';}
  function alertCard(a){var st=a.stability||{};var conf=Number.isFinite(Number(st.observed_confirmations))?(st.observed_confirmations+'/'+st.required_confirmations):'—';return '<div class="daw-alert"><div class="daw-row"><div class="daw-a-title">'+esc(a.title||a.key)+'</div><span class="daw-sev '+sevClass(a.severity)+'">'+esc(a.severity||'INFO')+'</span></div><div class="daw-a-detail">'+esc(a.detail||'')+'</div><div class="daw-line">Konfirmasi: '+esc(conf)+' · sumber '+esc(a.source||'—')+'</div></div>';}

  function render(raw,stable){
    if(!raw||raw.status!=='DECISION_ALERT_WATCH_ACTIVE') throw new Error('alert watch unavailable');
    var rs=raw.summary||{}, c=raw.current_watch||{};
    var hasStable=stable&&stable.status==='DECISION_ALERT_STABILITY_ACTIVE';
    var ss=hasStable?(stable.summary||{}):{};
    var gate=hasStable?(ss.stable_gate||rs.alert_gate||'STABLE'):(rs.alert_gate||'STABLE');
    var badge=document.getElementById('daw-gate');badge.className='daw-badge '+gateClass(gate);badge.textContent=gateText(gate);
    document.getElementById('daw-signal').textContent=(c.pair||'—')+' '+(c.canonical_bias||'—');
    document.getElementById('daw-session').textContent=c.session_date?'ECB '+c.session_date:'Sesi —';
    document.getElementById('daw-active').textContent=String(hasStable?(ss.confirmed_total||0):(rs.active_total||0));
    document.getElementById('daw-pending').textContent=String(hasStable?(ss.pending_total||0):0);
    document.getElementById('daw-suppressed').textContent=String(hasStable?(ss.suppressed_total||0):0);
    document.getElementById('daw-raw-note').textContent='Raw '+(rs.alert_gate||'—')+' · '+String(rs.active_total||0)+' aktif';
    document.getElementById('daw-risk').textContent=c.risk?score(c.risk.score)+' · '+(c.risk.state||'—'):'—';
    document.getElementById('daw-final').textContent=c.final_reasoner?((c.final_reasoner.status||'—')+' · '+(c.final_reasoner.decision||'—')):'—';

    var active=hasStable?(stable.confirmed_alerts||[]):(raw.active_alerts||[]);
    document.getElementById('daw-list').innerHTML=active.length?active.slice(0,8).map(alertCard).join(''):'<div class="daw-line"><b>Tidak ada confirmed alert material.</b> Kondisi raw dapat tetap terlihat pada audit event.</div>';

    if(hasStable){
      var o=stable.oscillation||{}, cfg=stable.config||{};
      document.getElementById('daw-stability').innerHTML=
        line('Stable gate',ss.stable_gate||'—')+
        line('Raw gate',ss.raw_gate||'—')+
        line('Oscillation',o.classification||'—')+
        line('Affected',Array.isArray(o.affected)&&o.affected.length?o.affected.join(', '):'Tidak ada')+
        line('Cooldown',(cfg.cooldown_minutes||'—')+' menit')+
        line('Eligible run ini',String(ss.notification_eligible_this_run||0))+
        line('Suppressed run ini',String(ss.notification_suppressed_this_run||0));
    }else{
      document.getElementById('daw-stability').innerHTML='<div class="daw-line">Stability data belum tersedia; UI menampilkan raw Decision Alert gate.</div>';
    }

    var events=Array.isArray(raw.events)?raw.events.slice(-8).reverse():[];
    document.getElementById('daw-events').innerHTML=events.length?events.map(function(e){return line((e.event_type||'EVENT')+' · '+(e.severity||'INFO'),(e.title||e.alert_key)+' — '+(e.detail||''));}).join(''):'<div class="daw-line">Belum ada alert event.</div>';

    var a=c.anchors||{};
    document.getElementById('daw-guardrail').innerHTML=
      line('Decision History',a.decision_history?a.decision_history.id:'—')+
      line('Fresh OOS',a.fresh_oos?a.fresh_oos.id:'—')+
      line('Raw alert log','Append-only + SHA-256')+
      line('Stability delivery log',hasStable?'Append-only + SHA-256':'Menunggu')+
      line('Model tuning','TIDAK')+
      line('Signal voting','TIDAK')+
      line('Trade execution','TIDAK');
  }

  Promise.all([
    fetch('./data/decision-alerts.json',{headers:{Accept:'application/json'},cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}),
    fetch('./data/decision-alert-stability.json',{headers:{Accept:'application/json'},cache:'no-store'}).then(function(r){if(!r.ok)return null;return r.json();}).catch(function(){return null;})
  ]).then(function(x){render(x[0],x[1]);})
    .catch(function(){var b=document.getElementById('daw-gate');if(b){b.className='daw-badge daw-muted';b.textContent='MENUNGGU DATA';}});
})();
