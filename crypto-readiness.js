(function(){
  var METHOD='CRYPTO_READINESS_UI_0.1';
  var data=null;
  var currentSymbol=null;
  var lastRegimeSymbol=null;

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
  function num(n){return Number.isFinite(Number(n))?Number(n):null;}
  function pct(n){var v=num(n);return v===null?'—':v.toFixed(2)+'%';}
  function signedPct(n){var v=num(n);return v===null?'—':(v>=0?'+':'')+v.toFixed(2)+'%';}
  function clamp(n){return Math.max(0,Math.min(100,Number(n)||0));}
  function sessionLabel(s){
    if(!s) return '—';
    var p=String(s).split('-');
    if(p.length===3) return p[2]+' '+(['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'][Number(p[1])-1]||p[1])+' '+p[0];
    return s;
  }
  function assetBySymbol(symbol){
    return data&&Array.isArray(data.symbols)?data.symbols.find(function(x){return x.symbol===symbol;}):null;
  }
  function selectedSymbol(){
    var active=document.querySelector('#tabs .tab.active');
    return active&&active.dataset.t || currentSymbol || (data&&data.symbols&&data.symbols[0]&&data.symbols[0].symbol) || null;
  }

  function addStyle(){
    if(document.getElementById('crypto-readiness-style')) return;
    var style=document.createElement('style');
    style.id='crypto-readiness-style';
    style.textContent=
      '#crypto-decision-readiness{margin:14px 0 18px}' +
      '.cr-panel{border:1px solid var(--line2);border-radius:18px;background:linear-gradient(180deg,rgba(148,163,184,.045),rgba(7,11,20,.2));overflow:hidden;--cr-tone:var(--amber);--cr-pct:0%}' +
      '.cr-panel.high{--cr-tone:var(--green)}.cr-panel.partial{--cr-tone:var(--amber)}.cr-panel.low{--cr-tone:var(--red)}' +
      '.cr-head{display:grid;grid-template-columns:1fr;gap:16px;padding:20px 22px;border-bottom:1px solid var(--line)}' +
      '@media(min-width:820px){.cr-head{grid-template-columns:1fr auto;align-items:center}}' +
      '.cr-eyebrow{font-size:.61rem;letter-spacing:.12em;text-transform:uppercase;color:var(--cyan);font-weight:900}' +
      '.cr-title{margin-top:5px;font-size:1.18rem;font-weight:900;color:var(--text);line-height:1.25}' +
      '.cr-sub{margin-top:6px;max-width:900px;font-size:.68rem;line-height:1.55;color:var(--muted)}' +
      '.cr-snapshot{margin-top:8px;font-size:.57rem;color:var(--muted2);font-weight:750}' +
      '.cr-summary{display:flex;align-items:center;gap:14px;justify-content:flex-start}' +
      '.cr-ring{width:88px;height:88px;border-radius:50%;background:conic-gradient(var(--cr-tone) var(--cr-pct),rgba(148,163,184,.12) 0);display:grid;place-items:center;position:relative;flex:0 0 auto}' +
      '.cr-ring:after{content:"";position:absolute;inset:8px;border-radius:50%;background:var(--p);border:1px solid var(--line)}' +
      '.cr-ring-pct{position:relative;z-index:1;font-size:1.38rem;font-weight:950;color:var(--text);letter-spacing:-.04em}' +
      '.cr-summary-meta{min-width:150px}.cr-met{font-size:.78rem;font-weight:900;color:var(--text)}' +
      '.cr-primary{display:inline-flex;margin-top:7px;border-radius:999px;padding:6px 9px;font-size:.55rem;font-weight:900;letter-spacing:.04em}' +
      '.cr-primary.pass{background:var(--greenD);color:var(--green)}.cr-primary.fail{background:var(--redD);color:var(--red)}' +
      '.cr-body{padding:16px 22px 18px}' +
      '.cr-progress{height:8px;border-radius:999px;background:rgba(148,163,184,.1);overflow:hidden;border:1px solid var(--line)}' +
      '.cr-progress>span{display:block;height:100%;width:var(--cr-pct);background:var(--cr-tone);border-radius:999px;transition:width .25s ease}' +
      '.cr-scale{display:flex;justify-content:space-between;gap:8px;margin-top:6px;font-size:.52rem;color:var(--muted2)}' +
      '.cr-blockers,.cr-why{display:flex;align-items:flex-start;gap:9px;margin-top:12px;padding:10px 12px;border-radius:11px;border:1px solid var(--line);background:rgba(7,11,20,.18);font-size:.58rem;line-height:1.5}' +
      '.cr-label{color:var(--muted2);font-weight:850;white-space:nowrap}.cr-value{color:var(--text);font-weight:800}' +
      '.cr-blockers.clear{border-color:rgba(59,214,154,.2);background:rgba(59,214,154,.035)}.cr-blockers.clear .cr-value{color:var(--green)}' +
      '.cr-why{margin-top:8px;border-color:rgba(240,163,47,.18);background:rgba(240,163,47,.025)}.cr-why.clear{display:none}' +
      '.cr-checks{display:grid;grid-template-columns:1fr;gap:8px;margin-top:14px}' +
      '@media(min-width:760px){.cr-checks{grid-template-columns:repeat(3,minmax(0,1fr))}}' +
      '@media(min-width:1180px){.cr-checks{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
      '.cr-check{border:1px solid var(--line);border-radius:11px;padding:10px;background:rgba(7,11,20,.18);min-width:0}' +
      '.cr-check.caution{border-color:rgba(240,163,47,.24);background:rgba(240,163,47,.025)}' +
      '.cr-check-top{display:flex;align-items:center;gap:7px}.cr-icon{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font-size:.62rem;font-weight:950;flex:0 0 auto}' +
      '.cr-check.pass .cr-icon{background:var(--greenD);color:var(--green)}.cr-check.caution .cr-icon{background:var(--amberD);color:var(--amber)}.cr-check.fail .cr-icon{background:var(--redD);color:var(--red)}' +
      '.cr-check-name{font-size:.59rem;font-weight:900;color:var(--text);line-height:1.25}.cr-check-status{margin-left:auto;font-size:.49rem;font-weight:950;letter-spacing:.04em;color:var(--muted2);text-align:right}' +
      '.cr-check.caution .cr-check-status{color:var(--amber)}.cr-check.pass .cr-check-status{color:var(--green)}.cr-check.fail .cr-check-status{color:var(--red)}' +
      '.cr-check-detail{margin-top:7px;font-size:.54rem;line-height:1.45;color:var(--muted)}' +
      '.cr-explain{margin-top:12px;border:1px solid var(--line);border-radius:11px;background:rgba(7,11,20,.14);overflow:hidden}' +
      '.cr-explain summary{cursor:pointer;list-style:none;padding:10px 12px;font-size:.59rem;font-weight:900;color:var(--text);display:flex;align-items:center;justify-content:space-between;gap:8px}' +
      '.cr-explain summary::-webkit-details-marker{display:none}.cr-explain summary:after{content:"+";font-size:.78rem;color:var(--cyan)}.cr-explain[open] summary:after{content:"−"}' +
      '.cr-explain-body{border-top:1px solid var(--line);padding:10px 12px;display:grid;gap:7px}' +
      '.cr-explain-row{display:grid;grid-template-columns:minmax(120px,.8fr) 1.5fr auto;gap:9px;align-items:start;font-size:.54rem;line-height:1.45}' +
      '.cr-explain-name{font-weight:850;color:var(--text)}.cr-explain-reason{color:var(--muted)}.cr-points{font-weight:950;white-space:nowrap}.cr-points.pass{color:var(--green)}.cr-points.fail{color:var(--red)}' +
      '.cr-final{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin-top:13px;padding:12px 14px;border-radius:11px;border:1px solid rgba(47,211,238,.2);background:rgba(47,211,238,.03)}' +
      '.cr-final-decision{font-size:.67rem;font-weight:950;color:var(--text)}.cr-guard{font-size:.55rem;color:var(--muted);line-height:1.45}.cr-guard b{color:var(--cyan)}' +
      '.cr-regime-score .value{font-size:1.05rem!important}.cr-regime-score .sub{line-height:1.45!important}' +
      '@media(min-width:1100px){#pane .scoreboard{grid-template-columns:repeat(6,minmax(0,1fr))!important}}' +
      '@media(max-width:700px){.cr-head,.cr-body{padding-left:14px;padding-right:14px}.cr-scale{font-size:.46rem}.cr-explain-row{grid-template-columns:1fr}.cr-points{justify-self:start}}';
    document.head.appendChild(style);
  }

  function ensurePanel(){
    var tabs=document.getElementById('tabs');
    if(!tabs) return null;
    var panel=document.getElementById('crypto-decision-readiness');
    if(panel) return panel;
    panel=document.createElement('section');
    panel.id='crypto-decision-readiness';
    panel.className='cr-panel low';
    panel.dataset.methodology=METHOD;
    tabs.insertAdjacentElement('afterend',panel);
    return panel;
  }

  function regimeInfo(x){
    var a=x&&x.actionability||{};
    var rg=a.dimensions&&a.dimensions.regime_guardrail||{};
    var ceiling=num(rg.score);
    var vol=String(rg.volatility_regime||'UNKNOWN_VOL').toUpperCase();
    var dd=String(rg.drawdown_regime||'UNKNOWN_DRAWDOWN').toUpperCase();
    return {raw:rg,ceiling:ceiling,vol:vol,dd:dd};
  }

  function buildChecks(x){
    var m=x.market_structure||{};
    var mtf=x.multi_timeframe_alignment||{};
    var a=x.actionability||{};
    var risk=x.decision_risk||{};
    var ct=x.counter_thesis||{};
    var rg=regimeInfo(x);

    var directionState=String(m.state||'UNAVAILABLE').toUpperCase();
    var directionPass=directionState==='SUPPORTIVE'||directionState==='PRESSURED';
    var mtfScore=num(mtf.score);
    var mtfPass=mtfScore!==null&&mtfScore>=60;
    var regimePass=rg.ceiling!==null&&rg.ceiling>=80;
    var riskState=String(risk.state||'UNAVAILABLE').toUpperCase();
    var r