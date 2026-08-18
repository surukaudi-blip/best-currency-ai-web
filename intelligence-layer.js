(function(){
  var liveSection=document.getElementById('live-strength');
  var pairPanel=liveSection&&liveSection.querySelector('.pair-panel');
  if(!pairPanel||document.getElementById('intelligence-layer-panel')) return;

  var style=document.createElement('style');
  style.textContent=
    '.intel-layer{margin-top:12px;padding:14px;border-radius:12px;background:var(--bg-3);border:1px solid var(--border);font-size:.78rem}' +
    '.intel-layer-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px}' +
    '.intel-layer-title{font-size:.69rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted-2);font-weight:700}' +
    '.intel-layer-sub{font-size:.66rem;color:var(--muted);margin-top:3px;line-height:1.45}' +
    '.intel-layer-grid{display:grid;grid-template-columns:1fr;gap:8px}' +
    '@media(min-width:560px){.intel-layer-grid{grid-template-columns:repeat(2,1fr)}}' +
    '.intel-stage{border:1px solid var(--border);border-radius:10px;padding:10px;background:rgba(7,11,20,.24);min-width:0}' +
    '.intel-stage.final-stage{border-color:rgba(47,211,238,.45);background:rgba(47,211,238,.05)}' +
    '.intel-stage .stage-k{font-size:.59rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted-2);margin-bottom:5px}' +
    '.intel-stage .stage-v{font-size:.88rem;font-weight:800;color:var(--text);line-height:1.3}' +
    '.intel-stage .stage-s{font-size:.64rem;color:var(--muted);line-height:1.45;margin-top:4px}' +
    '.intel-stage .stage-meta{font-size:.6rem;color:var(--muted-2);line-height:1.4;margin-top:5px}' +
    '.intel-final-explain{margin-top:8px;padding-top:7px;border-top:1px solid var(--border);display:grid;gap:5px}' +
    '.intel-final-row{font-size:.61rem;line-height:1.42;color:var(--muted)}' +
    '.intel-final-row b{color:var(--text);font-weight:700}' +
    '.intel-layer-badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 7px;font-size:.57rem;font-weight:800;letter-spacing:.04em;white-space:nowrap}' +
    '.intel-layer-ok{background:var(--green-dim);color:var(--green)}' +
    '.intel-layer-warn{background:var(--amber-dim);color:var(--amber)}' +
    '.intel-layer-bad{background:var(--red-dim);color:var(--red)}' +
    '.intel-layer-muted{background:rgba(148,163,184,.08);color:var(--muted)}' +
    '.intel-layer-foot{margin-top:9px;padding-top:8px;border-top:1px solid var(--border);font-size:.64rem;color:var(--muted-2);line-height:1.45}';
  document.head.appendChild(style);

  var box=document.createElement('div');
  box.id='intelligence-layer-panel';
  box.className='intel-layer';
  box.innerHTML=
    '<div class="intel-layer-head"><div><div class="intel-layer-title">Intelligence Layer</div><div class="intel-layer-sub">Macro & Yield → Cross-Market → News → Risk → Counter-Thesis → Final Reasoner</div></div><span class="intel-layer-badge intel-layer-muted" id="intel-readiness">MEMUAT</span></div>' +
    '<div class="intel-layer-grid">' +
      '<div class="intel-stage"><div class="stage-k">01 · Macro & Yield</div><div class="stage-v" id="intel-macro-v">—</div><div class="stage-s" id="intel-macro-s">Memeriksa bukti makro dan yield…</div></div>' +
      '<div class="intel-stage"><div class="stage-k">02 · Cross-Market</div><div class="stage-v" id="intel-cross-v">—</div><div class="stage-s" id="intel-cross-s">Memeriksa konfirmasi lintas pasar…</div></div>' +
      '<div class="intel-stage"><div class="stage-k">03 · News</div><div class="stage-v" id="intel-news-v">—</div><div class="stage-s" id="intel-news-s">Memeriksa bukti berita…</div><div class="stage-meta" id="intel-news-meta"></div></div>' +
      '<div class="intel-stage"><div class="stage-k">04 · Risk</div><div class="stage-v" id="intel-risk-v">—</div><div class="stage-s" id="intel-risk-s">Mengukur risiko kontekstual…</div><div class="stage-meta" id="intel-risk-meta"></div></div>' +
      '<div class="intel-stage"><div class="stage-k">05 · Counter-Thesis</div><div class="stage-v" id="intel-counter-v">—</div><div class="stage-s" id="intel-counter-s">Mencari bukti yang menentang setup…</div><div class="stage-meta" id="intel-counter-meta"></div></div>' +
      '<div class="intel-stage final-stage"><div class="stage-k">06 · Final Reasoner</div><div class="stage-v" id="intel-final-v">—</div><div class="stage-s" id="intel-final-s">Menunggu seluruh bukti yang diperlukan…</div><div class="stage-meta" id="intel-final-meta"></div><div class="intel-final-explain" id="intel-final-explain"></div></div>' +
    '</div>' +
    '<div class="intel-layer-foot">Fail-closed: Macro & Yield, Cross-Market, dan News tidak diisi dengan asumsi. Risk v0.2 tetap dibekukan selama Fresh OOS. Counter-Thesis adalah adversarial review. Final Reasoner v0.2 menambahkan explainability tanpa mengubah status/outlook/decision yang sedang diuji.</div>';

  var anchor=document.getElementById('provider-confirmation');
  if(anchor) anchor.insertAdjacentElement('afterend',box); else pairPanel.appendChild(box);

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
  function badge(text,cls){return '<span class="intel-layer-badge '+cls+'">'+esc(text)+'</span>';}
  function stateBadge(state){
    var s=String(state||'UNAVAILABLE').toUpperCase();
    if(s==='SUPPORTS'||s==='LOW'||s==='CONTEXT_CONFIRMED') return badge(s==='SUPPORTS'?'MENDUKUNG':s==='LOW'?'RISIKO RENDAH':'TERKONFIRMASI','intel-layer-ok');
    if(s==='OPPOSES'||s==='HIGH'||s==='CONTEXT_CONTRADICTED'||s==='RISK_CONSTRAINED') return badge(s==='OPPOSES'?'MENENTANG':s==='HIGH'?'RISIKO TINGGI':'TERBATAS','intel-layer-bad');
    if(s==='MIXED'||s==='NEUTRAL'||s==='MODERATE'||s==='ACTIVE'||s==='LIMITED'||s==='MIXED_CONTEXT') return badge(s==='MODERATE'?'RISIKO SEDANG':s==='ACTIVE'?'AKTIF':s==='LIMITED'?'TERBATAS':'CAMPURAN','intel-layer-warn');
    return badge('MENUNGGU DATA','intel-layer-muted');
  }
  function challengeBadge(level){
    var l=String(level||'').toUpperCase();
    if(l==='HIGH') return badge('TANTANGAN TINGGI','intel-layer-bad');
    if(l==='MODERATE') return badge('TANTANGAN SEDANG','intel-layer-warn');
    if(l==='LOW') return badge('TANTANGAN RENDAH','intel-layer-ok');
    return '';
  }
  function firstText(arr,fallback){return Array.isArray(arr)&&arr.length?String(arr[0]):fallback;}
  function firstStatement(arr,fallback){return Array.isArray(arr)&&arr.length&&arr[0]&&arr[0].statement?String(arr[0].statement):fallback;}
  function fmtScore(n){return Number.isFinite(Number(n))?Number(n).toFixed(1).replace('.',','):null;}
  function renderInput(prefix,layer){
    var v=document.getElementById('intel-'+prefix+'-v');
    var s=document.getElementById('intel-'+prefix+'-s');
    if(!v||!s) return;
    if(!layer||!layer.available){
      v.innerHTML=stateBadge('UNAVAILABLE');
      s.textContent='Provider bukti nyata belum tersambung. Tidak ada arah yang diasumsikan.';
      return;
    }
    v.innerHTML=stateBadge(layer.state)+(fmtScore(layer.score)!==null?' '+fmtScore(layer.score)+'/100':'');
    s.textContent=firstText(layer.evidence,layer.note||'Bukti tersedia.');
  }
  function riskDriverLabel(key){
    var map={
      actionability:'Actionability',regime:'Regime',context_coverage:'Cakupan konteks',context_opposition:'Kontradiksi konteks',
      context_dispersion:'Konflik antar-konteks',news_event:'Event berita',reversal:'Risiko reversal',data_uncertainty:'Ketidakpastian data'
    };
    return map[key]||key||'Risiko';
  }
  function counterSourceLabel(key){
    var map={
      macro_yield:'Macro & Yield',cross_market:'Cross-Market',news:'News',risk:'Risk',regime:'Regime',actionability:'Actionability',
      reversal_intelligence:'Reversal','risk.context_dispersion':'Konflik konteks',counter_thesis:'Counter-Thesis'
    };
    return map[key]||key||'—';
  }
  function render(data){
    var intel=data&&data.intelligence_layer;
    if(!intel){
      document.getElementById('intel-readiness').textContent='BELUM TERSEDIA';
      return;
    }
    var layers=intel.layers||{};
    renderInput('macro',layers.macro_yield);
    renderInput('cross',layers.cross_market);
    renderInput('news',layers.news);

    var news=layers.news||{};
    var nm=document.getElementById('intel-news-meta');
    if(nm&&news.available){
      var er=news.event_risk&&news.event_risk.level?String(news.event_risk.level):'—';
      var erLabel=er==='HIGH'?'TINGGI':er==='MODERATE'?'SEDANG':er==='LOW'?'RENDAH':er;
      var headline=Array.isArray(news.headlines)&&news.headlines.length?news.headlines[0].title:'';
      nm.textContent='Risiko event '+erLabel+(headline?' · '+headline:'');
    }else if(nm){nm.textContent='';}

    var risk=layers.risk||{};
    var rv=document.getElementById('intel-risk-v');
    var rs=document.getElementById('intel-risk-s');
    var rm=document.getElementById('intel-risk-meta');
    if(rv) rv.innerHTML=stateBadge(risk.state)+(fmtScore(risk.score)!==null?' '+fmtScore(risk.score)+'/100':'');
    if(rs) rs.textContent=firstText(risk.reasons,risk.note||'Risiko belum tersedia.');
    if(rm){
      var drivers=Array.isArray(risk.primary_drivers)?risk.primary_drivers.slice(0,3):[];
      rm.textContent=drivers.length
        ? 'Driver utama · '+drivers.map(function(d){return riskDriverLabel(d.key)+' +'+fmtScore(d.contribution);}).join(' · ')+(risk.version?' · v'+risk.version:'')
        : (risk.version?'Risk v'+risk.version+' · hanya baseline konservatif':'');
    }

    var counter=layers.counter_thesis||{};
    var cv=document.getElementById('intel-counter-v');
    var cs=document.getElementById('intel-counter-s');
    var cm=document.getElementById('intel-counter-meta');
    if(cv) cv.innerHTML=stateBadge(counter.state)+(counter.challenge_level?' '+challengeBadge(counter.challenge_level):'');
    var primary=counter.primary_objection&&counter.primary_objection.statement?counter.primary_objection.statement:null;
    if(cs) cs.textContent=primary||firstText(counter.objections,counter.note||'Counter-thesis belum tersedia.');
    if(cm){
      var nObj=Array.isArray(counter.structured_objections)?counter.structured_objections.length:Array.isArray(counter.objections)?counter.objections.length:0;
      var source=counter.primary_objection&&counter.primary_objection.source_layer?counterSourceLabel(counter.primary_objection.source_layer):'—';
      var triggered=Array.isArray(counter.triggered_conditions)?counter.triggered_conditions.length:0;
      cm.textContent='Utama · '+source+' · '+nObj+' keberatan'+(triggered?' · '+triggered+' trigger aktif':'')+(counter.version?' · v'+counter.version:'');
    }

    var finalR=layers.final_reasoner||{};
    var fv=document.getElementById('intel-final-v');
    var fs=document.getElementById('intel-final-s');
    var fm=document.getElementById('intel-final-meta');
    var fx=document.getElementById('intel-final-explain');
    if(fv){
      var finalLabel=finalR.outlook&&finalR.outlook!=='NOT_FINAL'?finalR.outlook:'BELUM FINAL';
      fv.innerHTML=esc(finalLabel)+' '+stateBadge(finalR.status);
    }
    if(fs) fs.textContent=finalR.final_assessment||finalR.explanation||'Final Reasoner belum tersedia.';
    if(fm) fm.textContent=(finalR.pair||'—')+' · Bias ECB '+(finalR.canonical_bias||'—')+' · Cakupan konteks '+(Number.isFinite(Number(finalR.contextual_coverage_percent))?finalR.contextual_coverage_percent:'0')+'%'+(finalR.risk_version?' · Risk v'+finalR.risk_version:'')+(finalR.counter_thesis_version?' · CT v'+finalR.counter_thesis_version:'')+(finalR.version?' · FR v'+finalR.version:'');
    if(fx){
      var evFor=firstStatement(finalR.evidence_for,'Belum ada bukti pendukung yang terstruktur.');
      var evAgainst=firstStatement(finalR.evidence_against,'Tidak ada keberatan langsung yang terstruktur.');
      var keyRisk=finalR.key_risk&&finalR.key_risk.reason?finalR.key_risk.reason:'Risiko utama belum tersedia.';
      var inv=Array.isArray(finalR.invalidation_conditions)&&finalR.invalidation_conditions.length?(finalR.invalidation_conditions.find(function(x){return x&&x.triggered;})||finalR.invalidation_conditions[0]):null;
      fx.innerHTML=
        '<div class="intel-final-row"><b>Bukti mendukung · </b>'+esc(evFor)+'</div>'+
        '<div class="intel-final-row"><b>Bukti menentang · </b>'+esc(evAgainst)+'</div>'+
        '<div class="intel-final-row"><b>Risiko utama · </b>'+esc(keyRisk)+'</div>'+
        '<div class="intel-final-row"><b>Invalidasi · </b>'+esc(inv&&inv.condition?inv.condition:'Belum ada kondisi invalidasi terstruktur.')+'</div>';
    }

    var readiness=document.getElementById('intel-readiness');
    var state=String(intel.readiness&&intel.readiness.state||'WAITING_FOR_CONTEXT_PROVIDERS');
    var coverage=Number(intel.readiness&&intel.readiness.external_coverage_percent||0);
    if(readiness){
      readiness.className='intel-layer-badge '+(state==='CONTEXT_READY'?'intel-layer-ok':state==='PARTIAL_CONTEXT'?'intel-layer-warn':'intel-layer-muted');
      readiness.textContent=(state==='CONTEXT_READY'?'KONTEKS SIAP':state==='PARTIAL_CONTEXT'?'KONTEKS PARSIAL':'MENUNGGU PROVIDER')+' · '+coverage+'%';
    }
  }

  function load(){
    fetch('./data/currency-strength.json?v=bee918da78',{headers:{Accept:'application/json'},cache:'no-store'})
      .then(function(r){if(!r.ok)throw new Error('HTTP '+r.status);return r.json();})
      .then(function(payload){render(payload&&payload.data?payload.data:payload);})
      .catch(function(){var el=document.getElementById('intel-readiness');if(el){el.className='intel-layer-badge intel-layer-bad';el.textContent='GAGAL MEMUAT';}});
  }

  var refresh=document.getElementById('live-refresh');
  if(refresh) refresh.addEventListener('click',function(){setTimeout(load,300);});
  load();
  setInterval(load,60000);
})();
