(function(){
  var liveSection=document.getElementById('live-strength');
  var container=liveSection&&liveSection.querySelector('.container');
  var liveShell=container&&container.querySelector('.live-shell');
  if(!container||!liveShell) return;

  var style=document.createElement('style');
  style.textContent=
    '.iw-shell{margin-top:22px;display:grid;gap:12px}' +
    '.iw-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap;padding:4px 2px 2px}' +
    '.iw-kicker{font-size:.61rem;text-transform:uppercase;letter-spacing:.11em;color:var(--accent);font-weight:800}' +
    '.iw-title{margin-top:4px;font-size:1.16rem;font-weight:850;line-height:1.25;color:var(--text)}' +
    '.iw-sub{margin-top:5px;max-width:760px;font-size:.68rem;line-height:1.5;color:var(--muted)}' +
    '.iw-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);border-radius:999px;padding:6px 10px;background:rgba(7,11,20,.28);font-size:.56rem;font-weight:800;color:var(--muted);white-space:nowrap}' +
    '.iw-chip:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 3px var(--green-dim)}' +
    '.iw-zone{min-width:0}' +
    '.iw-observe{display:grid;grid-template-columns:1fr;gap:12px;align-items:start}' +
    '.iw-shell #final-intelligence-dashboard,.iw-shell #decision-alert-watch,.iw-shell #intelligence-timeline,.iw-shell #decision-change-analytics,.iw-shell #intraday-context-drift{width:100%;min-width:0;margin-top:0}' +
    '@media(min-width:980px){.iw-shell .fid-kpis{grid-template-columns:repeat(4,minmax(0,1fr))}.iw-shell .fid-context{grid-template-columns:repeat(3,minmax(0,1fr))}}' +
    '.iw-divider{height:1px;background:linear-gradient(90deg,transparent,var(--border-2),transparent);margin:2px 0}' +
    '.iw-zone-label{display:flex;align-items:center;gap:8px;margin:2px 2px -2px;font-size:.58rem;text-transform:uppercase;letter-spacing:.08em;font-weight:800;color:var(--muted-2)}' +
    '.iw-zone-label:after{content:"";height:1px;flex:1;background:var(--border)}' +
    '@media(max-width:899px){.iw-shell{margin-top:16px}.iw-head{padding:0}.iw-title{font-size:1.03rem}.iw-sub{font-size:.64rem}}';
  document.head.appendChild(style);

  var shell=document.getElementById('intelligence-workspace');
  if(!shell){
    shell=document.createElement('div');
    shell.id='intelligence-workspace';
    shell.className='iw-shell';
    shell.innerHTML=
      '<div class="iw-head">' +
        '<div><div class="iw-kicker">Decision Intelligence Workspace</div><div class="iw-title">Keputusan utama dan monitoring dalam satu area</div><div class="iw-sub">Final Intelligence Dashboard menjadi tampilan utama. Alert, timeline, drift, dan analytics tetap tersedia sebagai observability tanpa mengulang seluruh Intelligence Layer di layar.</div></div>' +
        '<span class="iw-chip">RINGKAS & TERORGANISASI</span>' +
      '</div>' +
      '<div class="iw-zone-label">Executive View</div><div class="iw-zone" id="iw-executive"></div>' +
      '<div class="iw-zone-label">Decision Watch</div><div class="iw-zone" id="iw-watch"></div>' +
      '<div class="iw-divider"></div>' +
      '<div class="iw-zone-label">History & Observability</div><div class="iw-observe" id="iw-observe"></div>';
    liveShell.insertAdjacentElement('afterend',shell);
  }

  function move(id,targetId){
    var el=document.getElementById(id);
    var target=document.getElementById(targetId);
    if(el&&target&&el.parentElement!==target) target.appendChild(el);
  }

  function organize(){
    var redundant=document.getElementById('intelligence-layer-panel');
    if(redundant) redundant.remove();
    move('final-intelligence-dashboard','iw-executive');
    move('decision-alert-watch','iw-watch');
    move('intelligence-timeline','iw-observe');
    move('intraday-context-drift','iw-observe');
    move('decision-change-analytics','iw-observe');
  }

  organize();

  var observer=new MutationObserver(function(){organize();});
  observer.observe(liveSection,{childList:true,subtree:true});
  window.setTimeout(function(){organize();observer.disconnect();},2500);
})();
