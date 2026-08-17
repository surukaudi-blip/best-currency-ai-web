(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('intelligence-timeline')) return;

  var style=document.createElement('style');
  style.textContent=
    '.itl{margin-top:12px;padding:15px;border-radius:14px;border:1px solid var(--border);background:rgba(7,11,20,.18);font-size:.76rem}' +
    '.itl-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap}' +
    '.itl-eyebrow{font-size:.57rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted-2);font-weight:800}' +
    '.itl-title{margin-top:3px;font-size:.96rem;font-weight:850;color:var(--text)}' +
    '.itl-sub{margin-top:4px;font-size:.62rem;line-height:1.45;color:var(--muted)}' +
    '.itl-badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:.55rem;font-weight:850;letter-spacing:.04em;white-space:nowrap}' +
    '.itl-ok{background:var(--green-dim);color:var(--green)}' +
    '.itl-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.itl-bad{background:var(--red-dim);color:var(--red)}' +
    '.itl-muted{background:rgba(148,163,184,.09);color:var(--muted)}' +
    '.itl-summary{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}' +
    '@media(min-width:720px){.itl-summary{grid-template-columns:repeat(4,minmax(0,1fr))}}' +
    '.itl-kpi{border:1px solid var(--border);border-radius:10px;padding:8px 9px;background:rgba(7,11,20,.22)}' +
    '.itl-k{font-size:.53rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2)}' +
    '.itl-v{margin-top:4px;font-size:.82rem;font-weight:850;color:var(--text)}' +
    '.itl-track{position:relative;margin-top:11px;padding-left:17px;display:grid;gap:8px}' +
    '.itl-track:before{content:"";position:absolute;left:5px;top:7px;bottom:7px;width:1px;background:var(--border-2)}' +
    '.itl-item{position:relative;border:1px solid var(--border);border-radius:11px;padding:10px;background:rgba(7,11,20,.2)}' +
    '.itl-item:before{content:"";position:absolute;left:-16px;top:14px;width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px rgba(47,211,238,.11)}' +
    '.itl-top{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;flex-wrap:wrap}' +
    '.itl-date{font-size:.61rem;color:var(--muted-2);font-weight:700}' +
    '.itl-pair{margin-top:2px;font-size:.86rem;font-weight:850;color:var(--text)}' +
    '.itl-status{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}' +
    '.itl-metrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;margin-top:8px}' +
    '@media(min-width:700px){.itl-metrics{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
    '.itl-metric{padding:6px 7px;border-radius:8px;background:rgba(148,163,184,.045);min-width:0}' +
    '.itl-mk{font-size:.5rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted-2)}' +
    '.itl-mv{margin-top:2px;font-size:.61rem;font-weight:800;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.itl-change{margin-top:7px;font-size:.58rem;line-height:1.42;color:var(--muted)}' +
    '.itl-change b{color:var(--text)}' +
    '.itl-foot{margin-top:9px;padding-top:8px;border-top:1px solid var(--border);font-size:.56rem;color:var(--muted-2);line-height:1.42}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='intelligence-timeline';
  box.className='itl';
  box.innerHTML=
    '<div class="itl-head"><div><div class="itl-eyebrow">Decision History</div><div class="itl-title">Intelligence Timeline</div><div class="itl-sub">Riwayat immutable per sesi ECB: sinyal, Actionability, konteks, Risk, Counter-Thesis, dan Final Reasoner.</div></div><span class="itl-badge itl-muted" id="itl-status">MEMUAT</span></div>' +
    '<div class="itl-summary">' +
      '<div class="itl-kpi"><div class="itl-k">Snapshot</div><div class="itl-v" id="itl-count">—</div></div>' +
      '<div class="itl-kpi"><div class="itl-k">Periode</div><div class="itl-v" id="itl-period">—</div></div>' +
      '<div class="itl-kpi"><div class="itl-k">BUY / SELL</div><div class="itl-v" id="itl-bias-count">—</div></div>' +
      '<div class="itl-kpi"><div class="itl-k">Sesi Terakhir</div><div class="itl-v" id="itl-latest">—</div></div>' +
    '</div>' +
    '<div class="itl-track" id="itl-track"><div class="itl-item"><div class="itl-date">Menunggu Decision History…</div></div></div>' +
    '<div class="itl-foot">Prospective-only dan append-only. Timeline tidak melakukan backfill historis, tidak men-tuning model, dan tidak menggantikan Fresh OOS Validation Tracker.</div>';

  var dashboard=document.getElementById('final-intelligence-dashboard');
  var anchor=dashboard||document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function score(n){return Number.isFinite(Number(n))?Number(n).toFixed(1).replace('.',','):'—';}
  function biasLabel(x){return x==='BUY'?'BELI':x==='SELL'?'JUAL':'TUNGGU';}
  function stateLabel(x){return ({SUPPORTS:'MENDUKUNG',OPPOSES:'MENENTANG',NEUTRAL:'NETRAL',MIXED:'CAMPURAN',LOW:'RENDAH',MODERATE:'SEDANG',HIGH:'TINGGI',ACTIONABLE:'ACTIONABLE',SELECTIVE:'SELEKTIF',FILTERED:'TERFILTER',CONTEXT_CONFIRMED:'KONTEKS TERKONFIRMASI',CONTEXT_CONTRADICTED:'KONTEKS BERTENTANGAN',MIXED_CONTEXT:'KONTEKS CAMPURAN',RISK_CONSTRAINED:'DIBATASI RISIKO'})[String(x||'').toUpperCase()]||String(x||'—').replace(/_/g,' ');}
  function decisionLabel(x){return ({EVALUATE_SETUP:'EVALUASI SETUP',REVIEW_SELECTIVELY:'TINJAU SELEKTIF',DEPRIORITIZE:'TURUNKAN PRIORITAS',WAIT_FOR_CONTEXT:'TUNGGU KONTEKS'})[x]||String(x||'—').replace(/_/g,' ');}
  function cls(x){var s=String(x||'').toUpperCase();if(['SUPPORTS','LOW','ACTIONABLE','CONTEXT_CONFIRMED','EVALUATE_SETUP'].includes(s))return'itl-ok';if(['OPPOSES','HIGH','FILTERED','CONTEXT_CONTRADICTED','RISK_CONSTRAINED','DEPRIORITIZE'].includes(s))return'itl-bad';if(['NEUTRAL','MIXED','MODERATE','SELECTIVE','MIXED_CONTEXT','REVIEW_SELECTIVELY'].includes(s))return'itl-warn';return'itl-muted';}
  function metric(k,v){return '<div class="itl-metric"><div class="itl-mk">'+esc(k)+'</div><div class="itl-mv">'+esc(v)+'</div></div>';}
  function contextValue(layer){return layer&&layer.available?score(layer.score)+' · '+stateLabel(layer.state):'TIDAK TERSEDIA';}

  function render(history){
    var status=document.getElementById('itl-status');
    if(!history||!Array.isArray(history.entries)){
      status.className='itl-badge itl-bad';status.textContent='TIDAK TERSEDIA';return;
    }
    var s=history.summary||{};
    status.className='itl-badge itl-ok';status.textContent='AKTIF · '+history.entries.length+' SESI';
    document.getElementById('itl-count').textContent=String(s.captured||history.entries.length);
    document.getElementById('itl-period').textContent=(s.first_session||'—')+(s.last_session&&s.last_session!==s.first_session?' → '+s.last_session:'');
    document.getElementById('itl-bias-count').textContent=(s.buy_count||0)+' / '+(s.sell_count||0);
    document.getElementById('itl-latest').textContent=s.last_session||'—';

    var entries=history.entries.slice(-8).reverse();
    var track=document.getElementById('itl-track');
    track.innerHTML=entries.map(function(entry){
      var x=entry.snapshot||{};
      var a=x.actionability||{},c=x.context||{},r=x.risk||{},ct=x.counter_thesis||{},f=x.final_reasoner||{};
      var changes=Array.isArray(entry.changes_vs_previous)?entry.changes_vs_previous.slice(0,3):[];
      return '<div class="itl-item">' +
        '<div class="itl-top"><div><div class="itl-date">ECB '+esc(x.session_date||'—')+' · '+esc(entry.id||'—')+'</div><div class="itl-pair">'+esc(x.pair||'—')+' · '+esc(biasLabel(x.canonical_bias))+'</div></div><div class="itl-status"><span class="itl-badge '+cls(f.status)+'">'+esc(stateLabel(f.status))+'</span><span class="itl-badge '+cls(f.decision)+'">'+esc(decisionLabel(f.decision))+'</span></div></div>' +
        '<div class="itl-metrics">' +
          metric('Actionability',score(a.score)+' · '+stateLabel(a.state)) +
          metric('Macro & Yield',contextValue(c.macro_yield)) +
          metric('Cross-Market',contextValue(c.cross_market)) +
          metric('News',contextValue(c.news)) +
          metric('Risk',score(r.score)+' · '+stateLabel(r.state)) +
          metric('Counter-Thesis',(ct.challenge_level||'—')+' · '+(ct.state||'—')) +
        '</div>' +
        '<div class="itl-change">'+(changes.length?changes.map(function(ch){return '<div><b>'+esc(ch.label)+' · </b>'+esc(ch.detail)+'</div>';}).join(''):'Tidak ada ringkasan perubahan.')+'</div>' +
      '</div>';
    }).join('') || '<div class="itl-item"><div class="itl-date">Belum ada snapshot Decision History.</div></div>';
  }

  fetch('./data/decision-history.json',{headers:{Accept:'application/json'},cache:'no-store'})
    .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
    .then(render)
    .catch(function(){var status=document.getElementById('itl-status');if(status){status.className='itl-badge itl-muted';status.textContent='MENUNGGU SNAPSHOT';}});
})();
