(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!liveSection||document.getElementById('fresh-oos-monitoring')) return;

  var style=document.createElement('style');
  style.textContent=
    '.oosmon{margin-top:12px;padding:15px;border-radius:14px;border:1px solid rgba(52,211,153,.24);background:linear-gradient(180deg,rgba(52,211,153,.045),rgba(7,11,20,.16));font-size:.76rem}' +
    '.oosmon-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap}' +
    '.oosmon-eyebrow{font-size:.57rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted-2);font-weight:800}' +
    '.oosmon-title{margin-top:3px;font-size:.98rem;font-weight:850;color:var(--text)}' +
    '.oosmon-sub{margin-top:4px;font-size:.62rem;line-height:1.45;color:var(--muted);max-width:760px}' +
    '.oosmon-badge{display:inline-flex;align-items:center;border-radius:999px;padding:4px 8px;font-size:.55rem;font-weight:850;letter-spacing:.04em;white-space:nowrap}' +
    '.oosmon-ok{background:var(--green-dim);color:var(--green)}' +
    '.oosmon-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.oosmon-bad{background:var(--red-dim);color:var(--red)}' +
    '.oosmon-muted{background:rgba(148,163,184,.09);color:var(--muted)}' +
    '.oosmon-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;margin-top:10px}' +
    '@media(min-width:760px){.oosmon-grid{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
    '.oosmon-kpi{border:1px solid var(--border);border-radius:10px;padding:8px 9px;background:rgba(7,11,20,.22);min-width:0}' +
    '.oosmon-k{font-size:.5rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted-2)}' +
    '.oosmon-v{margin-top:4px;font-size:.8rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.oosmon-n{margin-top:3px;font-size:.55rem;color:var(--muted);line-height:1.35}' +
    '.oosmon-progress{margin-top:7px;height:5px;border-radius:999px;background:rgba(148,163,184,.1);overflow:hidden}' +
    '.oosmon-progress>span{display:block;height:100%;border-radius:999px;background:var(--green);width:0}' +
    '.oosmon-panels{display:grid;grid-template-columns:1fr;gap:8px;margin-top:9px}' +
    '@media(min-width:840px){.oosmon-panels{grid-template-columns:1fr 1fr}}' +
    '.oosmon-panel{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.18);min-width:0}' +
    '.oosmon-pt{font-size:.55rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);font-weight:800;margin-bottom:5px}' +
    '.oosmon-line{font-size:.6rem;color:var(--muted);line-height:1.45;margin-top:4px}' +
    '.oosmon-line b{color:var(--text);font-weight:750}' +
    '.oosmon-phase{display:grid;grid-template-columns:1fr;gap:6px}' +
    '.oosmon-phase-row{display:grid;grid-template-columns:82px 1fr;gap:8px;align-items:start;padding:6px 0;border-bottom:1px solid rgba(148,163,184,.08)}' +
    '.oosmon-phase-row:last-child{border-bottom:0}' +
    '.oosmon-phase-k{font-size:.54rem;font-weight:850;color:var(--text)}' +
    '.oosmon-phase-v{font-size:.58rem;line-height:1.42;color:var(--muted)}' +
    '.oosmon-foot{margin-top:9px;padding-top:8px;border-top:1px solid var(--border);font-size:.55rem;line-height:1.42;color:var(--muted-2)}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='fresh-oos-monitoring';
  box.className='oosmon';
  box.innerHTML=
    '<div class="oosmon-head"><div><div class="oosmon-eyebrow">Fresh OOS Monitoring</div><div class="oosmon-title">Validasi Prospektif Model</div><div class="oosmon-sub">Memantau prediction yang dibekukan sebelum outcome diketahui. Model tetap frozen sampai sampel OOS cukup untuk evaluasi.</div></div><div><span class="oosmon-badge oosmon-muted" id="oosmon-gate">MEMUAT</span></div></div>' +
    '<div class="oosmon-grid">' +
      '<div class="oosmon-kpi"><div class="oosmon-k">Captured</div><div class="oosmon-v" id="oosmon-captured">—</div><div class="oosmon-n">Prediction immutable</div></div>' +
      '<div class="oosmon-kpi"><div class="oosmon-k">Settled</div><div class="oosmon-v" id="oosmon-settled">—</div><div class="oosmon-n">Outcome diketahui</div></div>' +
      '<div class="oosmon-kpi"><div class="oosmon-k">Pending</div><div class="oosmon-v" id="oosmon-pending">—</div><div class="oosmon-n">Menunggu ECB berikutnya</div></div>' +
      '<div class="oosmon-kpi"><div class="oosmon-k">Preliminary Gate</div><div class="oosmon-v" id="oosmon-prelim">—</div><div class="oosmon-n">Target 20 settled</div></div>' +
      '<div class="oosmon-kpi"><div class="oosmon-k">Primary Gate</div><div class="oosmon-v" id="oosmon-primary">—</div><div class="oosmon-n">Target 60 settled</div><div class="oosmon-progress"><span id="oosmon-bar"></span></div></div>' +
      '<div class="oosmon-kpi"><div class="oosmon-k">Model Status</div><div class="oosmon-v">FROZEN</div><div class="oosmon-n">No retuning during collection</div></div>' +
    '</div>' +
    '<div class="oosmon-panels">' +
      '<div class="oosmon-panel"><div class="oosmon-pt">Latest Frozen Prediction</div><div id="oosmon-latest-pred"></div></div>' +
      '<div class="oosmon-panel"><div class="oosmon-pt">Latest Settled Outcome</div><div id="oosmon-latest-outcome"></div></div>' +
      '<div class="oosmon-panel"><div class="oosmon-pt">Evaluation Protocol</div><div class="oosmon-phase">' +
        '<div class="oosmon-phase-row"><div class="oosmon-phase-k">0–19</div><div class="oosmon-phase-v">Monitoring dan integrity check saja. Tidak ada tuning model.</div></div>' +
        '<div class="oosmon-phase-row"><div class="oosmon-phase-k">20–59</div><div class="oosmon-phase-v">Preliminary evaluation. Hasil boleh dibaca sebagai diagnosis awal, tetapi threshold/bobot tetap frozen.</div></div>' +
        '<div class="oosmon-phase-row"><div class="oosmon-phase-k">≥60</div><div class="oosmon-phase-v">Primary OOS evaluation. Setelah evaluasi selesai barulah keputusan optimasi model boleh dipertimbangkan.</div></div>' +
      '</div></div>' +
      '<div class="oosmon-panel"><div class="oosmon-pt">Integrity & Research Guardrails</div><div id="oosmon-integrity"></div></div>' +
    '</div>' +
    '<div class="oosmon-foot">Primary outcome: directional continuation dari canonical pair/bias yang dibekukan sampai complete ECB observation berikutnya. Fresh OOS adalah validasi prospektif, bukan backfill dan bukan probability of profit.</div>';

  var anchor=document.getElementById('final-intelligence-dashboard')||document.getElementById('provider-confirmation')||pairPanel;
  if(anchor&&anchor!==pairPanel) anchor.insertAdjacentElement('afterend',box); else if(pairPanel) pairPanel.appendChild(box); else liveSection.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function n(x){return Number.isFinite(Number(x))?Number(x):0;}
  function score(x,d){return Number.isFinite(Number(x))?Number(x).toFixed(d==null?1:d).replace('.',','):'—';}
  function line(k,v){return '<div class="oosmon-line"><b>'+esc(k)+' · </b>'+esc(v)+'</div>';}
  function gateLabel(settled,prelim,primary){
    if(settled>=primary) return {text:'PRIMARY GATE TERCAPAI',cls:'oosmon-ok'};
    if(settled>=prelim) return {text:'PRELIMINARY EVALUATION',cls:'oosmon-warn'};
    return {text:'COLLECTING · MODEL FROZEN',cls:'oosmon-muted'};
  }
  function shortHash(h){return h?String(h).slice(0,12)+'…':'—';}

  function render(t){
    if(!t||t.status!=='FRESH_OOS_COLLECTION_ACTIVE'||!Array.isArray(t.entries)) throw new Error('Fresh OOS tracker unavailable');
    var s=t.summary||{};
    var captured=n(s.captured||t.entries.length), settled=n(s.settled), pending=n(s.pending);
    var prelim=n(s.preliminary_target||t.policy&&t.policy.preliminary_settled_target||20);
    var primary=n(s.primary_target||t.policy&&t.policy.primary_settled_target||60);
    var g=gateLabel(settled,prelim,primary);
    var gb=document.getElementById('oosmon-gate');gb.className='oosmon-badge '+g.cls;gb.textContent=g.text;
    document.getElementById('oosmon-captured').textContent=String(captured);
    document.getElementById('oosmon-settled').textContent=String(settled);
    document.getElementById('oosmon-pending').textContent=String(pending);
    document.getElementById('oosmon-prelim').textContent=settled+' / '+prelim;
    document.getElementById('oosmon-primary').textContent=settled+' / '+primary;
    document.getElementById('oosmon-bar').style.width=Math.max(0,Math.min(100,primary?100*settled/primary:0))+'%';

    var latest=t.entries[t.entries.length-1];
    var p=latest&&latest.prediction||{};
    var pa=p.upstream&&p.upstream.actionability||{};
    var pr=p.intelligence&&p.intelligence.risk||{};
    var pf=p.intelligence&&p.intelligence.final_reasoner||{};
    document.getElementById('oosmon-latest-pred').innerHTML=latest?
      line('ID',latest.id||'—')+
      line('ECB session',p.session_date||'—')+
      line('Canonical',String(p.pair||'—')+' · '+String(p.bias||'—'))+
      line('Actionability',score(pa.score)+' · '+String(pa.state||'—'))+
      line('Risk v0.2',score(pr.score)+' · '+String(pr.state||'—'))+
      line('Final Reasoner',String(pf.status||'—')+' · '+String(pf.decision||'—'))+
      line('Prediction hash',shortHash(latest.prediction_hash)):
      '<div class="oosmon-line">Belum ada prediction.</div>';

    var settledEntries=t.entries.filter(function(e){return e&&e.outcome&&e.outcome.status==='SETTLED';});
    var lastSettled=settledEntries[settledEntries.length-1];
    if(lastSettled){
      var o=lastSettled.outcome||{};var pp=lastSettled.prediction||{};
      document.getElementById('oosmon-latest-outcome').innerHTML=
        line('Prediction',String(pp.session_date||'—')+' · '+String(pp.pair||'—')+' '+String(pp.bias||'—'))+
        line('Outcome session',o.outcome_session_date||'—')+
        line('Directional return',score(o.directional_return_pct,4)+'%')+
        line('Result',o.flat?'FLAT':o.hit?'HIT':'MISS')+
        line('Settlement source',o.source||'ECB reference rates');
    }else{
      document.getElementById('oosmon-latest-outcome').innerHTML='<div class="oosmon-line"><b>Belum ada settlement.</b> Outcome pertama baru dicatat ketika complete ECB observation yang lebih baru tersedia.</div>';
    }

    var remainingPrelim=Math.max(0,prelim-settled),remainingPrimary=Math.max(0,primary-settled);
    document.getElementById('oosmon-integrity').innerHTML=
      line('Start policy','Prospective only · no historical backfill')+
      line('Capture unit','1 immutable prediction per complete ECB session')+
      line('Settlement','Next complete ECB observation only')+
      line('Immutability','SHA-256 prediction hash')+
      line('Remaining to preliminary',remainingPrelim+' settled observation(s)')+
      line('Remaining to primary',remainingPrimary+' settled observation(s)')+
      line('Optimization gate',settled>=primary?'Eligible for primary evaluation first':'LOCKED until primary OOS evaluation');
  }

  fetch('./data/fresh-oos-tracker.json',{headers:{Accept:'application/json'},cache:'no-store'})
    .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
    .then(render)
    .catch(function(){var b=document.getElementById('oosmon-gate');if(b){b.className='oosmon-badge oosmon-bad';b.textContent='DATA OOS TIDAK TERSEDIA';}});
})();
