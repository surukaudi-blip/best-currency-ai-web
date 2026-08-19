(function(){
  if(window.__BC_STOCKS_MARKET_LAYER__) return;
  window.__BC_STOCKS_MARKET_LAYER__=true;
  if((location.pathname.split('/').pop()||'')!=='stocks.html') return;

  const css=`
    .market10b-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:12px}.market10b-head h2{margin:0;font-size:1.14rem}.market10b-head p{margin:5px 0 0;color:#97a5ba;font-size:.73rem}.market10b-badge{display:inline-flex;align-items:center;border:1px solid rgba(240,163,47,.22);border-radius:999px;padding:6px 9px;color:#f0a32f;background:rgba(240,163,47,.10);font:800 .57rem Inter,system-ui}.market10b-badge.ready{color:#3bd69a;background:rgba(59,214,154,.10);border-color:rgba(59,214,154,.2)}
    .market10b-tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}.market10b-tab{appearance:none;border:1px solid rgba(148,163,184,.15);background:#0d1420;color:#97a5ba;border-radius:999px;padding:7px 10px;font:800 .62rem Inter;cursor:pointer}.market10b-tab.active{background:#2fd3ee;color:#04121a;border-color:transparent}
    .market10b-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.market10b-mini{border:1px solid rgba(148,163,184,.15);border-radius:11px;padding:11px;background:rgba(17,26,41,.55)}.market10b-mini .l{font-size:.55rem;color:#97a5ba;text-transform:uppercase;letter-spacing:.07em}.market10b-mini .v{font-size:1rem;font-weight:900;margin-top:4px;color:#e7ecf4}.market10b-mini .n{font-size:.57rem;color:#68788f;margin-top:4px}.market10b-note{margin-top:10px;padding:11px;border:1px solid rgba(47,211,238,.22);border-radius:11px;color:#97a5ba;font-size:.64rem;line-height:1.55}.market10b-note b{color:#2fd3ee}.market10b-empty{padding:22px;border:1px dashed rgba(148,163,184,.28);border-radius:13px;color:#97a5ba;font-size:.72rem;text-align:center}
    @media(min-width:760px){.market10b-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
  `;
  const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);

  const sections=document.querySelectorAll('main > section');
  if(sections.length<3) return;
  const section=document.createElement('section');
  section.id='stocks-market-layer';
  section.innerHTML=`<div class="wrap"><div class="market10b-head"><div><h2>Daily Market Data · Stage 10B</h2><p>Alpha Vantage daily raw OHLCV, kept separate from SEC evidence and from Stage 10C decision reasoning.</p></div><span class="market10b-badge" id="market10bBadge">AWAITING API KEY</span></div><div class="market10b-tabs" id="market10bTabs"></div><div class="card"><div id="market10bPane" class="market10b-empty">Configure the GitHub Actions secret <b>ALPHA_VANTAGE_API_KEY</b>, then run <b>Refresh Stocks Market Data</b>. No market view or BUY/SELL is generated in Stage 10B.</div></div></div>`;
  sections[2].insertAdjacentElement('afterend',section);

  const badge=document.getElementById('market10bBadge');
  const tabs=document.getElementById('market10bTabs');
  const pane=document.getElementById('market10bPane');
  const marketKpi=document.getElementById('marketStatus');
  let artifact=null;let selected=null;

  const fmt=(v,d=2)=>v==null?'—':Number(v).toFixed(d);
  const pct=v=>v==null?'—':(v>0?'+':'')+Number(v).toFixed(2)+'%';
  const price=v=>v==null?'—':'$'+Number(v).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
  const integer=v=>v==null?'—':Math.round(Number(v)).toLocaleString();

  function enforceMarketKpi(text){
    if(!marketKpi)return;
    marketKpi.textContent=text;
    marketKpi.dataset.stage10b='1';
    const obs=new MutationObserver(()=>{if(marketKpi.dataset.stage10b==='1'&&marketKpi.textContent!==text)marketKpi.textContent=text});
    obs.observe(marketKpi,{childList:true,characterData:true,subtree:true});
    setTimeout(()=>obs.disconnect(),8000);
  }

  function patchRoadmap(ready){
    document.querySelectorAll('.step').forEach(step=>{
      const key=step.querySelector('.stepN')&&step.querySelector('.stepN').textContent.trim();
      const status=step.querySelector('.status');
      if(!status)return;
      if(key==='10A')status.textContent='COMPLETE';
      if(key==='10B')status.textContent=ready?'COMPLETE':'READY TO ACTIVATE';
    });
  }

  function renderTabs(){
    const symbols=artifact&&artifact.symbols||[];
    tabs.innerHTML=symbols.map(s=>`<button class="market10b-tab ${s.ticker===selected?'active':''}" data-t="${s.ticker}">${s.ticker}</button>`).join('');
  }

  function renderSymbol(){
    const s=(artifact.symbols||[]).find(x=>x.ticker===selected);
    if(!s){pane.className='market10b-empty';pane.innerHTML='No daily market data is available for this symbol.';return;}
    const b=s.latest_bar||{};const m=s.derived_market_context||{};const q=s.data_quality||{};
    pane.className='';
    pane.innerHTML=`<div class="companyHead"><div class="companyTitle"><h2>${s.ticker} · ${s.name||''}</h2><p>${s.exchange||'—'} · Latest completed market session ${s.freshness&&s.freshness.latest_market_session||'—'} · Alpha Vantage TIME_SERIES_DAILY</p></div><span class="market10b-badge ready">DAILY OHLCV READY</span></div><div class="market10b-grid" style="margin-top:13px"><div class="market10b-mini"><div class="l">Close</div><div class="v">${price(b.close)}</div><div class="n">Open ${price(b.open)} · High ${price(b.high)} · Low ${price(b.low)}</div></div><div class="market10b-mini"><div class="l">1D / 5D / 20D</div><div class="v">${pct(m.return_1d_percent)}</div><div class="n">5D ${pct(m.return_5d_percent)} · 20D ${pct(m.return_20d_percent)}</div></div><div class="market10b-mini"><div class="l">SMA 20 / 50</div><div class="v">${price(m.sma_20)}</div><div class="n">SMA50 ${price(m.sma_50)} · vs 20D ${pct(m.close_vs_sma20_percent)}</div></div><div class="market10b-mini"><div class="l">20D Volatility</div><div class="v">${pct(m.annualized_volatility_20d_percent)}</div><div class="n">20D range ${pct(m.high_low_range_20d_percent)}</div></div><div class="market10b-mini"><div class="l">Latest Volume</div><div class="v">${integer(b.volume)}</div><div class="n">20D avg ${integer(m.average_volume_20d)}</div></div><div class="market10b-mini"><div class="l">Volume / 20D Avg</div><div class="v">${m.latest_volume_vs_20d_average_ratio==null?'—':fmt(m.latest_volume_vs_20d_average_ratio,2)+'×'}</div><div class="n">Participation context only</div></div><div class="market10b-mini"><div class="l">Bars Received</div><div class="v">${q.bars_received==null?'—':q.bars_received}</div><div class="n">50D context ${q.minimum_for_50d_context_met?'available':'not available'}</div></div><div class="market10b-mini"><div class="l">Price Mode</div><div class="v" style="font-size:.78rem">RAW AS-TRADED</div><div class="n">Not realtime · not adjusted</div></div></div><div class="market10b-note"><b>10B guardrail:</b> these are market-data observations and descriptive derived metrics, not a trading recommendation. Raw daily prices are not split/dividend adjusted in v1, the full provider series is not republished, and Stage 10C remains responsible for Market View, risk, counter-thesis, and final reasoning.</div>`;
    renderTabs();
  }

  tabs.addEventListener('click',e=>{const b=e.target.closest('.market10b-tab');if(!b)return;selected=b.dataset.t;renderSymbol();});

  fetch('./data/stocks-market-data.json',{cache:'no-store'})
    .then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()})
    .then(data=>{
      artifact=data;
      const symbols=Array.isArray(data.symbols)?data.symbols:[];
      const ready=symbols.length>0&&(data.status==='DAILY_MARKET_DATA_READY'||data.status==='PARTIAL');
      patchRoadmap(ready);
      if(!ready){
        badge.textContent=String(data.status||'AWAITING API KEY').replaceAll('_',' ');
        enforceMarketKpi('Awaiting API key');
        return;
      }
      badge.textContent=data.status==='DAILY_MARKET_DATA_READY'?'DAILY DATA READY':'PARTIAL DATA';badge.classList.add('ready');
      enforceMarketKpi(data.status==='DAILY_MARKET_DATA_READY'?'Daily OHLCV ready':'Partial daily data');
      selected=symbols[0].ticker;renderTabs();renderSymbol();
    })
    .catch(()=>{badge.textContent='DATA UNAVAILABLE';enforceMarketKpi('Data unavailable');patchRoadmap(false)});

  const decisionPlugin=document.createElement('script');
  decisionPlugin.src='stocks-decision-layer.js?v=20260819-stage10c';
  document.body.appendChild(decisionPlugin);
})();
