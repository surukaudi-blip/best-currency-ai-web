(function(){
  var items={
    forex:{label:'Forex',page:'index.html',status:'FRESH OOS · MODEL FROZEN',tone:'green'},
    stocks:{label:'Stocks',page:'stocks.html',status:'FRESH OOS · MODEL FROZEN',tone:'green'},
    crypto:{label:'Crypto',page:'crypto.html',status:'FRESH OOS · MODEL FROZEN',tone:'green'},
    indices:{label:'Indeks',page:'indices.html',status:'PLANNED',tone:'amber'},
    oil:{label:'Oil',page:'oil.html',status:'PLANNED',tone:'amber'},
    gold:{label:'Gold',page:'gold.html',status:'PLANNED',tone:'amber'}
  };
  var order=['forex','stocks','crypto','indices','oil','gold'];
  function pageName(){return (location.pathname.split('/').pop()||'index.html').toLowerCase();}
  function assetForPage(p){
    if(p==='stocks.html') return 'stocks';
    if(p==='crypto.html') return 'crypto';
    if(p==='indices.html') return 'indices';
    if(p==='oil.html') return 'oil';
    if(p==='gold.html') return 'gold';
    return 'forex';
  }
  function isEmbedded(){return window.top!==window.self && new URLSearchParams(location.search).get('embed')==='1';}
  function ready(fn){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',fn,{once:true});else fn();}

  if(isEmbedded()){
    ready(function(){
      var h=document.querySelector('header');
      if(h) h.style.display='none';
      document.documentElement.style.scrollBehavior='auto';
      document.body.style.minHeight='0';
      if(pageName()==='crypto.html'){
        if(!document.getElementById('crypto-readiness-loader')){
          var s=document.createElement('script');
          s.id='crypto-readiness-loader';
          s.src='crypto-readiness.js?v=20260819-readiness-fix2';
          s.async=false;
          document.body.appendChild(s);
        }
        if(!document.getElementById('crypto-freeze-ui-loader')){
          var f=document.createElement('script');
          f.id='crypto-freeze-ui-loader';
          f.src='crypto-freeze-ui.js?v=20260819-freeze-v041';
          f.async=false;
          document.body.appendChild(f);
        }
      }
    });
    return;
  }

  var currentPage=pageName();
  if(currentPage!=='index.html' && currentPage!==''){
    location.replace('index.html#asset='+assetForPage(currentPage));
    return;
  }

  ready(function(){
    var nav=document.querySelector('.analysis-nav, header .links');
    var forexMain=document.querySelector('body > main');
    if(!nav||!forexMain) return;

    if(document.getElementById('asset-workspace-shell')){
      Array.from(nav.querySelectorAll('a:not([data-primary-asset-nav])')).forEach(function(a){a.remove();});
      return;
    }

    var style=document.createElement('style');
    style.id='single-shell-asset-style';
    style.textContent=
      '.analysis-nav>a[data-primary-asset-nav]{cursor:pointer;white-space:nowrap;transition:.16s}' +
      '.analysis-nav>a[data-primary-asset-nav].active{color:var(--text);font-weight:800}' +
      '#asset-workspace-shell{display:none;background:var(--bg);min-height:calc(100vh - 64px)}' +
      '#asset-workspace-frame{display:block;width:100%;min-height:calc(100vh - 64px);border:0;background:var(--bg)}' +
      '@media(max-width:900px){.analysis-nav{overflow-x:auto;max-width:72vw;gap:12px}.analysis-nav>a[data-primary-asset-nav]{display:inline-flex!important}}';
    document.head.appendChild(style);

    var shell=document.createElement('main');
    shell.id='asset-workspace-shell';
    var frame=document.createElement('iframe');
    frame.id='asset-workspace-frame';
    frame.title='Best Currency AI asset workspace';
    frame.loading='eager';
    shell.appendChild(frame);
    forexMain.insertAdjacentElement('afterend',shell);

    var freeze=nav.querySelector('.analysis-freeze, .freeze, .status');
    Array.from(nav.querySelectorAll('a')).forEach(function(a){a.remove();});
    var links={};
    order.forEach(function(key){
      var a=document.createElement('a');
      a.href='#asset='+key;
      a.textContent=items[key].label;
      a.dataset.primaryAssetNav='true';
      a.dataset.asset=key;
      a.addEventListener('click',function(ev){ev.preventDefault();setAsset(key,true);});
      links[key]=a;
      if(freeze) nav.insertBefore(a,freeze); else nav.appendChild(a);
    });

    function ensureFreeze(){
      if(freeze) return freeze;
      freeze=document.createElement('span');
      freeze.className='analysis-freeze';
      nav.appendChild(freeze);
      return freeze;
    }
    function setStatus(key){
      var el=ensureFreeze(),meta=items[key];
      el.innerHTML='<span></span>'+meta.status;
      var dot=el.querySelector('span');
      if(meta.tone==='amber'){
        dot.style.background='var(--amber)';
        dot.style.boxShadow='0 0 0 3px var(--amber-dim)';
      }else{
        dot.style.background='var(--green)';
        dot.style.boxShadow='0 0 0 3px var(--green-dim)';
      }
    }
    function markActive(key){order.forEach(function(k){links[k].classList.toggle('active',k===key);});}
    function resizeFrame(){
      try{
        var doc=frame.contentDocument;
        if(!doc) return;
        var h=Math.max(doc.body?doc.body.scrollHeight:0,doc.documentElement?doc.documentElement.scrollHeight:0,window.innerHeight-64);
        frame.style.height=h+'px';
      }catch(e){frame.style.height='calc(100vh - 64px)';}
    }
    frame.addEventListener('load',function(){
      try{
        var doc=frame.contentDocument;
        var childHeader=doc&&doc.querySelector('header');
        if(childHeader) childHeader.style.display='none';
        resizeFrame();
        if(window.ResizeObserver&&doc&&doc.body){
          if(frame._assetResizeObserver) frame._assetResizeObserver.disconnect();
          frame._assetResizeObserver=new ResizeObserver(resizeFrame);
          frame._assetResizeObserver.observe(doc.body);
        }
      }catch(e){resizeFrame();}
    });

    function setAsset(key,push){
      if(!items[key]) key='forex';
      markActive(key);
      setStatus(key);
      if(key==='forex'){
        shell.style.display='none';
        forexMain.style.display='block';
      }else{
        forexMain.style.display='none';
        shell.style.display='block';
        var target=items[key].page+'?embed=1&shell=20260819-freeze-v041';
        if(frame.getAttribute('src')!==target) frame.setAttribute('src',target);
      }
      if(push){
        var next='#asset='+key;
        if(location.hash!==next) history.pushState({asset:key},'',next);
      }
      window.scrollTo({top:0,behavior:'auto'});
    }
    function fromLocation(){
      var m=(location.hash||'').match(/^#asset=([a-z]+)$/i);
      return m&&items[m[1].toLowerCase()]?m[1].toLowerCase():'forex';
    }
    window.addEventListener('hashchange',function(){setAsset(fromLocation(),false);});
    window.addEventListener('popstate',function(){setAsset(fromLocation(),false);});
    setAsset(fromLocation(),false);
  });
})();