(function(){
  var liveSection=document.getElementById('live-strength');
  if(!liveSection || document.getElementById('beta-program')) return;

  var style=document.createElement('style');
  style.textContent=
    '#beta-program{position:relative;padding:64px 0 72px;background:linear-gradient(180deg,rgba(47,211,238,.025),rgba(13,20,32,.78));border-top:1px solid var(--border);border-bottom:1px solid var(--border);overflow:hidden}' +
    '#beta-program:before{content:"";position:absolute;inset:0;background:radial-gradient(620px 360px at 85% 0%,rgba(47,211,238,.08),transparent 70%);pointer-events:none}' +
    '.beta-wrap{position:relative;z-index:1}' +
    '.beta-head{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:26px}' +
    '.beta-head-copy{max-width:760px}' +
    '.beta-kicker{font-size:.62rem;text-transform:uppercase;letter-spacing:.12em;color:var(--accent);font-weight:850;margin-bottom:7px}' +
    '.beta-title{font-size:clamp(1.55rem,3vw,2.2rem);font-weight:850;line-height:1.18;color:var(--text)}' +
    '.beta-lead{margin-top:9px;font-size:.92rem;line-height:1.62;color:var(--muted);max-width:760px}' +
    '.beta-status{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(59,214,154,.28);background:rgba(59,214,154,.055);color:var(--green);border-radius:999px;padding:7px 11px;font-size:.58rem;font-weight:850;letter-spacing:.05em;white-space:nowrap}' +
    '.beta-status:before{content:"";width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 0 3px var(--green-dim)}' +
    '.beta-grid{display:grid;grid-template-columns:1fr;gap:14px}' +
    '@media(min-width:980px){.beta-grid{grid-template-columns:.92fr 1.08fr;gap:18px}}' +
    '.beta-panel{border:1px solid var(--border-2);border-radius:16px;background:rgba(7,11,20,.28);overflow:hidden}' +
    '.beta-panel-body{padding:18px}' +
    '.beta-section-title{font-size:.64rem;text-transform:uppercase;letter-spacing:.08em;color:var(--muted-2);font-weight:850;margin-bottom:10px}' +
    '.beta-goal{font-size:.88rem;line-height:1.55;color:var(--text);margin-bottom:15px}' +
    '.beta-cards{display:grid;grid-template-columns:1fr 1fr;gap:8px}' +
    '.beta-card{border:1px solid var(--border);border-radius:11px;background:rgba(13,20,32,.65);padding:11px}' +
    '.beta-card b{display:block;font-size:.64rem;color:var(--text);margin-bottom:3px}' +
    '.beta-card span{display:block;font-size:.55rem;line-height:1.42;color:var(--muted)}' +
    '.beta-flow{display:grid;gap:7px;margin-top:14px}' +
    '.beta-flow-row{display:flex;align-items:flex-start;gap:9px;padding:9px 10px;border:1px solid var(--border);border-radius:10px;background:rgba(13,20,32,.48)}' +
    '.beta-flow-n{width:20px;height:20px;border-radius:6px;background:var(--accent-dim);color:var(--accent);display:grid;place-items:center;flex:0 0 auto;font-size:.54rem;font-weight:900}' +
    '.beta-flow-row b{display:block;font-size:.6rem;color:var(--text)}' +
    '.beta-flow-row span{display:block;margin-top:2px;font-size:.53rem;color:var(--muted);line-height:1.4}' +
    '.beta-separation{margin-top:14px;padding:11px 12px;border-radius:11px;border:1px solid rgba(240,163,47,.22);background:rgba(240,163,47,.04);font-size:.56rem;line-height:1.52;color:var(--muted)}' +
    '.beta-separation b{color:var(--amber)}' +
    '.beta-form{padding:18px}' +
    '.beta-form h3{font-size:1rem;color:var(--text);margin-bottom:4px}' +
    '.beta-form-sub{font-size:.6rem;line-height:1.5;color:var(--muted);margin-bottom:14px}' +
    '.beta-form-grid{display:grid;grid-template-columns:1fr;gap:10px}' +
    '@media(min-width:700px){.beta-form-grid.two{grid-template-columns:1fr 1fr}}' +
    '.beta-field label{display:block;font-size:.56rem;font-weight:800;color:var(--text);margin-bottom:5px}' +
    '.beta-field label small{font-weight:500;color:var(--muted-2)}' +
    '.beta-field input,.beta-field select,.beta-field textarea{width:100%;border:1px solid var(--border);border-radius:9px;background:var(--bg-3);color:var(--text);font:inherit;font-size:.63rem;padding:10px 11px;outline:none}' +
    '.beta-field textarea{min-height:82px;resize:vertical}' +
    '.beta-field input:focus,.beta-field select:focus,.beta-field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-dim)}' +
    '.beta-consent{display:flex;align-items:flex-start;gap:8px;margin:11px 0 12px;font-size:.54rem;line-height:1.45;color:var(--muted)}' +
    '.beta-consent input{margin-top:2px;accent-color:var(--accent)}' +
    '.beta-submit{width:100%;padding:11px 14px;border:0;border-radius:9px;background:var(--accent);color:#04121a;font:inherit;font-size:.62rem;font-weight:900;cursor:pointer}' +
    '.beta-submit:hover{filter:brightness(1.06)}.beta-submit:disabled{opacity:.6;cursor:wait}' +
    '.beta-form-note{margin-top:9px;text-align:center;font-size:.5rem;line-height:1.45;color:var(--muted-2)}' +
    '.beta-form-note a{color:var(--accent)}' +
    '.beta-form-status{display:none;margin-top:10px;padding:9px 10px;border-radius:9px;border:1px solid var(--border);font-size:.55rem;line-height:1.45;text-align:center}' +
    '.beta-form-status.ok{display:block;color:var(--green);border-color:rgba(59,214,154,.25);background:rgba(59,214,154,.045)}' +
    '.beta-form-status.info{display:block;color:var(--amber);border-color:rgba(240,163,47,.25);background:rgba(240,163,47,.045)}' +
    '.beta-inline-note{margin-top:13px;font-size:.53rem;line-height:1.48;color:var(--muted-2)}' +
    '@media(max-width:640px){#beta-program{padding:48px 0 56px}.beta-cards{grid-template-columns:1fr}.beta-panel-body,.beta-form{padding:15px}}';
  document.head.appendChild(style);

  var section=document.createElement('section');
  section.id='beta-program';
  section.innerHTML=
    '<div class="container beta-wrap">' +
      '<div class="beta-head">' +
        '<div class="beta-head-copy"><div class="beta-kicker">Structured Product Validation</div><div class="beta-title">Join the Best Currency AI Beta Program</div><div class="beta-lead">Help us evaluate whether Best Currency AI is useful, understandable, and easy to use. The beta focuses on product experience and explainability — not on changing the frozen Fresh OOS model.</div></div>' +
        '<div class="beta-status">RECRUITING · TARGET 30–50 TRADERS</div>' +
      '</div>' +
      '<div class="beta-grid">' +
        '<div class="beta-panel"><div class="beta-panel-body">' +
          '<div class="beta-section-title">What we are validating</div>' +
          '<div class="beta-goal">Participants will use the same decision workflow shown in the public workspace and tell us where the product is clear, useful, confusing, or incomplete.</div>' +
          '<div class="beta-cards">' +
            '<div class="beta-card"><b>Usefulness</b><span>Does the workflow help organize currency research?</span></div>' +
            '<div class="beta-card"><b>Explanation clarity</b><span>Are Actionability, Risk, blockers, and invalidation easy to understand?</span></div>' +
            '<div class="beta-card"><b>Workflow comprehension</b><span>Can users correctly interpret Decision Readiness without treating it as profit probability?</span></div>' +
            '<div class="beta-card"><b>Repeat usage & willingness to pay</b><span>Would users return to the workflow and consider a future paid tier?</span></div>' +
          '</div>' +
          '<div class="beta-section-title" style="margin-top:16px">Participant journey</div>' +
          '<div class="beta-flow">' +
            '<div class="beta-flow-row"><span class="beta-flow-n">1</span><div><b>Apply</b><span>Tell us your experience level, region, and research habits.</span></div></div>' +
            '<div class="beta-flow-row"><span class="beta-flow-n">2</span><div><b>Guided product tasks</b><span>Review Currency Strength, Actionability, Risk, context, Counter-Thesis, invalidation, and Decision Readiness.</span></div></div>' +
            '<div class="beta-flow-row"><span class="beta-flow-n">3</span><div><b>Structured feedback</b><span>Rate clarity, usefulness, task completion, and the overall research workflow.</span></div></div>' +
            '<div class="beta-flow-row"><span class="beta-flow-n">4</span><div><b>Follow-up</b><span>Selected participants may be invited for repeat-use and willingness-to-pay evaluation.</span></div></div>' +
          '</div>' +
          '<div class="beta-separation"><b>Product validation ≠ model validation.</b> Beta feedback may improve UI, onboarding, wording, navigation, and explainability. It does not change frozen Actionability v1.1, Risk v0.2, Counter-Thesis v0.2, Final Reasoner v0.2, thresholds, weights, or decision logic during Fresh OOS collection.</div>' +
        '</div></div>' +
        '<div class="beta-panel"><form class="beta-form" id="beta-application-form" novalidate>' +
          '<h3>Apply for the structured beta cohort</h3>' +
          '<div class="beta-form-sub">Indonesia & Southeast Asia are the initial focus, but relevant Forex traders from other regions may also apply.</div>' +
          '<input type="hidden" name="program" value="Best Currency AI Structured Beta Cohort 2026">' +
          '<input type="hidden" name="source" value="best-currency-ai-web">' +
          '<input type="hidden" name="_subject" value="Best Currency AI Beta Application">' +
          '<div class="beta-form-grid two">' +
            '<div class="beta-field"><label for="beta-name">Name <small>· required</small></label><input id="beta-name" name="name" type="text" autocomplete="name" placeholder="Your name" required></div>' +
            '<div class="beta-field"><label for="beta-email">Email <small>· required</small></label><input id="beta-email" name="email" type="email" autocomplete="email" placeholder="you@example.com" required></div>' +
          '</div>' +
          '<div class="beta-form-grid two" style="margin-top:10px">' +
            '<div class="beta-field"><label for="beta-country">Country / region <small>· required</small></label><select id="beta-country" name="country" required><option value="">Select…</option><option>Indonesia</option><option>Malaysia</option><option>Singapore</option><option>Thailand</option><option>Vietnam</option><option>Philippines</option><option>Other Southeast Asia</option><option>Other region</option></select></div>' +
            '<div class="beta-field"><label for="beta-exp">Forex experience <small>· required</small></label><select id="beta-exp" name="experience" required><option value="">Select…</option><option>Beginner · under 1 year</option><option>Intermediate · 1–3 years</option><option>Advanced · 3+ years</option><option>Professional / full-time</option></select></div>' +
          '</div>' +
          '<div class="beta-form-grid two" style="margin-top:10px">' +
            '<div class="beta-field"><label for="beta-frequency">How often do you analyze Forex?</label><select id="beta-frequency" name="analysis_frequency"><option value="">Select…</option><option>Daily</option><option>Several times per week</option><option>Weekly</option><option>Occasionally</option></select></div>' +
            '<div class="beta-field"><label for="beta-platform">Primary analysis platform</label><input id="beta-platform" name="primary_platform" type="text" placeholder="e.g. TradingView, MT5"></div>' +
          '</div>' +
          '<div class="beta-field" style="margin-top:10px"><label for="beta-challenge">Biggest challenge when analyzing currencies</label><textarea id="beta-challenge" name="analysis_challenge" placeholder="What makes currency analysis difficult or fragmented for you?"></textarea></div>' +
          '<div class="beta-field" style="margin-top:10px"><label for="beta-motivation">Why do you want to join the beta?</label><textarea id="beta-motivation" name="motivation" placeholder="What would make this beta useful to you?"></textarea></div>' +
          '<label class="beta-consent"><input id="beta-consent" name="consent" type="checkbox" value="yes" required><span>I agree to be contacted about the Best Currency AI beta and understand that this is a research/product-validation program, not financial advice or a trading-signal service.</span></label>' +
          '<button class="beta-submit" type="submit">APPLY FOR BETA</button>' +
          '<div class="beta-form-note">Please do not submit brokerage credentials, account numbers, or financial account data. See our <a href="privacy.html">Privacy Policy</a>.</div>' +
          '<div class="beta-form-status" id="beta-form-status"></div>' +
        '</form></div>' +
      '</div>' +
      '<div class="beta-inline-note">Selection is based on cohort fit and research needs. The 30–50 figure is a recruitment target, not a current-user or traction claim.</div>' +
    '</div>';

  liveSection.insertAdjacentElement('afterend',section);

  var nav=document.querySelector('.analysis-nav');
  if(nav && !document.getElementById('beta-program-nav')){
    var link=document.createElement('a');
    link.id='beta-program-nav';
    link.href='#beta-program';
    link.textContent='Beta Program';
    var freeze=nav.querySelector('.analysis-freeze');
    if(freeze) nav.insertBefore(link,freeze); else nav.appendChild(link);
  }

  var FORM_ENDPOINT='https://formspree.io/f/xnpabadp';
  var form=document.getElementById('beta-application-form');
  var status=document.getElementById('beta-form-status');
  function show(message,kind){
    if(!status) return;
    status.textContent=message;
    status.className='beta-form-status '+(kind||'info');
  }
  if(form){
    form.addEventListener('submit',function(event){
      event.preventDefault();
      var name=document.getElementById('beta-name');
      var email=document.getElementById('beta-email');
      var country=document.getElementById('beta-country');
      var exp=document.getElementById('beta-exp');
      var consent=document.getElementById('beta-consent');
      if(!name.value.trim()){show('Please enter your name.','info');name.focus();return;}
      if(!email.value || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)){show('Please enter a valid email address.','info');email.focus();return;}
      if(!country.value){show('Please select your country or region.','info');country.focus();return;}
      if(!exp.value){show('Please select your Forex experience level.','info');exp.focus();return;}
      if(!consent.checked){show('Please confirm the beta-program consent before submitting.','info');consent.focus();return;}
      var button=form.querySelector('.beta-submit');
      button.disabled=true;
      button.textContent='SUBMITTING…';
      fetch(FORM_ENDPOINT,{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}})
        .then(function(response){if(!response.ok) throw new Error('Submission failed');return response;})
        .then(function(){
          show('Application received. We will contact selected participants with the next beta-testing steps.','ok');
          form.reset();
        })
        .catch(function(){show('We could not submit your application. Please try again in a moment.','info');})
        .finally(function(){button.disabled=false;button.textContent='APPLY FOR BETA';});
    });
  }
})();