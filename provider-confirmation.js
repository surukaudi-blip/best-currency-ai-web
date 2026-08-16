(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('provider-confirmation')) return;

  var style=document.createElement('style');
  style.textContent=
    '.provider-confirm{margin-top:12px;padding:14px;border-radius:12px;background:var(--bg-3);border:1px solid var(--border);font-size:.78rem}' +
    '.provider-confirm-title{font-size:.69rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted-2);font-weight:700;margin-bottom:10px}' +
    '.intel-grid{display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:10px}' +
    '@media(min-width:560px){.intel-grid{grid-template-columns:repeat(3,1fr)}}' +
    '.intel-card{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.28)}' +
    '.intel-card .k{font-size:.62rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted-2);margin-bottom:4px}' +
    '.intel-card .v{font-size:.98rem;font-weight:800;color:var(--text)}' +
    '.intel-card .s{font-size:.65rem;color:var(--muted);margin-top:2px}' +
    '.provider-badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 7px;font-size:.6rem;font-weight:800;letter-spacing:.05em;margin-left:5px;vertical-align:1px}' +
    '.provider-high{background:var(--green-dim);color:var(--green)}' +
    '.provider-moderate{background:var(--amber-dim);color:var(--amber)}' +
    '.provider-low{background:var(--red-dim);color:var(--red)}' +
    '.provider-unavailable{background:rgba(148,163,184,.08);color:var(--muted)}' +
    '.provider-line{color:var(--muted);line-height:1.55}.provider-line b{color:var(--text);font-weight:700}' +
    '.provider-note{margin-top:5px;color:var(--muted-2);font-size:.7rem;line-height:1.45}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='provider-confirmation';
  box.className='provider-confirm';
  box.innerHTML=
    '<div class="provider-confirm-title">Currency Strength Intelligence</div>' +
    '<div class="intel-grid">' +
      '<div class="intel-card"><div class="k">Provider Agreement</div><div class="v" id="provider-score">—</div><div class="s" id="provider-state">Loading…</div></div>' +
      '<div class="intel-card"><div class="k">MTF Alignment</div><div class="v" id="mtf-score">—</div><div class="s" id="mtf-state">Daily · Weekly · Monthly</div></div>' +
      '<div class="intel-card"><div class="k">Strength Percentile</div><div class="v" id="strength-percentile">—</div><div class="s" id="strength-percentile-sub">Historical context</div></div>' +
    '</div>' +
    '<div class="provider-line" id="provider-confirm-line">Checking cross-provider confirmation…</div>' +
    '<div class="provider-note" id="provider-confirm-note">ECB remains the canonical Currency Strength source.</div>';
  var reversal=document.getElementById('reversal-box');
  if(reversal) reversal.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  var activeTf='daily';
  var latest=null;

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function tfLabel(tf){return tf==='weekly'?'Weekly':tf==='monthly'?'Monthly':'Daily';}
  function stateClass(state){return state==='HIGH'?'provider-high':state==='MODERATE'?'provider-moderate':state==='LOW'?'provider-low':'provider-unavailable';}
  function ordinal(n){
    var v=Math.round(Number(n));
    if(!Number.isFinite(v)) return '—';
    var mod100=v%100;
    var suffix=(mod100>=11&&mod100<=13)?'th':(v%10===1?'st':v%10===2?'nd':v%10===3?'rd':'th');
    return v+suffix;
  }
  function snap(data,tf){return data&&data.strength_timeframes&&data.strength_timeframes[tf];}

  function render(){
    var entry=latest&&latest.confirmation_layer&&latest.confirmation_layer.timeframes&&latest.confirmation_layer.timeframes[activeTf];
    var mtf=latest&&latest.multi_timeframe_alignment;
    var active=snap(latest,activeTf);
    var pct=active&&active.strength_percentile;

    var providerScore=document.getElementById('provider-score');
    var providerState=document.getElementById('provider-state');
    if(entry&&entry.available!==false&&Number.isFinite(Number(entry.agreement_score))){
      var state=String(entry.agreement||'LOW').toUpperCase();
      providerScore.innerHTML=Number(entry.agreement_score).toFixed(1)+'/100 <span class="provider-badge '+stateClass(state)+'">'+esc(state)+'</span>';
      providerState.textContent=tfLabel(activeTf)+' cross-provider confirmation';
    }else{
      providerScore.textContent='—';
      providerState.textContent='Confirmation unavailable';
    }

    var mtfScore=document.getElementById('mtf-score');
    var mtfState=document.getElementById('mtf-state');
    if(mtf&&Number.isFinite(Number(mtf.score))){
      var mtfStatus=String(mtf.state||'LOW').toUpperCase();
      mtfScore.innerHTML=Number(mtf.score).toFixed(1)+'/100 <span class="provider-badge '+stateClass(mtfStatus)+'">'+esc(mtfStatus)+'</span>';
      var leaders=mtf.timeframe_leaders||{};
      mtfState.textContent='D '+((leaders.daily&&leaders.daily.strongest)||'—')+' · W '+((leaders.weekly&&leaders.weekly.strongest)||'—')+' · M '+((leaders.monthly&&leaders.monthly.strongest)||'—');
    }else{
      mtfScore.textContent='—';
      mtfState.textContent='MTF analytics unavailable';
    }

    var percentile=document.getElementById('strength-percentile');
    var percentileSub=document.getElementById('strength-percentile-sub');
    if(pct&&Number.isFinite(Number(pct.gap_percentile))){
      percentile.textContent=ordinal(pct.gap_percentile)+' pct';
      var st=pct.strongest||{}, wk=pct.weakest||{};
      percentileSub.textContent=(st.currency||'—')+' '+ordinal(st.directional_percentile)+' · '+(wk.currency||'—')+' '+ordinal(wk.directional_percentile);
    }else{
      percentile.textContent='—';
      percentileSub.textContent='Not enough historical samples';
    }

    var line=document.getElementById('provider-confirm-line');
    var note=document.getElementById('provider-confirm-note');
    if(!entry||entry.available===false){
      line.textContent='No aligned blended-provider confirmation is available for '+tfLabel(activeTf)+'.';
      note.textContent='ECB remains canonical; primary strength and history are unchanged.';
      return;
    }
    var p=entry.primary||{}, c=entry.confirmation||{};
    var rho=Number(entry.rank_correlation);
    line.innerHTML='<b>'+esc(tfLabel(activeTf))+'</b> · ECB '+esc((p.strongest||'—')+'/'+(p.weakest||'—'))+' · Blended '+esc((c.strongest||'—')+'/'+(c.weakest||'—'))+(Number.isFinite(rho)?' · Rank corr '+rho.toFixed(2):'');
    var adjustment=entry.confidence_adjustment||'NONE';
    note.textContent=adjustment==='NONE'?'Cross-provider evidence supports the ECB view.':adjustment==='CAUTION'?'Partial provider divergence detected; interpret confidence with caution.':'Material provider divergence detected; reduce reliance on the strength signal until other agents confirm it.';
  }

  function load(){
    fetch('./data/currency-strength.json',{headers:{Accept:'application/json'},cache:'no-store'})
      .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
      .then(function(payload){latest=payload&&payload.data?payload.data:payload;render();})
      .catch(function(){
        document.getElementById('provider-score').textContent='—';
        document.getElementById('mtf-score').textContent='—';
        document.getElementById('strength-percentile').textContent='—';
        document.getElementById('provider-confirm-line').textContent='Currency Strength Intelligence could not be loaded.';
      });
  }

  liveSection.addEventListener('click',function(e){
    var btn=e.target.closest('.tf-card');
    if(!btn) return;
    activeTf=btn.getAttribute('data-tf')||'daily';
    render();
  });
  var refresh=document.getElementById('live-refresh');
  if(refresh) refresh.addEventListener('click',function(){setTimeout(load,250);});
  load();
  setInterval(load,60000);
})();
