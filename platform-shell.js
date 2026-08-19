(function(){
  if(window.__BC_PLATFORM_SHELL__) return;
  window.__BC_PLATFORM_SHELL__=true;

  const navItems=[
    ['Overview','index.html'],
    ['Strength','strength.html'],
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
    .platform-home-cta{display:flex;gap:9px;flex-wrap:wrap;margin-top:20px}.platform-home-cta a{display:inline-flex;align-items:center;justify-content:center;border-radius:10px;padding:11px 16px;font:800 12px/1 Inter,system-ui;border:1px solid rgba(148,163,184,.28)}.platform-home-cta .primary{background:#2fd3ee;color:#04121a;border-color:transparent}.platform-home-cta .secondary{color:#e7ecf4}
    .platform-flow{padding:28px 0}.platform-flow-wrap{max-width:1180px;margin:auto;padding:0 20px}.platform-flow-head{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:14px}.platform-flow-head h2{margin:0;font:800 19px/1.2 Inter,system-ui;color:#e7ecf4}.platform-flow-head p{margin:5px 0 0;color:#97a5ba;font:500 12px/1.5 Inter,system-ui}.platform-flow-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.platform-flow-card{border:1px solid rgba(148,163,184,.15);border-radius:15px;padding:17px;background:linear-gradient(180deg,#0d1420,rgba(13,20,32,.72));color:#e7ecf4}.platform-flow-card .n{font:800 10px/1 Inter,system-ui;color:#2fd3ee;letter-spacing:.1em}.platform-flow-card h3{margin:9px 0 5px;font:800 14px/1.2 Inter,system-ui}.platform-flow-card p{margin:0;color:#97a5ba;font:500 11px/1.55 Inter,system-ui}.platform-flow-card a{display:inline-block;margin-top:11px;color:#2fd3ee;font:750 11px/1 Inter,system-ui}
    @media(max-width:930px){.platform-menu-toggle{display:flex}.platform-status-inner{padding:7px 14px}.platform-status-items{gap:8px}.platform-status-items span:nth-child(n+3){display:none}.platform-flow-grid{grid-template-columns:1fr}.platform-demo-link{font-size:10px}}
  `;
  const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);

  const nav=document.querySelector('header .nav');
  if(nav){
    const btn=document.createElement('button');btn.className='platform-menu-toggle';btn.type='button';btn.setAttribute('aria-label','Open navigation');btn.setAttribute('aria-expanded','false');btn.textContent='☰';nav.appendChild(btn);
    const drawer=document.createElement('nav');drawer.className='platform-mobile-drawer';drawer.setAttribute('aria-label','Mobile navigation');
    drawer.innerHTML=navItems.map(([label,href])=>`<a href="${href}" class="${current===href?'active':''}">${label}</a>`).join('')+`<a class="demo" href="demo.html">Demo Mode · 90 sec</a>`;
    document.body.appendChild(drawer);
    btn.addEventListener('click',()=>{const open=drawer.classList.toggle('open');btn.setAttribute('aria-expanded',String(open));btn.textContent=open?'×':'☰'});
    drawer.addEventListener('click',()=>{drawer.classList.remove('open');btn.setAttribute('aria-expanded','false');btn.textContent='☰'});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'){drawer.classList.remove('open');btn.setAttribute('aria-expanded','false');btn.textContent='☰'}});
  }

  const status=document.createElement('div');status.className='platform-statusbar';status.innerHTML=`<div class="platform-status-inner"><div class="platform-status-items"><span><i class="platform-dot"></i><b id="platform-session">ECB session —</b></span><span id="platform-gate">Decision gate —</span><span id="platform-oos">Fresh OOS —</span><span>Trade Execution <b>OFF</b></span></div><a class="platform-demo-link" href="demo.html">Launch Demo Mode</a></div>`;
  const header=document.querySelector('header');if(header)header.insertAdjacentElement('afterend',status);

  Promise.allSettled([
    fetch('./data/currency-strength.json',{cache:'no-store'}).then(r=>r.ok?r.json():null),
    fetch('./data/decision-alert-stability.json',{cache:'no-store'}).then(r=>r.ok?r.json():null),
    fetch('./data/fresh-oos-tracker.json',{cache:'no-store'}).then(r=>r.ok?r.json():null)
  ]).then(results=>{
    const currency=results[0].status==='fulfilled'&&results[0].value?(results[0].value.data||results[0].value):null;
    const stable=results[1].status==='fulfilled'?results[1].value:null;
    const oos=results[2].status==='fulfilled'?results[2].value:null;
    const session=document.getElementById('platform-session');const gate=document.getElementById('platform-gate');const oosEl=document.getElementById('platform-oos');
    if(currency&&session){session.textContent='ECB session '+(currency.session_date||'—');session.title=currency.generated_at?'Generated '+new Date(currency.generated_at).toLocaleString():''}
    if(stable&&gate){const g=(stable.summary&&stable.summary.stable_gate)||stable.raw_alert_status||'—';gate.innerHTML='Decision gate <b>'+String(g).replaceAll('_',' ')+'</b>'}
    if(oos&&oosEl){const entries=Array.isArray(oos.entries)?oos.entries:[];const settled=entries.filter(e=>{const x=e&&e.outcome||{};return x.settled===true||String(x.status||'').startsWith('SETTLED')||x.hit===true||x.hit===false}).length;const target=oos.policy&&oos.policy.primary_settled_target||60;oosEl.innerHTML='Fresh OOS <b>'+settled+'/'+target+' settled</b>'}
  });

  if(current==='index.html'){
    const heroMeta=document.querySelector('.heroMeta');
    if(heroMeta&&!document.querySelector('.platform-home-cta'))heroMeta.insertAdjacentHTML('afterend',`<div class="platform-home-cta"><a class="primary" href="demo.html">Launch 90-Second Demo</a><a class="secondary" href="intelligence.html">Open FX Intelligence</a></div>`);
    const footer=document.querySelector('footer');
    if(footer&&!document.querySelector('.platform-flow')){
      const flow=document.createElement('section');flow.className='platform-flow';flow.innerHTML=`<div class="platform-flow-wrap"><div class="platform-flow-head"><div><h2>One signal. Six layers of explainable intelligence.</h2><p>A pitch-ready product flow from market movement to prospective validation.</p></div><a class="platform-demo-link" href="demo.html">Run guided demo</a></div><div class="platform-flow-grid">
      <div class="platform-flow-card"><div class="n">01 · DETECT</div><h3>Currency Strength</h3><p>Identify the strongest and weakest currencies and form the canonical ECB pair bias.</p><a href="strength.html">Open Strength →</a></div>
      <div class="platform-flow-card"><div class="n">02 · EXPLAIN</div><h3>FX Intelligence</h3><p>Combine macro, yield, cross-market, news, risk and counter-thesis around the canonical signal.</p><a href="intelligence.html">Open Intelligence →</a></div>
      <div class="platform-flow-card"><div class="n">03 · WATCH</div><h3>Decision Watch</h3><p>Escalate only material, persistent changes while filtering noisy alert oscillation.</p><a href="decision-watch.html">Open Watch →</a></div>
      <div class="platform-flow-card"><div class="n">04 · TRACE</div><h3>Timeline</h3><p>See what changed across sessions and which layers moved with the final decision.</p><a href="timeline.html">Open Timeline →</a></div>
      <div class="platform-flow-card"><div class="n">05 · VALIDATE</div><h3>Fresh OOS Validation</h3><p>Track immutable prospective predictions and suppress premature performance claims.</p><a href="validation.html">Open Validation →</a></div>
      <div class="platform-flow-card"><div class="n">06 · GOVERN</div><h3>Model Integrity</h3><p>Keep thresholds and weights frozen, execution off, and evidence separated from prediction claims.</p><a href="validation.html">Review Integrity →</a></div>
      </div></div>`;footer.parentNode.insertBefore(flow,footer);
    }
  }
})();
