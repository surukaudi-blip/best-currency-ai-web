(function(){
  if(window.__BC_PLATFORM_SHELL__) return;
  window.__BC_PLATFORM_SHELL__=true;

  const params=new URLSearchParams(location.search);
  const embeddedDemo=params.get('demo')==='1';
  if(embeddedDemo) document.documentElement.classList.add('platform-competition-embed');

  const navItems=[
    ['Overview','index.html'],
    ['Markets','markets.html'],
    ['Forex','strength.html'],
    ['Stocks','stocks.html'],
    ['Crypto','crypto.html'],
    ['Intelligence','intelligence.html'],
    ['Decision Watch','decision-watch.html'],
    ['Timeline','timeline.html'],
    ['Validation','validation.html']
  ];
  const current=(location.pathname.split('/').pop()||'index.html').split('?')[0];
  const css=`
    .platform-menu-toggle{display:none;appearance:none;border:1px solid rgba(148,163,184,.24);background:rgba(13,20,32,.9);color:#e7ecf4;border-radius:10px;width:38px;height:38px;align-items:center;justify-content:center;font:800 18px/1 Inter,system-ui;cursor:pointer}
    .platform-mobile-drawer{display:none;position:fixed;z-index:1000;top:66px;left:12px;right:12px;padding:10px;background:rgba(7,11,20,.98);border:1px solid rgba(148,163,184,.2);border-radius:14px;box-shadow:0 18px 55px rgba(0,0,0,.38)}
    .platform-mobile-drawer.open{display:grid;gap:4px}.platform-mobile-drawer a{padding:11px 12px;border-radius:9px;color:#97a5ba;font:700 13px/1.2 Inter,system-ui}.platform-mobile-drawer a:hover,.platform-mobile-drawer a.active{background:rgba(47,211,238,.09);color:#e7ecf4}.platform-mobile-drawer .demo{color:#2fd3ee;border-top:1px solid rgba(148,163,184,.14);margin-top:5px;padding-top:13px}
    .platform-statusbar{border-bottom:1px solid rgba(148,163,184,.12);background:rgba(9,14,24,.92);color:#7f8da3;font:600 11px/1.3 Inter,system-ui}.platform-status-inner{max-width:1180px;margin:auto;padding:7px 20px;display:flex;align-items:center;gap:12px;justify-content:space-between}.platform-status-items{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.platform-status-items b{color:#dce5f1;font-weight:750}.platform-demo-link{border:1px solid rgba(47,211,238,.25);border-radius:999px;padding:5px 9px;color:#2fd3ee;white-space:nowrap}.platform-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#3bd69a;margin-right:5px;box-shadow:0 0 0 3px rgba(59,214,154,.09)}
    .platform-home-cta{display:flex;gap:9px;flex-wrap:wrap;margin-top:20px}.platform-home-cta a{display:inline-flex;align-items:center;justify-content:center;border-radius:10px;padding:11px 16px;font:800 12px/1 Inter,system-ui;border:1px solid rgba(148,163,184,.28)}.platform-home-cta .primary{background:#2fd3ee;color:#04121a;border-color:transparent}.platform-home-cta .secondary{color:#e7ecf4}.platform-pitch-thesis{margin-top:13px;max-width:760px;font:700 12px/1.55 Inter,system-ui;color:#cbd5e1}.platform-pitch-thesis b{color:#2fd3ee}
    .platform-flow{padding:28px 0}.platform-flow-wrap{max-width:1180px;margin:auto;padding:0 20px}.platform-flow-head{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:14px}.platform-flow-head h2{margin:0;font:800 19px/1.2 Inter,system-ui;color:#e7ecf4}.platform-flow-head p{margin:5px 0 0;color:#97a5ba;font:500 12px/1.5 Inter,system-ui}.platform-flow-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.platform-flow-card{border:1px solid rgba(148,163,184,.15);border-radius:15px;padding:17px;background:linear-gradient(180deg,#0d1420,rgba(13,20,32,.72));color:#e7ecf4}.platform-flow-card .n{font:800 10px/1 Inter,system-ui;color:#2fd3ee;letter-spacing:.1em}.platform-flow-card h3{margin:9px 0 5px;font:800 14px/1.2 Inter,system-ui}.platform-flow-card p{margin:0;color:#97a5ba;font:500 11px/1.55 Inter,system-ui}.platform-flow-card a{display:inline-block;margin-top:11px;color:#2fd3ee;font:750 11px/1 Inter,system-ui}
    html.platform-competition-embed header,html.platform-competition-embed .platform-statusbar,html.platform-competition-embed .platform-home-cta,html.platform-competition-embed .platform-pitch-thesis,html.platform-competition-embed .platform-flow{display:none!important}html.platform-competition-embed body{min-height:100vh}html.platform-competition-embed .hero{padding-top:30px!important}
    @media(max-width:930px){.platform-menu-toggle{display:flex}.platform-status-inner{padding:7px 14px}.platform-status-items{gap:8px}.platform-status-items span:nth-child(n+4){display:none}.platform-flow-grid{grid-template-columns:1fr}.platform-demo-link{font-size:10px}}
  `;
  const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);

  const header=document.querySelector('header');
  let status=null;
  if(!embeddedDemo){
    const desktopLinks=document.querySelector('header .links');
    if(desktopLinks){
      const overview=desktopLinks.querySelector('a[href="index.html"]');
      if(!desktopLinks.querySelector('a[href="markets.html"]')){
        const marketLink=document.createElement('a');marketLink.href='markets.html';marketLink.textContent='Markets';if(current==='markets.html')marketLink.classList.add('active');
        if(overview&&overview.nextSibling)desktopLinks.insertBefore(marketLink,overview.nextSibling);else if(overview)desktopLinks.appendChild(marketLink);
      }
      const strength=desktopLinks.querySelector('a[href="strength.html"]');
      if(strength)strength.textContent='Forex';
      if(!desktopLinks.querySelector('a[href="stocks.html"]')){
        const stocksLink=document.createElement('a');stocksLink.href='stocks.html';stocksLink.textContent='Stocks';if(current==='stocks.html')stocksLink.classList.add('active');
        if(strength&&strength.nextSibling)desktopLinks.insertBefore(stocksLink,strength.nextSibling);else if(strength)desktopLinks.appendChild(stocksLink);
      }
      const stocks=desktopLinks.querySelector('a[href="stocks.html"]');
      if(!desktopLinks.querySelector('a[href="crypto.html"]')){
        const cryptoLink=document.createElement('a');cryptoLink.href='crypto.html';cryptoLink.textContent='Crypto';if(current==='crypto.html')cryptoLink.classList.add('active');
        if(stocks&&stocks.nextSibling)desktopLinks.insertBefore(cryptoLink,stocks.nextSibling);else if(stocks)desktopLinks.appendChild(cryptoLink);
      }
    }
    const nav=document.querySelector('header .nav');
    if(nav){
      const btn=document.createElement('button');btn.className='platform-menu-toggle';btn.type='button';btn.setAttribute('aria-label','Open navigation');btn.setAttribute('aria-expanded','false');btn.textContent='☰';nav.appendChild(btn);
      const drawer=document.createElement('nav');drawer.className='platform-mobile-drawer';drawer.setAttribute('aria-label','Mobile navigation');
      drawer.innerHTML=navItems.map(([label,href])=>`<a href="${href}" class="${current===href?'active':''}">${label}</a>`).join('')+`<a class="demo" href="demo.html">FX Competition Demo · 90 sec</a>`;
      document.body.appendChild(drawer);
      btn.addEventListener('click',()=>{const open=drawer.classList.toggle('open');btn.setAttribute('aria-expanded',String(open));btn.textContent=open?'×':'☰'});
      drawer.addEventListener('click',()=>{drawer.classList.remove('open');btn.setAttribute('aria-expanded','false');btn.textContent='☰'});
      document.addEventListener('keydown',e=>{if(e.key==='Escape'){drawer.classList.remove('open');btn.setAttribute('aria-expanded','false');btn.textContent='☰'}});
    }

    status=document.createElement('div');status.className='platform-statusbar';status.innerHTML=`<div class="platform-status-inner"><div class="platform-status-items"><span><i class="platform-dot"></i><b id="platform-market">Forex Live —</b></span><span id="platform-readiness">Decision Readiness —</span><span id="platform-risk">Decision Risk —</span><span id="platform-gate">Decision Gate —</span><span id="platform-oos">Prospective Validation —</span></div><a class="platform-demo-link" href="markets.html">Explore Markets</a></div>`;
    if(header)header.insertAdjacentElement('afterend',status);
  }

  if(current==='strength.html'){
    const workspace=document.querySelector('.workspace');
    const fitWorkspace=()=>{
      if(!workspace)return;
      if(embeddedDemo){workspace.style.height='100vh';return;}
      workspace.style.height=Math.max(320,window.innerHeight-(header?header.offsetHeight:66)-(status?status.offsetHeight:0))+'px';
    };
    fitWorkspace();window.addEventListener('resize',fitWorkspace);
  }

  Promise.allSettled([
    fetch('./data/currency-strength.json',{cache:'no-store'}).then(r=>r.ok?r.json():null),
    fetch('./data/decision-alert-stability.json',{cache:'no-store'}).then(r=>r.ok?r.json():null),
    fetch('./data/fresh-oos-tracker.json',{cache:'no-store'}).then(r=>r.ok?r.json():null)
  ]).then(results=>{
    const currency=results[0].status==='fulfilled'&&results[0].value?(results[0].value.data||results[0].value):null;
    const stable=results[1].status==='fulfilled'?results[1].value:null;
    const oos=results[2].status==='fulfilled'?results[2].value:null;
    if(!embeddedDemo){
      const market=document.getElementById('platform-market');const readiness=document.getElementById('platform-readiness');const risk=document.getElementById('platform-risk');const gate=document.getElementById('platform-gate');const oosEl=document.getElementById('platform-oos');
      if(currency){
        const daily=(currency.strength_timeframes&&currency.strength_timeframes.daily)||currency;const pa=daily.pair_analysis||currency.pair_analysis||{};const action=(currency.actionability_score&&currency.actionability_score.current)||{};const layers=(currency.intelligence_layer&&currency.intelligence_layer.layers)||{};const finalR=layers.final_reasoner||{};const riskLayer=layers.risk||{};
        if(market){market.textContent='Forex Live '+(finalR.pair||pa.pair||'—')+' '+(finalR.canonical_bias||pa.bias||'—');market.title='ECB session '+(currency.session_date||'—')}
        if(readiness)readiness.innerHTML='Decision Readiness <b>'+((action.score!=null?action.score:'—')+'/100 · '+String(action.state||'—').replaceAll('_',' '))+'</b>';
        if(risk)risk.innerHTML='Decision Risk <b>'+((riskLayer.score!=null?riskLayer.score:'—')+'/100 · '+String(riskLayer.state||'—').replaceAll('_',' '))+'</b>';
      }
      if(stable&&gate){const g=(stable.summary&&stable.summary.stable_gate)||stable.raw_alert_status||'—';gate.innerHTML='Decision Gate <b>'+String(g).replaceAll('_',' ')+'</b>'}
      if(oos&&oosEl){const entries=Array.isArray(oos.entries)?oos.entries:[];const settled=entries.filter(e=>{const x=e&&e.outcome||{};return x.settled===true||String(x.status||'').startsWith('SETTLED')||x.hit===true||x.hit===false}).length;const target=oos.policy&&oos.policy.primary_settled_target||60;oosEl.innerHTML='Prospective Validation <b>'+settled+'/'+target+' settled</b>'}
    }
  });

  if(current==='stocks.html'){
    const plugin=document.createElement('script');
    plugin.src='stocks-market-layer.js?v=20260819-stage10b';
    document.body.appendChild(plugin);
  }

  if(current==='markets.html'){
    const pills=[...document.querySelectorAll('.heroMeta .pill')];
    const stocksPill=pills.find(x=>x.textContent.trim().startsWith('Stocks'));
    if(stocksPill)stocksPill.textContent='Stocks · LIVE · MODEL FROZEN';
    const cryptoPill=pills.find(x=>x.textContent.trim().startsWith('Crypto'));
    if(cryptoPill)cryptoPill.textContent='Crypto · Stage 11A ready';
    const assets=[...document.querySelectorAll('.asset')];
    const stockCard=assets.find(x=>x.querySelector('.assetName')&&x.querySelector('.assetName').textContent.trim()==='Stocks');
    if(stockCard){
      const role=stockCard.querySelector('.assetRole');if(role)role.textContent='SEC evidence + daily market data + frozen decision intelligence';
      const badge=stockCard.querySelector('.badge');if(badge){badge.textContent='STAGE 10 COMPLETE';badge.classList.remove('statusBuild');badge.classList.add('statusLive')}
      const metric=stockCard.querySelector('.metric');if(metric)metric.textContent='FROZEN · ACTIVE';
      const sub=stockCard.querySelector('.sub');if(sub)sub.textContent='Decision Watch, immutable Timeline, and Fresh OOS monitoring';
      const sources=stockCard.querySelectorAll('.source');
      if(sources[1]){const b=sources[1].querySelector('b');const s=sources[1].querySelector('span');if(b)b.textContent='Alpha Vantage + 10C/10D';if(s)s.textContent='Daily OHLCV · frozen reasoning · prospective validation'}
      const action=stockCard.querySelector('.action');if(action&&!stockCard.querySelector('a[href="stocks-observability.html"]')){action.textContent='Open Stocks Intelligence →';action.insertAdjacentHTML('afterend','<br><a class="action" href="stocks-observability.html">Open Stocks Observability →</a>')}
    }
    const cryptoCard=assets.find(x=>x.querySelector('.assetName')&&x.querySelector('.assetName').textContent.trim()==='Crypto');
    if(cryptoCard){
      const role=cryptoCard.querySelector('.assetRole');if(role)role.textContent='24/7 market structure first; official protocol/regulatory evidence follows in 11B';
      const badge=cryptoCard.querySelector('.badge');if(badge){badge.textContent='STAGE 11A READY';badge.classList.add('statusBuild')}
      const metric=cryptoCard.querySelector('.metric');if(metric)metric.textContent='Keyed adapter';
      const sub=cryptoCard.querySelector('.sub');if(sub)sub.textContent='Completed UTC daily context · backtest and freeze not yet active';
      const sources=cryptoCard.querySelectorAll('.source');
      if(sources[0]){const b=sources[0].querySelector('b');const s=sources[0].querySelector('span');if(b)b.textContent='CoinGecko Demo/Pro API';if(s)s.textContent='Keyed aggregated market data · Stage 11A'}
      if(sources[1]){const b=sources[1].querySelector('b');const s=sources[1].querySelector('span');if(b)b.textContent='Official project + regulators';if(s)s.textContent='Protocol/regulatory authority · Stage 11B'}
      if(!cryptoCard.querySelector('.action'))cryptoCard.insertAdjacentHTML('beforeend','<a class="action" href="crypto.html">Open Crypto Intelligence →</a>');
    }
  }

  if(current==='index.html'&&!embeddedDemo){
    const eyebrow=document.querySelector('.hero .eyebrow');if(eyebrow)eyebrow.textContent='Explainable AI Intelligence for Global Markets';
    const h1=document.querySelector('.hero h1');if(h1)h1.textContent='Know what is moving markets — and what could invalidate the view.';
    const heroP=document.querySelector('.hero p');if(heroP)heroP.textContent='One explainable decision-intelligence platform expanding across Forex, Stocks, Crypto, Gold, and Oil. Forex and Stocks are governed verticals; Crypto Stage 11A is now building its keyed 24/7 market-data truth layer before protocol evidence, decision intelligence, backtest, QA, or freeze.';
    const heroMeta=document.querySelector('.heroMeta');
    if(heroMeta&&!document.querySelector('.platform-home-cta'))heroMeta.insertAdjacentHTML('afterend',`<div class="platform-home-cta"><a class="primary" href="markets.html">Explore Multi-Asset Markets</a><a class="secondary" href="crypto.html">Open Crypto Stage 11A</a><a class="secondary" href="demo.html">Launch FX Competition Demo</a></div><div class="platform-pitch-thesis"><b>The signal is not the product.</b> Across markets, the product is the decision discipline around the signal: source it, explain it, challenge it, constrain it, trace it, backtest it diagnostically, and validate it prospectively.</div>`);
    const footer=document.querySelector('footer');
    if(footer&&!document.querySelector('.platform-flow')){
      const flow=document.createElement('section');flow.className='platform-flow';flow.innerHTML=`<div class="platform-flow-wrap"><div class="platform-flow-head"><div><h2>One architecture. Multiple markets. Explainable decisions.</h2><p>Forex and Stocks are active governed verticals; Crypto Stage 11A is next, then Oil and Gold before Unified News Intelligence.</p></div><a class="platform-demo-link" href="markets.html">Explore market universe</a></div><div class="platform-flow-grid">
      <div class="platform-flow-card"><div class="n">01 · UNIVERSE</div><h3>Multi-Asset Markets</h3><p>Forex, Stocks, Crypto, Gold and Oil share one transparent source and evidence architecture.</p><a href="markets.html">Open Markets →</a></div>
      <div class="platform-flow-card"><div class="n">02 · CRYPTO</div><h3>24/7 Market Truth Layer</h3><p>Crypto starts with keyed aggregated price, market-cap and volume context. Official protocol and regulatory evidence remains a separate next stage.</p><a href="crypto.html">Open Crypto →</a></div>
      <div class="platform-flow-card"><div class="n">03 · EXPLAIN</div><h3>Evidence Intelligence</h3><p>Official data, licensed wires and reputable financial press are separated by trust tier and relevance.</p><a href="intelligence.html">Open Intelligence →</a></div>
      <div class="platform-flow-card"><div class="n">04 · CHALLENGE</div><h3>Risk + Counter-Thesis</h3><p>The AI must show why a market view could fail before it is promoted to higher decision priority.</p><a href="intelligence.html">Review reasoning →</a></div>
      <div class="platform-flow-card"><div class="n">05 · BACKTEST + QA</div><h3>Pre-Freeze Governance</h3><p>Crypto, Oil and Gold must pass historical diagnostic backtesting and model QA before any new model freeze is allowed.</p><a href="crypto.html">Review Crypto roadmap →</a></div>
      <div class="platform-flow-card"><div class="n">06 · VALIDATE</div><h3>Prospective Validation</h3><p>After a model passes QA and freezes, Fresh OOS—not backtest alone—becomes the primary validation evidence.</p><a href="stocks-validation.html">See validation standard →</a></div>
      </div></div>`;footer.parentNode.insertBefore(flow,footer);
    }
  }
})();