(function(){
  var liveSection = document.getElementById('live-strength');
  if(!liveSection || document.getElementById('strength-history')) return;

  var style = document.createElement('style');
  style.textContent =
    '#strength-history{background:var(--bg-2);border-bottom:1px solid var(--border)}' +
    '.history-shell{background:var(--bg);border:1px solid var(--border-2);border-radius:18px;overflow:hidden}' +
    '.history-top{display:flex;flex-direction:column;gap:14px;padding:22px;border-bottom:1px solid var(--border)}' +
    '@media(min-width:760px){.history-top{flex-direction:row;align-items:center;justify-content:space-between}}' +
    '.history-top h3{font-size:1.08rem}.history-top p{font-size:.82rem;color:var(--muted);margin-top:4px}' +
    '.history-tabs{display:flex;gap:7px;flex-wrap:wrap}' +
    '.history-tab{appearance:none;border:1px solid var(--border);background:var(--bg-3);color:var(--muted);border-radius:9px;padding:7px 12px;font:inherit;font-size:.75rem;font-weight:700;cursor:pointer}' +
    '.history-tab.active{color:var(--accent);border-color:rgba(47,211,238,.5);background:var(--accent-dim)}' +
    '.history-grid{display:grid;grid-template-columns:1fr}' +
    '@media(min-width:960px){.history-grid{grid-template-columns:1.15fr .85fr}}' +
    '.history-chart-panel,.history-table-panel{padding:22px}.history-table-panel{border-top:1px solid var(--border)}' +
    '@media(min-width:960px){.history-table-panel{border-top:0;border-left:1px solid var(--border)}}' +
    '.history-panel-title{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px}' +
    '.history-panel-title h4{font-size:.9rem}.history-panel-title span{font-size:.7rem;color:var(--muted-2)}' +
    '.rank-chart-wrap{overflow-x:auto}.rank-chart{width:100%;min-width:620px;height:auto;display:block;background:var(--bg-3);border:1px solid var(--border);border-radius:12px}' +
    '.history-legend{display:grid;grid-template-columns:repeat(2,1fr);gap:6px 12px;margin-top:12px}' +
    '@media(min-width:620px){.history-legend{grid-template-columns:repeat(4,1fr)}}' +
    '.history-legend-item{display:flex;align-items:center;gap:7px;font-size:.73rem;color:var(--muted)}' +
    '.history-legend-dot{width:8px;height:8px;border-radius:50%;flex:0 0 auto}' +
    '.history-legend-item b{color:var(--text);font-weight:700}' +
    '.history-table-wrap{overflow:auto;max-height:390px}.history-table{width:100%;border-collapse:collapse}' +
    '.history-table th,.history-table td{padding:10px 8px;border-bottom:1px solid var(--border);font-size:.76rem;text-align:left;white-space:nowrap}' +
    '.history-table th{color:var(--muted-2);font-size:.67rem;text-transform:uppercase;letter-spacing:.06em;position:sticky;top:0;background:var(--bg)}' +
    '.history-strong{color:var(--green);font-weight:750}.history-weak{color:var(--red);font-weight:750}' +
    '.history-empty{padding:28px;text-align:center;color:var(--muted);font-size:.84rem}' +
    '.history-meta{padding:13px 22px;border-top:1px solid var(--border);font-size:.72rem;color:var(--muted-2)}';
  document.head.appendChild(style);

  var section = document.createElement('section');
  section.id = 'strength-history';
  section.innerHTML =
    '<div class="container">' +
      '<div class="section-head center">' +
        '<div class="kicker">Currency Strength Story</div>' +
        '<h2>Currency Strength History</h2>' +
        '<p class="lead">See how all eight currencies move through the ranking over Daily, Weekly, and Monthly periods — not only who is strongest today.</p>' +
      '</div>' +
      '<div class="history-shell">' +
        '<div class="history-top">' +
          '<div><h3>Rank journey · 8 currencies</h3><p id="history-sub">Loading ECB reference-rate analytics via Frankfurter…</p></div>' +
          '<div class="history-tabs">' +
            '<button type="button" class="history-tab active" data-history-tf="daily">Daily</button>' +
            '<button type="button" class="history-tab" data-history-tf="weekly">Weekly</button>' +
            '<button type="button" class="history-tab" data-history-tf="monthly">Monthly</button>' +
          '</div>' +
        '</div>' +
        '<div class="history-grid">' +
          '<div class="history-chart-panel">' +
            '<div class="history-panel-title"><h4>Ranking evolution</h4><span id="history-range">—</span></div>' +
            '<div class="rank-chart-wrap" id="history-chart-wrap"><div class="history-empty">Loading chart…</div></div>' +
            '<div class="history-legend" id="history-legend"></div>' +
          '</div>' +
          '<div class="history-table-panel">' +
            '<div class="history-panel-title"><h4>Strongest / Weakest history</h4><span id="history-count">—</span></div>' +
            '<div class="history-table-wrap" id="history-table-wrap"><div class="history-empty">Loading history…</div></div>' +
          '</div>' +
        '</div>' +
        '<div class="history-meta" id="history-meta">Historical strength is calculated from ECB reference rates via Frankfurter.</div>' +
      '</div>' +
    '</div>';
  liveSection.insertAdjacentElement('afterend', section);

  var liveActions = liveSection.querySelector('.live-actions');
  if(liveActions && !document.getElementById('history-jump')){
    var jump = document.createElement('a');
    jump.id = 'history-jump';
    jump.className = 'btn btn-ghost btn-sm';
    jump.href = '#strength-history';
    jump.textContent = 'View history';
    liveActions.appendChild(jump);
  }

  var activeTf = 'daily';
  var historyData = null;
  var colors = {
    USD:'#2FD3EE', EUR:'#7FB3F5', GBP:'#3BD69A', JPY:'#F26D6D',
    CHF:'#C084FC', CAD:'#F0A32F', AUD:'#F5A3C7', NZD:'#8BD8C2'
  };

  function esc(s){
    return String(s == null ? '' : s).replace(/[&<>"']/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c];
    });
  }

  function shortDate(s){
    if(!s) return '—';
    var d = new Date(String(s).slice(0,10)+'T12:00:00Z');
    if(isNaN(d.getTime())) return String(s);
    return d.toLocaleDateString(undefined,{day:'numeric',month:'short'});
  }

  function periodLabel(row, tf){
    if(tf === 'daily') return shortDate(row.to_date);
    if(tf === 'weekly') return row.period_key || (shortDate(row.from_date)+'–'+shortDate(row.to_date));
    return row.period_key || String(row.to_date || '').slice(0,7);
  }

  function renderChart(rows, currencies){
    var wrap = document.getElementById('history-chart-wrap');
    var legend = document.getElementById('history-legend');
    if(!rows.length){
      wrap.innerHTML = '<div class="history-empty">History is not available yet. Run the ECB history refresh function once after deployment.</div>';
      legend.innerHTML = '';
      return;
    }

    var chronological = rows.slice().reverse();
    var width = 760, height = 330, left = 48, right = 18, top = 24, bottom = 48;
    var plotW = width-left-right, plotH = height-top-bottom;
    var xStep = chronological.length > 1 ? plotW/(chronological.length-1) : 0;
    function x(i){return left+i*xStep;}
    function y(rank){return top+((rank-1)/7)*plotH;}

    var svg = '<svg class="rank-chart" viewBox="0 0 '+width+' '+height+'" role="img" aria-label="Currency ranking history">';
    for(var r=1;r<=8;r++){
      var yy=y(r);
      svg += '<line x1="'+left+'" y1="'+yy+'" x2="'+(width-right)+'" y2="'+yy+'" stroke="rgba(148,163,184,.15)" stroke-width="1" />';
      svg += '<text x="14" y="'+(yy+4)+'" fill="#6B7A90" font-size="11">#'+r+'</text>';
    }

    chronological.forEach(function(row,i){
      if(i===0 || i===chronological.length-1 || (chronological.length>8 && i%Math.ceil(chronological.length/6)===0)){
        svg += '<text x="'+x(i)+'" y="'+(height-16)+'" text-anchor="middle" fill="#6B7A90" font-size="10">'+esc(periodLabel(row,activeTf))+'</text>';
      }
    });

    currencies.forEach(function(ccy){
      var points=[];
      chronological.forEach(function(row,i){
        var rank=(row.ranking||[]).indexOf(ccy)+1;
        if(rank>0) points.push([x(i),y(rank),rank]);
      });
      if(!points.length) return;
      var path=points.map(function(p,i){return (i?'L':'M')+p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');
      svg += '<path d="'+path+'" fill="none" stroke="'+colors[ccy]+'" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" opacity=".9" />';
      points.forEach(function(p){svg += '<circle cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="2.6" fill="'+colors[ccy]+'" />';});
    });
    svg += '</svg>';
    wrap.innerHTML = svg;

    var latest=rows[0]||{};
    legend.innerHTML = currencies.map(function(ccy){
      var rank=(latest.ranking||[]).indexOf(ccy)+1;
      return '<div class="history-legend-item"><span class="history-legend-dot" style="background:'+colors[ccy]+'"></span><b>'+ccy+'</b><span>'+(rank?'#'+rank:'—')+'</span></div>';
    }).join('');
  }

  function renderTable(rows){
    var wrap=document.getElementById('history-table-wrap');
    if(!rows.length){
      wrap.innerHTML='<div class="history-empty">No stored ECB history for this timeframe yet.</div>';
      return;
    }
    var shown=rows.slice(0,12);
    wrap.innerHTML='<table class="history-table"><thead><tr><th>Period</th><th>Strongest</th><th>Weakest</th><th>Pair</th><th>Bias</th><th>Gap</th></tr></thead><tbody>' +
      shown.map(function(row){
        var p=row.pair_analysis||{};
        return '<tr>' +
          '<td>'+esc(periodLabel(row,activeTf))+'</td>' +
          '<td class="history-strong">'+esc(row.strongest_currency||'—')+'</td>' +
          '<td class="history-weak">'+esc(row.weakest_currency||'—')+'</td>' +
          '<td>'+esc(p.pair||'—')+'</td>' +
          '<td>'+esc(p.bias||'—')+'</td>' +
          '<td>'+((Number.isFinite(Number(p.strength_difference)))?(Number(p.strength_difference)>0?'+':'')+Number(p.strength_difference).toFixed(3):'—')+'</td>' +
        '</tr>';
      }).join('') + '</tbody></table>';
  }

  function render(){
    if(!historyData) return;
    var rows=Array.isArray(historyData[activeTf])?historyData[activeTf]:[];
    var currencies=historyData.currencies||['USD','EUR','GBP','JPY','CHF','CAD','AUD','NZD'];
    document.querySelectorAll('.history-tab').forEach(function(btn){btn.classList.toggle('active',btn.getAttribute('data-history-tf')===activeTf);});
    document.getElementById('history-count').textContent=rows.length+' periods';
    var authority=historyData.provider_authority||'ECB';
    document.getElementById('history-sub').textContent=authority+' reference-rate ranking via Frankfurter · '+activeTf.toUpperCase();
    if(rows.length){
      var oldest=rows[rows.length-1], newest=rows[0];
      document.getElementById('history-range').textContent=shortDate(oldest.from_date)+' → '+shortDate(newest.to_date);
    } else {
      document.getElementById('history-range').textContent='—';
    }
    renderChart(rows,currencies);
    renderTable(rows);
    var ts=historyData.generated_at;
    document.getElementById('history-meta').textContent='Source: '+(historyData.source||'Frankfurter')+' · Authority: '+authority+' · '+(ts?'History generated '+new Date(ts).toLocaleString():'History builder has not run yet')+' · Reference-rate analytics, not executable quotes.';
  }

  section.addEventListener('click',function(e){
    var btn=e.target.closest('.history-tab');
    if(!btn) return;
    activeTf=btn.getAttribute('data-history-tf')||'daily';
    render();
  });

  fetch('./data/currency-strength-history.json',{headers:{Accept:'application/json'},cache:'no-store'})
    .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
    .then(function(payload){historyData=payload&&payload.data?payload.data:payload;render();})
    .catch(function(){
      document.getElementById('history-sub').textContent='ECB static history data is not available yet.';
      document.getElementById('history-chart-wrap').innerHTML='<div class="history-empty">Wait for the next scheduled GitHub data update, then refresh.</div>';
      document.getElementById('history-table-wrap').innerHTML='<div class="history-empty">Waiting for ECB history data.</div>';
    });
})();
