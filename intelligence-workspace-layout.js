(function(){
  var liveSection=document.getElementById('live-strength');
  var container=liveSection&&liveSection.querySelector('.container');
  var liveShell=container&&container.querySelector('.live-shell');
  if(!container||!liveShell) return;

  // Decision Readiness methodology is presentation-only UI heuristic v0.1.
  // It summarizes existing frozen model outputs and does not alter model logic.
  var DECISION_READINESS_METHOD='ui_heuristic_v0.1';

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
    '.iw-shell #final-intelligence-dashboard,.iw-shell #fresh-oos-monitoring,.iw-shell #decision-alert-watch,.iw-shell #intelligence-timeline,.iw-shell #decision-change-analytics,.iw-shell #intraday-context-drift{width:100%;min-width:0;margin-top:0}' +
    '@media(min-width:980px){.iw-shell .fid-kpis{grid-template-columns:repeat(4,minmax(0,1fr))}.iw-shell .fid-context{grid-template-columns:repeat(3,minmax(0,1fr))}}' +
    '.iw-divider{height:1px;background:linear-gradient(90deg,transparent,var(--border-2),transparent);margin:2px 0}' +
    '.iw-zone-label{display:flex;align-items:center;gap:8px;margin:2px 2px -2px;font-size:.58rem;text-transform:uppercase;letter-spacing:.08em;font-weight:800;color:var(--muted-2)}' +
    '.iw-zone-label:after{content:"";height:1px;flex:1;background:var(--border)}' +
    '.ug-panel{border:1px solid rgba(47,211,238,.2);border-radius:16px;background:linear-gradient(180deg,rgba(47,211,238,.035),rgba(7,11,20,.18));overflow:hidden}' +
    '.ug-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;flex-wrap:wrap;padding:18px 18px 15px;border-bottom:1px solid var(--border)}' +
    '.ug-eyebrow{font-size:.57rem;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);font-weight:850}' +
    '.ug-title{margin-top:4px;font-size:1.05rem;font-weight:850;line-height:1.25;color:var(--text)}' +
    '.ug-lead{margin-top:5px;max-width:760px;font-size:.64rem;line-height:1.55;color:var(--muted)}' +
    '.ug-badge{display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:999px;padding:6px 9px;font-size:.53rem;font-weight:850;letter-spacing:.05em;color:var(--muted);background:rgba(7,11,20,.3);white-space:nowrap}' +
    '.ug-flow{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:14px 18px 4px}' +
    '@media(min-width:760px){.ug-flow{grid-template-columns:repeat(6,minmax(0,1fr))}}' +
    '.ug-step{position:relative;border:1px solid var(--border);border-radius:10px;padding:9px;background:rgba(7,11,20,.2);min-width:0}' +
    '.ug-step-n{display:flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:6px;background:var(--accent-dim);color:var(--accent);font-size:.56rem;font-weight:900}' +
    '.ug-step-t{margin-top:6px;font-size:.58rem;font-weight:800;color:var(--text);line-height:1.25}' +
    '.ug-step-s{margin-top:3px;font-size:.52rem;color:var(--muted-2);line-height:1.35}' +
    '.ug-block{padding:14px 18px}' +
    '.ug-block+.ug-block{border-top:1px solid var(--border)}' +
    '.ug-block-title{font-size:.56rem;text-transform:uppercase;letter-spacing:.08em;font-weight:850;color:var(--muted-2);margin-bottom:9px}' +
    '.ug-state-grid{display:grid;grid-template-columns:1fr;gap:8px}' +
    '@media(min-width:760px){.ug-state-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}' +
    '.ug-state{border:1px solid var(--border);border-radius:11px;padding:11px;background:rgba(7,11,20,.18)}' +
    '.ug-state-top{display:flex;align-items:center;justify-content:space-between;gap:8px}' +
    '.ug-state-name{font-size:.68rem;font-weight:900;letter-spacing:.02em}' +
    '.ug-dot{width:8px;height:8px;border-radius:50%}' +
    '.ug-green{color:var(--green)}.ug-amber{color:var(--amber)}.ug-red{color:var(--red)}' +
    '.ug-dot.ug-green{background:var(--green)}.ug-dot.ug-amber{background:var(--amber)}.ug-dot.ug-red{background:var(--red)}' +
    '.ug-state-use{margin-top:5px;font-size:.61rem;font-weight:750;color:var(--text)}' +
    '.ug-state-note{margin-top:3px;font-size:.55rem;line-height:1.4;color:var(--muted)}' +
    '.ug-metrics{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}' +
    '.ug-metric{border-radius:8px;background:rgba(148,163,184,.07);padding:5px 7px;font-size:.52rem;color:var(--muted);white-space:nowrap}' +
    '.ug-metric b{color:var(--text);font-weight:850}' +
    '.ug-risk-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}' +
    '.ug-risk{border:1px solid var(--border);border-radius:10px;padding:9px;background:rgba(7,11,20,.16)}' +
    '.ug-risk-name{font-size:.58rem;font-weight:900}' +
    '.ug-risk-m{margin-top:5px;font-size:.52rem;line-height:1.4;color:var(--muted)}' +
    '.ug-use-grid{display:grid;grid-template-columns:1fr;gap:8px}' +
    '@media(min-width:760px){.ug-use-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}' +
    '.ug-use{border-radius:11px;padding:11px;border:1px solid var(--border);background:rgba(7,11,20,.16)}' +
    '.ug-use.good{border-color:rgba(59,214,154,.24);background:rgba(59,214,154,.035)}' +
    '.ug-use.wait{border-color:rgba(240,163,47,.24);background:rgba(240,163,47,.035)}' +
    '.ug-use.stop{border-color:rgba(242,109,109,.24);background:rgba(242,109,109,.035)}' +
    '.ug-use-h{font-size:.62rem;font-weight:900;color:var(--text)}' +
    '.ug-use-p{margin-top:5px;font-size:.56rem;line-height:1.48;color:var(--muted)}' +
    '.ug-guard{margin:0 18px 17px;padding:10px 11px;border-radius:10px;border:1px solid rgba(240,163,47,.2);background:rgba(240,163,47,.035);font-size:.55rem;line-height:1.5;color:var(--muted)}' +
    '.ug-guard b{color:var(--amber);font-weight:850}' +
    '.dr-panel{margin-top:12px;border:1px solid var(--border-2);border-radius:16px;background:linear-gradient(180deg,rgba(148,163,184,.045),rgba(7,11,20,.2));overflow:hidden;--dr-tone:var(--amber);--dr-pct:0%}' +
    '.dr-panel.high{--dr-tone:var(--green)}.dr-panel.partial{--dr-tone:var(--amber)}.dr-panel.low{--dr-tone:var(--red)}' +
    '.dr-head{display:grid;grid-template-columns:1fr;gap:14px;padding:17px 18px;border-bottom:1px solid var(--border)}' +
    '@media(min-width:760px){.dr-head{grid-template-columns:1fr auto;align-items:center}}' +
    '.dr-eyebrow{font-size:.57rem;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);font-weight:850}' +
    '.dr-title{margin-top:4px;font-size:1.04rem;font-weight:900;color:var(--text)}' +
    '.dr-sub{margin-top:5px;max-width:720px;font-size:.62rem;line-height:1.5;color:var(--muted)}' +
    '.dr-summary{display:flex;align-items:center;gap:12px;justify-content:flex-start}' +
    '.dr-ring{width:82px;height:82px;border-radius:50%;background:conic-gradient(var(--dr-tone) var(--dr-pct),rgba(148,163,184,.12) 0);display:grid;place-items:center;position:relative;flex:0 0 auto}' +
    '.dr-ring:after{content:"";position:absolute;inset:7px;border-radius:50%;background:var(--bg-2);border:1px solid var(--border)}' +
    '.dr-pct{position:relative;z-index:1;font-size:1.18rem;font-weight:900;color:var(--text);letter-spacing:-.03em}' +
    '.dr-summary-meta{min-width:128px}.dr-met{font-size:.72rem;font-weight:850;color:var(--text)}' +
    '.dr-primary{display:inline-flex;margin-top:6px;border-radius:999px;padding:5px 8px;font-size:.54rem;font-weight:900;letter-spacing:.04em}' +
    '.dr-primary.pass{background:var(--green-dim);color:var(--green)}.dr-primary.fail{background:var(--red-dim);color:var(--red)}' +
    '.dr-body{padding:14px 18px 16px}' +
    '.dr-progress{height:7px;border-radius:999px;background:rgba(148,163,184,.1);overflow:hidden;border:1px solid var(--border)}' +
    '.dr-progress>span{display:block;height:100%;width:var(--dr-pct);background:var(--dr-tone);border-radius:999px;transition:width .25s ease}' +
    '.dr-scale{display:flex;justify-content:space-between;gap:8px;margin-top:5px;font-size:.5rem;color:var(--muted-2)}' +
    '.dr-blockers{display:flex;align-items:flex-start;gap:8px;margin-top:11px;padding:9px 10px;border-radius:10px;border:1px solid var(--border);background:rgba(7,11,20,.18);font-size:.54rem;line-height:1.45}' +
    '.dr-blockers-label{color:var(--muted-2);font-weight:800;white-space:nowrap}' +
    '.dr-blockers-value{color:var(--text);font-weight:800}' +
    '.dr-blockers.clear{border-color:rgba(59,214,154,.2);background:rgba(59,214,154,.035)}' +
    '.dr-blockers.clear .dr-blockers-value{color:var(--green)}' +
    '.dr-checks{display:grid;grid-template-columns:1fr;gap:7px;margin-top:12px}' +
    '@media(min-width:760px){.dr-checks{grid-template-columns:repeat(5,minmax(0,1fr))}}' +
    '.dr-check{border:1px solid var(--border);border-radius:10px;padding:9px;background:rgba(7,11,20,.18);min-width:0}' +
    '.dr-check-top{display:flex;align-items:center;gap:6px}' +
    '.dr-icon{width:18px;height:18px;border-radius:6px;display:grid;place-items:center;font-size:.58rem;font-weight:900;flex:0 0 auto}' +
    '.dr-check.pass .dr-icon{background:var(--green-dim);color:var(--green)}.dr-check.fail .dr-icon{background:var(--red-dim);color:var(--red)}' +
    '.dr-check-name{font-size:.56rem;font-weight:850;color:var(--text);line-height:1.25}' +
    '.dr-check-detail{margin-top:6px;font-size:.51rem;line-height:1.4;color:var(--muted)}' +
    '.dr-foot{display:flex;flex-direction:column;gap:7px;margin-top:12px;padding:10px 11px;border-radius:10px;background:rgba(47,211,238,.03);border:1px solid rgba(47,211,238,.14)}' +
    '@media(min-width:760px){.dr-foot{flex-direction:row;align-items:center;justify-content:space-between}}' +
    '.dr-interpretation{font-size:.6rem;font-weight:900;color:var(--text)}' +
    '.dr-guard{font-size:.52rem;line-height:1.45;color:var(--muted);max-width:760px}' +
    '.dr-guard b{color:var(--accent);font-weight:850}' +
    '@media(max-width:899px){.iw-shell{margin-top:16px}.iw-head{padding:0}.iw-title{font-size:1.03rem}.iw-sub{font-size:.64rem}.ug-head{padding:15px}.ug-flow,.ug-block{padding-left:15px;padding-right:15px}.ug-guard{margin-left:15px;margin-right:15px}.dr-head,.dr-body{padding-left:15px;padding-right:15px}.dr-ring{width:74px;height:74px}.dr-blockers{flex-direction:column;gap:3px}}';
  document.head.appendChild(style);

  var shell=document.getElementById('intelligence-workspace');
  if(!shell){
    shell=document.createElement('div');
    shell.id='intelligence-workspace';
    shell.className='iw-shell';
    shell.innerHTML=
      '<div class="iw-head">' +
        '<div><div class="iw-kicker">Decision Intelligence Workspace</div><div class="iw-title">Keputusan utama dan monitoring dalam satu area</div><div class="iw-sub">Final Intelligence Dashboard menjadi tampilan utama. Fresh OOS memantau validasi prospektif model, sementara alert, timeline, drift, dan analytics tetap menjadi observability tanpa mengulang seluruh Intelligence Layer di layar.</div></div>' +
        '<span class="iw-chip">RINGKAS & TERORGANISASI</span>' +
      '</div>' +
      '<div class="iw-zone-label">Executive View</div><div class="iw-zone" id="iw-executive"></div>' +
      '<div class="iw-zone-label">Cara Penggunaan</div><div class="iw-zone" id="iw-guide"></div>' +
      '<div class="iw-zone-label">Fresh OOS Validation</div><div class="iw-zone" id="iw-oos"></div>' +
      '<div class="iw-zone-label">Decision Watch</div><div class="iw-zone" id="iw-watch"></div>' +
      '<div class="iw-divider"></div>' +
      '<div class="iw-zone-label">History & Observability</div><div class="iw-observe" id="iw-observe"></div>';
    liveShell.insertAdjacentElement('afterend',shell);
  }

  var guide=document.getElementById('how-to-use-bcai');
  if(!guide){
    guide=document.createElement('div');
    guide.id='how-to-use-bcai';
    guide.className='ug-panel';
    guide.innerHTML=
      '<div class="ug-head">' +
        '<div><div class="ug-eyebrow">How to Read Best Currency AI</div><div class="ug-title">Gunakan sebagai funnel keputusan — bukan sinyal entry otomatis</div><div class="ug-lead">Mulai dari bias mata uang, gunakan Actionability sebagai primary gate, lalu cek Risk, konteks eksternal, Counter-Thesis, dan kondisi invalidasi sebelum membaca Final Assessment.</div></div>' +
        '<span class="ug-badge">RETROSPECTIVE DIAGNOSTIC · N=510</span>' +
      '</div>' +
      '<div class="ug-flow">' +
        '<div class="ug-step"><div class="ug-step-n">1</div><div class="ug-step-t">Currency Strength</div><div class="ug-step-s">Temukan strongest / weakest & directional bias.</div></div>' +
        '<div class="ug-step"><div class="ug-step-n">2</div><div class="ug-step-t">Actionability</div><div class="ug-step-s">Primary gate: ACTIONABLE, SELECTIVE, atau FILTERED.</div></div>' +
        '<div class="ug-step"><div class="ug-step-n">3</div><div class="ug-step-t">Risk v0.2</div><div class="ug-step-s">Nilai risiko kontekstual, bukan peluang rugi.</div></div>' +
        '<div class="ug-step"><div class="ug-step-n">4</div><div class="ug-step-t">Context + Counter</div><div class="ug-step-s">Macro, Cross-Market, News, dan Counter-Thesis.</div></div>' +
        '<div class="ug-step"><div class="ug-step-n">5</div><div class="ug-step-t">Invalidation</div><div class="ug-step-s">Cari kondisi yang dapat membatalkan tesis.</div></div>' +
        '<div class="ug-step"><div class="ug-step-n">6</div><div class="ug-step-t">Final Assessment</div><div class="ug-step-s">Ringkasan decision-support, bukan eksekusi.</div></div>' +
      '</div>' +
      '<div class="ug-block"><div class="ug-block-title">Actionability v1.1 · Primary Gate · Backtest 14 Aug 2024 — 13 Aug 2026</div><div class="ug-state-grid">' +
        '<div class="ug-state"><div class="ug-state-top"><span class="ug-state-name ug-green">ACTIONABLE</span><span class="ug-dot ug-green"></span></div><div class="ug-state-use">Prioritaskan untuk review lebih dalam</div><div class="ug-state-note">State dengan pemisahan historis paling kuat. Tetap wajib cek Risk dan konteks.</div><div class="ug-metrics"><span class="ug-metric">N <b>50</b></span><span class="ug-metric">Hit <b>60.0%</b></span><span class="ug-metric">Avg dir. return <b>+0.1151%</b></span></div></div>' +
        '<div class="ug-state"><div class="ug-state-top"><span class="ug-state-name ug-amber">SELECTIVE</span><span class="ug-dot ug-amber"></span></div><div class="ug-state-use">Tunggu / review secara selektif</div><div class="ug-state-note">Belum menunjukkan pemisahan historis yang cukup untuk dipakai sendirian.</div><div class="ug-metrics"><span class="ug-metric">N <b>159</b></span><span class="ug-metric">Hit <b>49.7%</b></span><span class="ug-metric">Avg dir. return <b>-0.0036%</b></span></div></div>' +
        '<div class="ug-state"><div class="ug-state-top"><span class="ug-state-name ug-red">FILTERED</span><span class="ug-dot ug-red"></span></div><div class="ug-state-use">Turunkan prioritas</div><div class="ug-state-note">Gunakan sebagai filter untuk menghindari setup yang kualitas evidencenya lebih lemah.</div><div class="ug-metrics"><span class="ug-metric">N <b>301</b></span><span class="ug-metric">Hit <b>46.2%</b></span><span class="ug-metric">Avg dir. return <b>-0.0259%</b></span></div></div>' +
      '</div></div>' +
      '<div class="ug-block"><div class="ug-block-title">Risk v0.2 · Secondary Filter · Retrospective Structural Diagnostic</div><div class="ug-risk-grid">' +
        '<div class="ug-risk"><div class="ug-risk-name ug-green">LOW</div><div class="ug-risk-m">N 97 · Hit 56.7% · Avg dir. return +0.0606%<br>Lebih konstruktif secara historis; tetap bukan probabilitas profit.</div></div>' +
        '<div class="ug-risk"><div class="ug-risk-name ug-amber">MODERATE</div><div class="ug-risk-m">N 270 · Hit 47.8% · Avg dir. return +0.0088%<br>Butuh review tambahan terhadap evidence dan invalidation.</div></div>' +
        '<div class="ug-risk"><div class="ug-risk-name ug-red">HIGH</div><div class="ug-risk-m">N 143 · Hit 44.8% · Avg dir. return -0.0759%<br>Elevated caution; turunkan prioritas bila konteks juga bertentangan.</div></div>' +
      '</div></div>' +
      '<div class="ug-block"><div class="ug-block-title">Rekomendasi Penggunaan</div><div class="ug-use-grid">' +
        '<div class="ug-use good"><div class="ug-use-h">PRIORITAS REVIEW</div><div class="ug-use-p">ACTIONABLE + Risk LOW/MODERATE + konteks tidak contradicted + Counter-Thesis tidak dominan. Gunakan sebagai kandidat untuk analisis lanjutan.</div></div>' +
        '<div class="ug-use wait"><div class="ug-use-h">TUNGGU / REVIEW</div><div class="ug-use-p">SELECTIVE, MIXED_CONTEXT, atau evidence eksternal belum konsisten. Jangan memaksakan directional bias menjadi keputusan.</div></div>' +
        '<div class="ug-use stop"><div class="ug-use-h">DEPRIORITIZE</div><div class="ug-use-p">FILTERED, HIGH Risk, CONTEXT_CONTRADICTED, RISK_CONSTRAINED, atau bukti tidak cukup. Fokus pada setup lain.</div></div>' +
      '</div></div>' +
      '<div class="ug-guard"><b>Guardrail:</b> angka di atas adalah retrospective diagnostic, bukan Fresh OOS, win probability, profit forecast, atau executable trading P&amp;L. Actionability dan Risk adalah lapisan filtering / decision-support. Fresh OOS tetap berjalan dengan model frozen untuk menguji perilaku pada unseen future observations.</div>';
  }

  var guideZone=document.getElementById('iw-guide');
  if(guideZone&&guide.parentElement!==guideZone) guideZone.appendChild(guide);

  var readiness=document.getElementById('decision-readiness');
  if(!readiness){
    readiness=document.createElement('div');
    readiness.id='decision-readiness';
    readiness.className='dr-panel partial';
    readiness.dataset.methodology=DECISION_READINESS_METHOD;
    readiness.dataset.methodologyVersion='0.1';
    readiness.dataset.role='presentation_only';
    readiness.style.setProperty('--dr-pct','0%');
    readiness.innerHTML=
      '<div class="dr-head">' +
        '<div><div class="dr-eyebrow">Decision Readiness</div><div class="dr-title">Persentase syarat review yang terpenuhi</div><div class="dr-sub">Ringkasan rule-based dari lima pemeriksaan keputusan. Setiap check bernilai 20 poin; Primary Gate tetap ditentukan oleh Actionability dan dapat meng-override interpretasi persentase.</div></div>' +
        '<div class="dr-summary"><div class="dr-ring"><div class="dr-pct" id="dr-pct">—</div></div><div class="dr-summary-meta"><div class="dr-met" id="dr-met">Memuat…</div><span class="dr-primary fail" id="dr-primary">PRIMARY GATE · —</span></div></div>' +
      '</div>' +
      '<div class="dr-body">' +
        '<div class="dr-progress"><span></span></div>' +
        '<div class="dr-scale"><span>0–40% · Low Readiness</span><span>60% · Review</span><span>80–100% · High Readiness</span></div>' +
        '<div class="dr-blockers" id="dr-blockers"><span class="dr-blockers-label">Current blockers</span><span class="dr-blockers-value">Memuat…</span></div>' +
        '<div class="dr-checks" id="dr-checks"></div>' +
        '<div class="dr-foot"><div class="dr-interpretation" id="dr-interpretation">Menunggu data terbaru…</div><div class="dr-guard"><b>Guardrail:</b> Decision Readiness mengukur requirement completion, bukan win probability, expected return, profit forecast, atau performa trading.</div></div>' +
      '</div>';
  }
  if(guideZone&&readiness.parentElement!==guideZone) guideZone.appendChild(readiness);

  function drEsc(value){
    return String(value==null?'—':value).replace(/[&<>"']/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c];
    });
  }
  function drNum(value){
    var n=Number(value);
    return Number.isFinite(n)?n.toFixed(1).replace('.',','):'—';
  }
  function drRender(payload){
    var data=payload&&payload.data?payload.data:payload;
    var intel=data&&data.intelligence_layer||{};
    var layers=intel.layers||{};
    var f=layers.final_reasoner||{};
    var r=layers.risk||{};
    var c=layers.counter_thesis||{};
    var a=data&&data.actionability_score&&(data.actionability_score.current||(data.actionability_score.timeframes&&data.actionability_score.timeframes.daily))||intel.upstream_actionability||{};
    var counts=f.context_counts||{};
    var supports=Number(counts.supports)||0;
    var opposes=Number(counts.opposes)||0;
    var available=Number(counts.available)||0;
    var expected=Number(counts.expected)||3;
    var challenge=String(c.challenge_level||f.counter_thesis_challenge_level||'UNAVAILABLE').toUpperCase();
    var evidenceFor=Array.isArray(f.evidence_for)?f.evidence_for:[];
    var evidenceAgainst=Array.isArray(f.evidence_against)?f.evidence_against:[];
    var evidenceGaps=Array.isArray(f.evidence_gaps)?f.evidence_gaps:[];
    var invalidation=Array.isArray(f.invalidation_conditions)?f.invalidation_conditions:[];
    var riskState=String(r.state||f.risk_level||'UNAVAILABLE').toUpperCase();
    var actionState=String(a.state||'UNAVAILABLE').toUpperCase();

    var checks=[
      {
        name:'Actionability Gate',
        pass:actionState==='ACTIONABLE',
        detail:(Number.isFinite(Number(a.score))?drNum(a.score)+'/100 · ':'')+actionState
      },
      {
        name:'Risk Check',
        pass:riskState==='LOW'||riskState==='MODERATE',
        detail:(Number.isFinite(Number(r.score))?drNum(r.score)+'/100 · ':'')+riskState
      },
      {
        name:'External Context',
        pass:available>=2&&supports>opposes,
        detail:available+'/'+expected+' tersedia · support '+supports+' · oppose '+opposes
      },
      {
        name:'Counter-Thesis',
        pass:challenge!=='HIGH'&&challenge!=='UNAVAILABLE',
        detail:'Challenge '+challenge
      },
      {
        name:'Evidence & Invalidation',
        pass:(evidenceFor.length+evidenceAgainst.length)>=2&&invalidation.length>0&&evidenceGaps.length===0,
        detail:(evidenceFor.length+evidenceAgainst.length)+' evidence · '+invalidation.length+' invalidation · gaps '+evidenceGaps.length
      }
    ];

    var met=checks.filter(function(x){return x.pass;}).length;
    var pct=met*20;
    var primaryPassed=checks[0].pass;
    var className=!primaryPassed?'low':(pct>=80?'high':pct>=60?'partial':'low');
    var interpretation=!primaryPassed?'DEPRIORITIZE · Primary Gate belum terpenuhi':(pct>=80?'PRIORITIZE REVIEW · High Readiness':pct>=60?'REVIEW SELECTIVELY · Partial Readiness':'DEPRIORITIZE · Low Readiness');
    var blockers=checks.filter(function(x){return !x.pass;}).map(function(x){return x.name;});

    readiness.className='dr-panel '+className;
    readiness.style.setProperty('--dr-pct',pct+'%');
    document.getElementById('dr-pct').textContent=pct+'%';
    document.getElementById('dr-met').textContent=met+' / 5 checks met';
    var primary=document.getElementById('dr-primary');
    primary.className='dr-primary '+(primaryPassed?'pass':'fail');
    primary.textContent='PRIMARY GATE · '+(primaryPassed?'PASSED':'NOT PASSED');
    document.getElementById('dr-interpretation').textContent=interpretation;

    var blockersEl=document.getElementById('dr-blockers');
    if(blockersEl){
      blockersEl.className='dr-blockers'+(blockers.length?'':' clear');
      blockersEl.innerHTML='<span class="dr-blockers-label">Current blockers</span><span class="dr-blockers-value">'+drEsc(blockers.length?blockers.join(' · '):'None — all five checks met')+'</span>';
    }

    document.getElementById('dr-checks').innerHTML=checks.map(function(x){
      return '<div class="dr-check '+(x.pass?'pass':'fail')+'"><div class="dr-check-top"><span class="dr-icon">'+(x.pass?'✓':'×')+'</span><span class="dr-check-name">'+drEsc(x.name)+'</span></div><div class="dr-check-detail">'+drEsc(x.detail)+'</div></div>';
    }).join('');
  }
  function drLoad(){
    fetch('./data/currency-strength.json?decision-readiness='+Date.now(),{headers:{Accept:'application/json'},cache:'no-store'})
      .then(function(res){if(!res.ok) throw new Error('HTTP '+res.status);return res.json();})
      .then(drRender)
      .catch(function(){
        var pct=document.getElementById('dr-pct');
        var met=document.getElementById('dr-met');
        var blockers=document.getElementById('dr-blockers');
        var interpretation=document.getElementById('dr-interpretation');
        if(pct) pct.textContent='—';
        if(met) met.textContent='Data belum tersedia';
        if(blockers) blockers.innerHTML='<span class="dr-blockers-label">Current blockers</span><span class="dr-blockers-value">Tidak dapat dihitung</span>';
        if(interpretation) interpretation.textContent='Decision Readiness tidak dapat dihitung pada snapshot ini.';
      });
  }

  var nav=document.querySelector('.analysis-nav');
  if(nav&&!document.getElementById('how-to-use-nav')){
    var navLink=document.createElement('a');
    navLink.id='how-to-use-nav';
    navLink.href='#how-to-use-bcai';
    navLink.textContent='Cara Pakai';
    var freeze=nav.querySelector('.analysis-freeze');
    if(freeze) nav.insertBefore(navLink,freeze); else nav.appendChild(navLink);
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
    move('how-to-use-bcai','iw-guide');
    move('decision-readiness','iw-guide');
    move('fresh-oos-monitoring','iw-oos');
    move('decision-alert-watch','iw-watch');
    move('intelligence-timeline','iw-observe');
    move('intraday-context-drift','iw-observe');
    move('decision-change-analytics','iw-observe');
  }

  organize();
  drLoad();

  var refresh=document.getElementById('live-refresh');
  if(refresh) refresh.addEventListener('click',function(){setTimeout(drLoad,450);});
  setInterval(drLoad,60000);

  var observer=new MutationObserver(function(){organize();});
  observer.observe(liveSection,{childList:true,subtree:true});
  window.setTimeout(function(){organize();observer.disconnect();},2500);
})();