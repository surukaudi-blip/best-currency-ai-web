(function(){
  var items=[
    ['Forex','index.html','index.html'],
    ['Stocks','stocks.html','stocks.html'],
    ['Crypto','crypto.html','crypto.html'],
    ['Indeks','indices.html','indices.html'],
    ['Oil','oil.html','oil.html'],
    ['Gold','gold.html','gold.html']
  ];
  function currentPage(){
    var p=(location.pathname.split('/').pop()||'index.html').toLowerCase();
    return p||'index.html';
  }
  function apply(){
    var nav=document.querySelector('.analysis-nav, header .links');
    if(!nav) return;
    var freeze=nav.querySelector('.analysis-freeze, .freeze');
    Array.from(nav.querySelectorAll('a')).forEach(function(a){a.remove();});
    var current=currentPage();
    items.forEach(function(item){
      var a=document.createElement('a');
      a.href=item[1];
      a.textContent=item[0];
      a.setAttribute('data-primary-asset-nav','true');
      if(current===item[2]) a.classList.add('active');
      if(freeze) nav.insertBefore(a,freeze); else nav.appendChild(a);
    });
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',apply); else apply();
  setTimeout(apply,0);
  setTimeout(apply,250);
  setTimeout(apply,1000);
})();
