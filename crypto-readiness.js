(function(){
  'use strict';

  var METHOD='CRYPTO_READINESS_UI_0.2';
  var decisionData=null;
  var scheduled=false;

  function ready(fn){
    if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',fn,{once:true});
    else fn();
  }
  function esc(s){
    return String(s==null?'—':s).replace(/[&<>"']/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }
  function clean(s){return String(s==null?'—':s).replace(/_/g,' ');}
  function n(v){return Number.isFinite(Number(v))?Number(v):null;}
  function pct(v){var x=n(v);return x===null?'—':x.toFixed(2)+'%';}
  function clamp(v){return Math.max(0,Math.min(100,Number(v)||0));}
  function activeSymbol(){
    var tab=document.querySelector('#tabs .tab.active');
    if(tab) return tab.dataset.t||tab.textContent.trim();
    return decisionData&&decisionData.symbols&&decisionData.symbols[0]?decisionData.symbols[0].symbol:null;
  }
  function asset(symbol){
    return decisionData&&Array.isArray(decisionData.symbols)?decisionData.symbols.find(function(x){return x.symbol===symbol;}):null;
  }
  function regime(x){
    var a=x&&x.actionability||{};
    var d=a.dimensions||{};
    var r=d.regime_guardrail||{};
    return {
      ceiling:n(r.score),
      vol:String(r.volatility_regime||'UNKNOWN_VOL').toUpperCase(),
      volPct:n(r.volatility_30d_annualized_percent),
      drawdown:String(r.drawdown_regime||'UNKNOWN_DRAWDOWN').toUpperCase(),
      drawdownPct:n(r.drawdown_from_90d_high_percent)
    };
  }
  function toneClass(state){
    state=String(state||'').toUpperCase();
    if(/PASS|LOW_VOL|LOW$|ACTIONABLE|SUPPORTIVE|PRESSURED|STRONG/.test(state)) return 'good';
    if(/CAUTION|MODERATE|SELECTIVE|MIXED/.test(state)) return 'warn';
    if(/FAIL|HIGH|FILTERED|UNKNOWN/.test(state)) return 'bad';
    return 'neutral';
  }

  function addStyle(){
    if(document.getElementById('crypto-readiness-final-style')) return;
    var style=document.createElement('style');
    style.id='crypto-readiness-final-style';
    style.textContent=
      '#crypto-decision-readiness{margin:10px 0 16px}' +
      '.cr-panel{--cr-tone:var(--amber);--cr-pct:0%;border:1px solid var(--line2);border-radius:18px;background:linear-gradient(180deg,rgba(17,26,41,.84),rgba(8,13,22,.78));overflow:hidden}' +
      '.cr-panel.high{--cr-tone:var(--green)}.cr-panel.partial{--cr-tone:var(--amber)}.cr-panel.low{--cr-tone:var(--red)}' +
      '.cr-head{display:grid;grid-template-columns:1fr;gap:16px;padding:19px 21px;border-bottom:1px solid var(--line)}' +
      '@media(min-width:850px){.cr-head{grid-template-columns:1fr auto;align-items:center}}' +
      '.cr-eyebrow{font-size:.59rem;letter-spacing:.12em;text-transform:uppercase;color:var(--cyan);font-weight:900}' +
      '.cr-title{margin-top:5px;font-size:1.15rem;font-weight:950;color:var(--text)}' +
      '.cr-sub{margin-top:6px;max-width:940px;font-size:.66rem;line-height:1.55;color:var(--muted)}' +
      '.cr-summary{display:flex;align-items:center;gap:13px}' +
      '.cr-ring{width:88px;height:88px;border-radius:50%;background:conic-gradient(var(--cr-tone) var(--cr-pct),rgba(148,163,184,.12) 0);display:grid;place-items:center;position:relative;flex:0 0 auto}' +
      '.cr-ring:after{content:"";position:absolute;inset:8px;border-radius:50%;background:var(--p);border:1px solid var(--line)}' +
      '.cr-ring strong{position:relative;z-index:1;font-size:1.34rem;letter-spacing:-.04em}' +
      '.cr-met{font-size:.76rem;font-weight:900}.cr-primary{display:inline-flex;margin-top:7px;padding:6px 9px;border-radius:999px;font-size:.54rem;font-weight:950;letter-spacing:.03em}' +
      '.cr-primary.pass{background:var(--greenD);color:var(--green)}.cr-primary.fail{background:var(--redD);color:var(--red)}' +
      '.cr-body{padding:15px 21px 18px}.cr-progress{height:7px;border-radius:999px;background:rgba(148,163,184,.1);overflow:hidden;border:1px solid var(--line)}' +
      '.cr-progress i{display:block;height:100%;width:var(--cr-pct);background:var(--cr-tone);border-radius:999px}' +
      '.cr-scale{display:flex;justify-content:space-between;gap:8px;margin-top:6px;font-size:.51rem;color:var(--muted2)}' +
      '.cr-blockers,.cr-why{display:flex;gap:9px;align-items:flex-start;margin-top:11px;padding:10px 12px;border:1px solid var(--line);border-radius:11px;background:rgba(7,11,20,.2);font-size:.58rem;line-height:1.48}' +
      '.cr-blockers.clear{border-color:rgba(59,214,154,.2);background:rgba(59,214,154,.035)}.cr-label{font-weight:900;color:var(--muted2);white-space:nowrap}.cr-value{font-weight:800;color:var(--text)}' +
      '.cr-why{border-color:rgba(240,163,47,.2);background:rgba(240,163,47,.025)}.cr-why.clear{display:none}' +
      '.cr-checks{display:grid;grid-template-columns:1fr;gap:8px;margin-top:13px}@media(min-width:760px){.cr-checks{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(min-width:1180px){.cr-checks{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
      '.cr-check{border:1px solid var(--line);border-radius:11px;padding:10px;background:rgba(7,11,20,.18);min-width:0}.cr-check.caution{border-color:rgba(240,163,47,.24);background:rgba(240,163,47,.025)}.cr-check.fail{border-color:rgba(242,109,109,.2)}' +
      '.cr-check-top{display:flex;align-items:center;gap:7px}.cr-icon{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:.62rem;font-weight:950;flex:0 0 auto}' +
      '.cr-check.pass .cr-icon{background:var(--greenD);color:var(--green)}.cr-check.caution .cr-icon{background:var(--amberD);color:var(--amber)}.cr-check.fail .cr-icon{background:var(--redD);color:var(--red)}' +
      '.cr-check-name{font-size:.58rem;font-weight:900;color:var(--text);line-height:1.25}.cr-check-status{margin-left:auto;font-size:.48rem;font-weight:950;letter-spacing:.04em}.cr-check.pass .cr-check-status{color:var(--green)}.cr-check.caution .cr-check-status{color:var(--amber)}.cr-check.fail .cr-check-status{color:var(--red)}' +
      '.cr-check-detail{margin-top:7px;font-size:.53rem;line-height:1.45;color:var(--muted)}' +
      '.cr-explain{margin-top:12px;border:1px solid var(--line);border-radius:11px;background:rgba(7,11,20,.14);overflow:hidden}.cr-explain summary{cursor:pointer;list-style:none;padding:10px 12px;font-size:.59rem;font-weight:900;color:var(--text);display:flex;justify-content:space-between}.cr-explain summary::-webkit-details-marker{display:none}.cr-explain summary:after{content:"+";color:var(--cyan);font-size:.8rem}.cr-explain[open] summary:after{content:"−"}' +
      '.cr-explain-body{border-top:1px solid var(--line);padding:10px 12px;display:grid;gap:7px}.cr-explain-row{display:grid;grid-template-columns:minmax(120px,.8fr) 1.5fr auto;gap:9px;font-size:.54rem;line-height:1.45}.cr-explain-name{font-weight:850;color:var(--text)}.cr-explain-reason{color:var(--muted)}.cr-points{font-weight:950;white-space:nowrap}.cr-points.pass{color:var(--green)}.cr-points.fail{color:var(--red)}' +
      '.cr-final{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-top:12px;padding:12px 14px;border:1px solid rgba(47,211,238,.2);border-radius:11px;background:rgba(47,211,238,.03)}.cr-final-decision{font-size:.67rem;font-weight:950}.cr-guard{font-size:.54rem;color:var(--muted);line-height:1.45}.cr-guard b{color:var(--cyan)}' +
      '.cr-regime-score .value{font-size:1.22rem!important}.cr-regime-score .sub{line-height:1.35!important}' +
      '@media(min-width:1100px){#pane .scoreboard{grid-template-columns:1fr 1.42fr 1fr 1fr 1fr 1fr!important}.thresholds{grid-template-columns:repeat(5,minmax(0,1fr))!important}}' +
      '@media(max-width:700px){.cr-head,.cr-body{padding-left:14px;padding-right:14px}.cr-explain-row{grid-template-columns:1fr}.cr-points{justify-self:start}}';
    document.head.appendChild(style);
  }

  function updateStrategyChain(){
    var hero=document.querySelector('.hero p');
    if(hero) hero.textContent='Baca strategi sebagai persentase: Direction → Daily/Weekly/Monthly → MTF → Regime → Risk → Actionability. Persentase score menunjukkan posisi pada skala model 0–100, bukan peluang profit.';
    var chain=document.querySelector('.strategy-chain');
    if(chain) chain.innerHTML='<span><b>1</b> Direction %</span>→<span><b>2</b> D/W/M %</span>→<span><b>3</b> MTF %</span>→<span><b>4</b> Regime</span>→<span><b>5</b> Risk %</span>→<span><b>6</b> Actionability %</span>';
  }

  function checksFor(x){
    var m=x.market_structure||{};
    var mtf=x.multi_timeframe_alignment||{};
    var a=x.actionability||{};
    var risk=x.decision_risk||{};
    var ct=x.counter_thesis||{};
    var rg=regime(x);

    var direction=String(m.state||'UNAVAILABLE').toUpperCase();
    var directionPass=direction==='SUPPORTIVE'||direction==='PRESSURED';

    var mtfScore=n(mtf.score);
    var mtfStatus=mtfScore!==null&&mtfScore>=80?'pass':mtfScore!==null&&mtfScore>=60?'caution':'fail';

    var regimeStatus=rg.ceiling!==null&&rg.ceiling>=80?'pass':rg.ceiling!==null&&rg.ceiling>=60?'caution':'fail';

    var riskState=String(risk.state||'UNAVAILABLE').toUpperCase();
    var riskStatus=riskState==='LOW'?'pass':riskState==='MODERATE'?'caution':'fail';

    var ctStrength=String(ct.strength||'UNAVAILABLE').toUpperCase();
    var ctStatus=ctStrength==='LOW'?'pass':ctStrength==='MODERATE'?'caution':'fail';

    var actionState=String(a.state||'UNAVAILABLE').toUpperCase();
    var actionScore=n(a.score);
    var actionPass=actionState==='ACTIONABLE'&&actionScore!==null&&actionScore>=80;
    var actionStatus=actionPass?'pass':actionState==='SELECTIVE'?'caution':'fail';

    return [
      {name:'Canonical Direction',status:directionPass?'pass':'fail',detail:pct(m.score)+' · '+clean(direction),reason:directionPass?'Canonical v0.1 memiliki arah directional yang valid.':'Canonical v0.1 masih MIXED / tidak directional.'},
      {name:'MTF Alignment',status:mtfStatus,detail:pct(mtf.score)+' · '+clean(mtf.state),reason:mtfStatus==='pass'?'Konfirmasi lintas timeframe STRONG.':mtfStatus==='caution'?'Konfirmasi lintas timeframe hanya MODERATE.':'Konfirmasi lintas timeframe belum memadai.'},
      {name:'Regime Guardrail',status:regimeStatus,detail:(rg.ceiling===null?'—':pct(rg.ceiling)+' ceiling')+' · '+clean(rg.vol),reason:regimeStatus==='pass'?'Regime mengizinkan tier ACTIONABLE.':regimeStatus==='caution'?'Regime membatasi Actionability; perlu review selektif.':'Regime membatasi prioritas secara kuat / tidak tersedia.'},
      {name:'Decision Risk',status:riskStatus,detail:pct(risk.score)+' · '+clean(riskState),reason:riskStatus==='pass'?'Decision Risk LOW.':riskStatus==='caution'?'Decision Risk MODERATE; tetap perlu kehati-hatian.':'Decision Risk HIGH / tidak tersedia.'},
      {name:'Counter-Thesis',status:ctStatus,detail:clean(ctStrength),reason:ctStatus==='pass'?'Counter-thesis rendah.':ctStatus==='caution'?'Counter-thesis moderat; tesis perlu diuji ulang.':'Counter-thesis tinggi / tidak tersedia.'},
      {name:'Actionability Gate',status:actionStatus,primary:true,detail:pct(a.score)+' · '+clean(actionState),reason:actionPass?'Primary Gate lulus: ACTIONABLE ≥80%.':actionState==='SELECTIVE'?'Primary Gate belum lulus: SELECTIVE adalah review-only.':'Primary Gate belum lulus: FILTERED / tidak actionable.'}
    ];
  }

  function ensurePanel(){
    var title=document.querySelector('.section-title');
    if(!title) return null;
    var panel=document.getElementById('crypto-decision-readiness');
    if(panel) return panel;
    panel=document.createElement('section');
    panel.id='crypto-decision-readiness';
    panel.className='cr-panel low';
    panel.dataset.methodology=METHOD;
    title.insertAdjacentElement('afterend',panel);
    return panel;
  }

  function renderPanel(x){
    var panel=ensurePanel();
    if(!panel) return;
    var checks=checksFor(x);
    var passed=checks.filter(function(c){return c.status==='pass';}).length;
    var readiness=Math.round((passed/checks.length)*100);
    var primary=checks[5].status==='pass';
    var blocked=checks.filter(function(c){return c.status!=='pass';});
    var tone=primary&&passed>=5?'high':readiness>=50?'partial':'low';
    panel.className='cr-panel '+tone;
    panel.style.setProperty('--cr-pct',readiness+'%');

    var a=x.actionability||{};
    var ai=x.ai_decision_reasoner||{};
    var decision=primary?(passed===6?'PRIORITIZE REVIEW · FULL READINESS':'PRIORITIZE REVIEW · CONDITIONAL'):(String(a.state||'').toUpperCase()==='SELECTIVE'?'REVIEW SELECTIVELY · PRIMARY GATE NOT PASSED':'DEPRIORITIZE · PRIMARY GATE NOT PASSED');
    var blockers=blocked.length?blocked.map(function(c){return c.name;}).join(' · '):'Tidak ada blocker aktif.';
    var why=blocked.length?blocked.map(function(c){return c.name+': '+c.reason;}).join(' '):'';

    panel.innerHTML=
      '<div class="cr-head"><div><div class="cr-eyebrow">Decision Readiness · 6-check framework</div><div class="cr-title">'+esc(x.symbol)+' · Apakah kondisi sudah layak diprioritaskan?</div><div class="cr-sub">Readiness mengukur kelengkapan persyaratan review. <b>Actionability adalah Primary Gate</b>; SELECTIVE/FILTERED tidak boleh dibaca sebagai gate yang lulus atau sebagai peluang profit.</div></div>'+
      '<div class="cr-summary"><div class="cr-ring"><strong>'+readiness+'%</strong></div><div><div class="cr-met">'+passed+' / 6 checks met</div><span class="cr-primary '+(primary?'pass':'fail')+'">PRIMARY GATE · '+(primary?'PASSED':'NOT PASSED')+'</span></div></div></div>'+
      '<div class="cr-body"><div class="cr-progress"><i></i></div><div class="cr-scale"><span>0% · BLOCKED</span><span>50% · PARTIAL</span><span>100% · ALL REQUIREMENTS</span></div>'+
      '<div class="cr-blockers '+(blocked.length?'':'clear')+'"><span class="cr-label">Current blockers</span><span class="cr-value">'+esc(blockers)+'</span></div>'+
      '<div class="cr-why '+(blocked.length?'':'clear')+'"><span class="cr-label">Why blocked?</span><span class="cr-value">'+esc(why)+'</span></div>'+
      '<div class="cr-checks">'+checks.map(function(c){return '<div class="cr-check '+c.status+'"><div class="cr-check-top"><span class="cr-icon">'+(c.status==='pass'?'✓':c.status==='caution'?'!':'×')+'</span><span class="cr-check-name">'+esc(c.name)+(c.primary?' · PRIMARY':'')+'</span><span class="cr-check-status">'+(c.status==='pass'?'PASS':c.status==='caution'?'CAUTION':'FAIL')+'</span></div><div class="cr-check-detail">'+esc(c.detail)+'</div></div>';}).join('')+'</div>'+
      '<details class="cr-explain"><summary>Why this score?</summary><div class="cr-explain-body">'+checks.map(function(c){return '<div class="cr-explain-row"><span class="cr-explain-name">'+esc(c.name)+'</span><span class="cr-explain-reason">'+esc(c.reason)+'</span><span class="cr-points '+(c.status==='pass'?'pass':'fail')+'">'+(c.status==='pass'?'+1 check':'0 check')+'</span></div>';}).join('')+'</div></details>'+
      '<div class="cr-final"><div class="cr-final-decision">'+esc(decision)+'</div><div class="cr-guard"><b>Governance:</b> '+esc(clean(ai.decision||a.decision||'Review only'))+' · readiness ≠ win probability · trade execution OFF.</div></div></div>';
  }

  function injectRegimeCard(x){
    var board=document.querySelector('#pane .scoreboard');
    if(!board) return;
    var rg=regime(x);
    var existing=board.querySelector('.cr-regime-score');
    if(existing) existing.remove();

    var card=document.createElement('div');
    var state=rg.ceiling!==null&&rg.ceiling>=80?'LOW_VOL':rg.ceiling!==null&&rg.ceiling>=60?'MODERATE':'HIGH_OR_UNKNOWN';
    card.className='score-card cr-regime-score '+toneClass(state);
    card.innerHTML='<div class="k">Regime Guardrail</div><div class="value">'+pct(rg.ceiling)+'</div><div class="sub">'+esc(clean(rg.vol))+' · ceiling'+(rg.drawdown&&rg.drawdown!=='UNKNOWN_DRAWDOWN'?' · '+esc(clean(rg.drawdown)):'')+'</div><div class="meter"><i style="width:'+clamp(rg.ceiling)+'%"></i></div>';

    var riskCard=Array.from(board.querySelectorAll('.score-card')).find(function(c){
      var k=c.querySelector('.k'); return k&&/Decision Risk/i.test(k.textContent);
    });
    if(riskCard) board.insertBefore(card,riskCard); else board.appendChild(card);

    var disclaimer=board.querySelector('.score-disclaimer');
    if(disclaimer) disclaimer.innerHTML='<b>Score ≠ probability:</b> angka di atas adalah posisi pada skala model 0–100%. Gunakan urutan baca Direction → D/W/M → MTF → Regime → Risk → Actionability.';

    var thresholds=document.querySelector('#pane .thresholds');
    if(thresholds&&!thresholds.querySelector('[data-cr-regime-threshold]')){
      var t=document.createElement('div');
      t.className='threshold';
      t.dataset.crRegimeThreshold='1';
      t.innerHTML='<b>Regime Guardrail</b>LOW_VOL: boleh ACTIONABLE · MODERATE_VOL: maks. 70% · HIGH_VOL: maks. 55% · STRESSED_DRAWDOWN: maks. 60%';
      var kids=thresholds.querySelectorAll('.threshold');
      if(kids.length>=3) thresholds.insertBefore(t,kids[2]); else thresholds.appendChild(t);
    }
  }

  function renderCurrent(){
    if(!decisionData) return;
    var symbol=activeSymbol();
    var x=asset(symbol);
    if(!x) return;
    renderPanel(x);
    injectRegimeCard(x);
  }
  function schedule(){
    if(scheduled) return;
    scheduled=true;
    setTimeout(function(){scheduled=false;renderCurrent();},0);
  }

  ready(function(){
    addStyle();
    updateStrategyChain();

    document.addEventListener('click',function(e){
      if(e.target&&e.target.closest&&e.target.closest('#tabs .tab')) schedule();
    });

    var tabs=document.getElementById('tabs');
    if(tabs&&window.MutationObserver){
      new MutationObserver(schedule).observe(tabs,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
    }

    fetch('./data/crypto-decision-intelligence.json',{cache:'no-store'})
      .then(function(r){if(!r.ok) throw new Error('crypto decision artifact unavailable');return r.json();})
      .then(function(d){decisionData=d;schedule();})
      .catch(function(){
        var panel=ensurePanel();
        if(panel) panel.innerHTML='<div class="cr-body"><div class="cr-final-decision">Decision Readiness belum tersedia karena artifact Crypto tidak dapat dimuat.</div></div>';
      });
  });
})();
