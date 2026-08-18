(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('provider-confirmation')) return;

  var style=document.createElement('style');
  style.textContent=
    '.provider-confirm{margin-top:12px;padding:14px;border-radius:12px;background:var(--bg-3);border:1px solid var(--border);font-size:.78rem}' +
    '.provider-confirm-title{font-size:.69rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted-2);font-weight:700;margin-bottom:10px}' +
    '.intel-grid{display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:9px}' +
    '@media(min-width:560px){.intel-grid{grid-template-columns:repeat(2,1fr)}.actionability-card{grid-column:1/-1}}' +
    '@media(min-width:980px){.intel-grid{grid-template-columns:repeat(3,1fr)}.actionability-card{grid-column:1/-1}}' +
    '.intel-card{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.28)}' +
    '.intel-card.actionability-card{border-color:rgba(47,211,238,.48);background:rgba(47,211,238,.06)}' +
    '.intel-card .k{font-size:.62rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted-2);margin-bottom:4px}' +
    '.intel-card .v{font-size:.98rem;font-weight:800;color:var(--text)}.actionability-card .v{font-size:1.12rem;line-height:1.3}.actionability-card .v .provider-badge{display:flex;width:max-content;margin:6px 0 0}' +
    '.intel-card .s{font-size:.65rem;color:var(--muted);margin-top:2px;line-height:1.45}' +
    '.provider-badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 7px;font-size:.6rem;font-weight:800;letter-spacing:.05em;margin-left:5px;vertical-align:1px}' +
    '.provider-high{background:var(--green-dim);color:var(--green)}' +
    '.provider-moderate{background:var(--amber-dim);color:var(--amber)}' +
    '.provider-low{background:var(--red-dim);color:var(--red)}' +
    '.provider-unavailable{background:rgba(148,163,184,.08);color:var(--muted)}' +
    '.action-gates{display:grid;grid-template-columns:repeat(2,1fr);gap:6px;margin:8px 0 10px}' +
    '@media(min-width:760px){.action-gates{grid-template-columns:repeat(2,1fr)}}' +
    '.action-gate{display:flex;align-items:center;justify-content:space-between;gap:6px;border:1px solid var(--border);border-radius:8px;padding:7px 8px;background:rgba(7,11,20,.22)}' +
    '.action-gate .gk{font-size:.58rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted-2)}' +
    '.action-gate .gv{font-size:.64rem;font-weight:800;color:var(--text);text-align:right;line-height:1.25}' +
    '.regime-panel{display:flex;gap:10px;align-items:flex-start;justify-content:space-between;margin:10px 0;padding:11px 12px;border:1px solid var(--border);border-radius:10px;background:rgba(7,11,20,.25)}' +
    '.regime-panel.regime-good{border-color:rgba(59,214,154,.35);background:rgba(59,214,154,.05)}' +
    '.regime-panel.regime-warn{border-color:rgba(240,163,47,.35);background:rgba(240,163,47,.05)}' +
    '.regime-panel.regime-bad{border-color:rgba(242,109,109,.35);background:rgba(242,109,109,.05)}' +
    '.regime-k{font-size:.61rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted-2)}' +
    '.regime-v{font-size:.92rem;font-weight:800;color:var(--text);margin-top:2px}' +
    '.regime-s{font-size:.66rem;color:var(--muted);line-height:1.45;margin-top:3px}' +
    '.regime-status{white-space:nowrap}' +
    '.provider-line{color:var(--muted);line-height:1.55}.provider-line b{color:var(--text);font-weight:700}' +
    '.provider-note{margin-top:5px;color:var(--muted-2);font-size:.7rem;line-height:1.45}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='provider-confirmation';
  box.className='provider-confirm';
  box.innerHTML=
    '<div class="provider-confirm-title">Intelijen Kekuatan Mata Uang</div>' +
    '<div class="intel-grid">' +
      '<div class="intel-card actionability-card"><div class="k">Actionability Score</div><div class="v" id="actionability-score">—</div><div class="s" id="actionability-state">Memuat kelayakan evaluasi…</div></div>' +
      '<div class="intel-card"><div class="k">Keselarasan Penyedia</div><div class="v" id="provider-score">—</div><div class="s" id="provider-state">Memuat…</div></div>' +
      '<div class="intel-card"><div class="k">Keselarasan Multi-Timeframe</div><div class="v" id="mtf-score">—</div><div class="s" id="mtf-state">Harian · Mingguan · Bulanan</div></div>' +
      '<div class="intel-card"><div class="k">Persentil Kekuatan</div><div class="v" id="strength-percentile">—</div><div class="s" id="strength-percentile-sub">Konteks historis</div></div>' +
    '</div>' +
    '<div class="action-gates">' +
      '<div class="action-gate"><span class="gk">Bukti</span><span class="gv" id="gate-evidence">—</span></div>' +
      '<div class="action-gate"><span class="gk">Regime</span><span class="gv" id="gate-regime">—</span></div>' +
      '<div class="action-gate"><span class="gk">Pair</span><span class="gv" id="gate-pair">—</span></div>' +
      '<div class="action-gate"><span class="gk">Data</span><span class="gv" id="gate-data">—</span></div>' +
    '</div>' +
    '<div class="regime-panel" id="regime-panel"><div><div class="regime-k">Regime Pasar</div><div class="regime-v" id="regime-name">—</div><div class="regime-s" id="regime-note">Memeriksa guardrail kondisi pasar…</div></div><div class="regime-status" id="regime-status">—</div></div>' +
    '<div class="provider-line" id="provider-confirm-line">Memeriksa konfirmasi lintas penyedia…</div>' +
    '<div class="provider-note" id="provider-confirm-note">ECB tetap menjadi sumber acuan utama Kekuatan Mata Uang.</div>';
  var reversal=document.getElementById('reversal-box');
  if(reversal) reversal.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  var activeTf='daily';
  var latest=null;

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function tfLabel(tf){return tf==='weekly'?'Mingguan':tf==='monthly'?'Bulanan':'Harian';}
  function stateClass(state){return state==='HIGH'?'provider-high':state==='MODERATE'?'provider-moderate':state==='LOW'?'provider-low':'provider-unavailable';}
  function stateLabel(state){return state==='HIGH'?'TINGGI':state==='MODERATE'?'SEDANG':state==='LOW'?'RENDAH':'TIDAK TERSEDIA';}
  function actionabilityClass(state){return state==='ACTIONABLE'?'provider-high':state==='SELECTIVE'?'provider-moderate':state==='FILTERED'?'provider-low':'provider-unavailable';}
  function actionabilityLabel(state){return state==='ACTIONABLE'?'LAYAK DIEVALUASI':state==='SELECTIVE'?'SELEKTIF':state==='FILTERED'?'TERFILTER':'TIDAK TERSEDIA';}
  function decisionLabel(state){return state==='EVALUATE_SETUP'?'LANJUT EVALUASI SETUP':state==='REVIEW_SELECTIVELY'?'TINJAU SELEKTIF':state==='DEPRIORITIZE'?'DEPRIORITASKAN':'TIDAK TERSEDIA';}
  function pairConfidenceLabel(state){return state==='HIGH'?'TINGGI':state==='MODERATE_HIGH'?'SEDANG–TINGGI':state==='MODERATE'?'SEDANG':state==='LOW'?'RENDAH':'—';}
  function limiterLabel(state){return ({EVIDENCE_QUALITY:'Bukti',REGIME_GUARDRAIL:'Regime',PAIR_READINESS:'Pair',DATA_READINESS:'Data'})[state]||'—';}
  function yesNo(pass){return pass?'LOLOS':'BATAS';}
  function fmtScore(n){var v=Number(n);return Number.isFinite(v)?v.toFixed(1).replace('.',','):'—';}
  function percentileLabel(n){var v=Math.round(Number(n));return Number.isFinite(v)?'Persentil ke-'+v:'—';}
  function percentileShort(n){var v=Math.round(Number(n));return Number.isFinite(v)?'P'+v:'—';}
  function snap(data,tf){return data&&data.strength_timeframes&&data.strength_timeframes[tf];}
  function regimeLabel(regime){return ({CONFIRMED_TREND:'TREN TERKONFIRMASI',EXTREME_SEPARATION:'SEPARASI EKSTREM',PROVIDER_DIVERGENCE:'DIVERGENSI PENYEDIA',LOW_ALIGNMENT:'KESELARASAN RENDAH',LOW_SEPARATION:'SEPARASI RENDAH',NORMAL:'NORMAL',INSUFFICIENT_DATA:'DATA BELUM CUKUP'})[regime]||String(regime||'—').replace(/_/g,' ');}
  function regimeNote(regime){return ({CONFIRMED_TREND:'Bukti lintas penyedia dan multi-timeframe kuat; persentil berada di zona kelanjutan tren yang tidak ekstrem.',EXTREME_SEPARATION:'Kesenjangan kekuatan sangat ekstrem; risiko kelelahan tren atau mean reversion meningkat.',PROVIDER_DIVERGENCE:'Konfirmasi lintas penyedia lemah. Sinyal ECB tetap acuan, tetapi Actionability dibatasi.',LOW_ALIGNMENT:'Harian, Mingguan, dan Bulanan belum cukup selaras untuk mendukung kelanjutan tren.',LOW_SEPARATION:'Kesenjangan historis terlalu rendah untuk mendukung kelanjutan tren yang kuat.',NORMAL:'Tidak ada kondisi ekstrem, tetapi kualitas bukti belum memenuhi syarat Tren Terkonfirmasi.',INSUFFICIENT_DATA:'Salah satu komponen regime belum tersedia.'})[regime]||'Regime belum tersedia.';}

  function renderGate(id,gate,detail){
    var el=document.getElementById(id);
    if(!el) return;
    if(!gate){el.textContent='—';return;}
    var cls=gate.pass?'provider-high':'provider-low';
    el.innerHTML='<span class="provider-badge '+cls+'">'+yesNo(gate.pass)+'</span>'+(detail?' '+esc(detail):'');
  }

  function render(){
    var entry=latest&&latest.confirmation_layer&&latest.confirmation_layer.timeframes&&latest.confirmation_layer.timeframes[activeTf];
    var mtf=latest&&latest.multi_timeframe_alignment;
    var active=snap(latest,activeTf);
    var pct=active&&active.strength_percentile;
    var composite=latest&&latest.composite_currency_strength_confidence&&latest.composite_currency_strength_confidence.timeframes&&latest.composite_currency_strength_confidence.timeframes[activeTf];
    var actionability=latest&&latest.actionability_score&&latest.actionability_score.timeframes&&latest.actionability_score.timeframes[activeTf];
    var regime=(latest&&latest.currency_strength_regime&&latest.currency_strength_regime.timeframes&&latest.currency_strength_regime.timeframes[activeTf])||(composite&&composite.regime);

    var actionabilityScore=document.getElementById('actionability-score');
    var actionabilityState=document.getElementById('actionability-state');
    if(actionability&&Number.isFinite(Number(actionability.score))){
      var actionState=String(actionability.state||'UNAVAILABLE').toUpperCase();
      actionabilityScore.innerHTML=fmtScore(actionability.score)+'/100 <span class="provider-badge '+actionabilityClass(actionState)+'">'+esc(actionabilityLabel(actionState))+'</span>';
      var pairReady=actionability.dimensions&&actionability.dimensions.pair_readiness;
      var align=pairReady&&pairReady.alignment;
      var alignText=align&&Number.isFinite(Number(align.aligned_count))?align.aligned_count+'/'+align.available_timeframes+' TF':'—';
      actionabilityState.textContent='Pair '+alignText+' · Pembatas: '+limiterLabel(actionability.primary_limiter);

      var gates=actionability.gates||{};
      renderGate('gate-evidence',gates.evidence,fmtScore(gates.evidence&&gates.evidence.score));
      renderGate('gate-regime',gates.regime,({CONFIRMED_TREND:'TREND',EXTREME_SEPARATION:'EKSTREM',PROVIDER_DIVERGENCE:'DIVERGENSI',LOW_ALIGNMENT:'ALIGNMENT RENDAH',LOW_SEPARATION:'SEPARASI RENDAH',NORMAL:'NORMAL',INSUFFICIENT_DATA:'DATA KURANG'})[gates.regime&&gates.regime.code]||'—');
      renderGate('gate-pair',gates.pair,alignText);
      var dg=gates.data;
      var dataText=dg&&Number.isFinite(Number(dg.business_day_age))?dg.business_day_age+' hari kerja':'—';
      renderGate('gate-data',dg,dataText);
    }else{
      actionabilityScore.textContent='—';
      actionabilityState.textContent='Skor kelayakan evaluasi belum tersedia';
      ['gate-evidence','gate-regime','gate-pair','gate-data'].forEach(function(id){var el=document.getElementById(id);if(el)el.textContent='—';});
    }

    var providerScore=document.getElementById('provider-score');
    var providerState=document.getElementById('provider-state');
    if(entry&&entry.available!==false&&Number.isFinite(Number(entry.agreement_score))){
      var state=String(entry.agreement||'LOW').toUpperCase();
      providerScore.innerHTML=fmtScore(entry.agreement_score)+'/100 <span class="provider-badge '+stateClass(state)+'">'+esc(stateLabel(state))+'</span>';
      providerState.textContent='Konfirmasi lintas penyedia · '+tfLabel(activeTf);
    }else{providerScore.textContent='—';providerState.textContent='Konfirmasi penyedia tidak tersedia';}

    var mtfScore=document.getElementById('mtf-score');
    var mtfState=document.getElementById('mtf-state');
    if(mtf&&Number.isFinite(Number(mtf.score))){
      var mtfStatus=String(mtf.state||'LOW').toUpperCase();
      mtfScore.innerHTML=fmtScore(mtf.score)+'/100 <span class="provider-badge '+stateClass(mtfStatus)+'">'+esc(stateLabel(mtfStatus))+'</span>';
      var leaders=mtf.timeframe_leaders||{};
      mtfState.textContent='H '+((leaders.daily&&leaders.daily.strongest)||'—')+' · M '+((leaders.weekly&&leaders.weekly.strongest)||'—')+' · B '+((leaders.monthly&&leaders.monthly.strongest)||'—');
    }else{mtfScore.textContent='—';mtfState.textContent='Analitik multi-timeframe tidak tersedia';}

    var percentile=document.getElementById('strength-percentile');
    var percentileSub=document.getElementById('strength-percentile-sub');
    if(pct&&Number.isFinite(Number(pct.gap_percentile))){
      percentile.textContent=percentileLabel(pct.gap_percentile);
      var st=pct.strongest||{},wk=pct.weakest||{};
      percentileSub.textContent=(st.currency||'—')+' '+percentileShort(st.directional_percentile)+' · '+(wk.currency||'—')+' '+percentileShort(wk.directional_percentile);
    }else{percentile.textContent='—';percentileSub.textContent='Sampel historis belum mencukupi';}

    var regimePanel=document.getElementById('regime-panel');
    var regimeName=document.getElementById('regime-name');
    var regimeStatus=document.getElementById('regime-status');
    var regimeNoteEl=document.getElementById('regime-note');
    if(regime){
      var regimeCode=String(regime.regime||'INSUFFICIENT_DATA');
      regimeName.textContent=regimeLabel(regimeCode);
      regimeNoteEl.textContent=regimeNote(regimeCode);
      var status=String(regime.continuation_status||'UNAVAILABLE');
      var statusText=status==='SUPPORTED'?'MENDUKUNG KELANJUTAN TREN':status==='NEUTRAL'?'NETRAL':status==='FILTERED'?'TERFILTER':'TIDAK TERSEDIA';
      var statusClass=status==='SUPPORTED'?'provider-high':status==='NEUTRAL'?'provider-moderate':status==='FILTERED'?'provider-low':'provider-unavailable';
      regimeStatus.innerHTML='<span class="provider-badge '+statusClass+'">'+esc(statusText)+'</span>';
      regimePanel.className='regime-panel '+(status==='SUPPORTED'?'regime-good':status==='FILTERED'?'regime-bad':'regime-warn');
    }else{regimeName.textContent='—';regimeNoteEl.textContent='Regime belum tersedia pada snapshot ini.';regimeStatus.textContent='—';regimePanel.className='regime-panel';}

    var line=document.getElementById('provider-confirm-line');
    var note=document.getElementById('provider-confirm-note');
    if(!entry||entry.available===false){line.textContent='Konfirmasi penyedia gabungan yang selaras tanggal belum tersedia untuk timeframe '+tfLabel(activeTf)+'.';note.textContent='ECB tetap menjadi acuan utama; skor kekuatan dan riwayat utama tidak berubah.';return;}
    var p=entry.primary||{},c=entry.confirmation||{};
    var rho=Number(entry.rank_correlation);
    line.innerHTML='<b>'+esc(tfLabel(activeTf))+'</b> · ECB '+esc((p.strongest||'—')+'/'+(p.weakest||'—'))+' · Gabungan '+esc((c.strongest||'—')+'/'+(c.weakest||'—'))+(Number.isFinite(rho)?' · Korelasi peringkat '+rho.toFixed(2).replace('.',','):'');
    var adjustment=entry.confidence_adjustment||'NONE';
    note.textContent=adjustment==='NONE'?'Bukti lintas penyedia mendukung pandangan ECB.':adjustment==='CAUTION'?'Terdapat sebagian perbedaan antarpenyedia; interpretasikan tingkat keyakinan dengan hati-hati.':'Terdapat perbedaan material antarpenyedia; kurangi ketergantungan pada sinyal kekuatan sampai agen lain memberikan konfirmasi.';
  }

  function load(){
    fetch('./data/currency-strength.json?v=73eb1d019d',{headers:{Accept:'application/json'},cache:'no-store'})
      .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
      .then(function(payload){latest=payload&&payload.data?payload.data:payload;render();})
      .catch(function(){document.getElementById('actionability-score').textContent='—';document.getElementById('provider-score').textContent='—';document.getElementById('mtf-score').textContent='—';document.getElementById('strength-percentile').textContent='—';document.getElementById('regime-name').textContent='—';document.getElementById('provider-confirm-line').textContent='Intelijen Kekuatan Mata Uang tidak dapat dimuat.';});
  }

  liveSection.addEventListener('click',function(e){var btn=e.target.closest('.tf-card');if(!btn)return;activeTf=btn.getAttribute('data-tf')||'daily';render();});
  var refresh=document.getElementById('live-refresh');
  if(refresh)refresh.addEventListener('click',function(){setTimeout(load,250);});
  load();
  setInterval(load,60000);
})();