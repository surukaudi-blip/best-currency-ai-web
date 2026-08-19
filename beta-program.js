(function(){
  var nav=document.querySelector('.analysis-nav');
  if(nav && !document.getElementById('market-tools-nav')){
    var link=document.createElement('a');
    link.id='market-tools-nav';
    link.href='markets.html';
    link.textContent='Market Tools';
    link.title='Forex, Stocks, dan Crypto Intelligence';
    var freeze=nav.querySelector('.analysis-freeze');
    if(freeze) nav.insertBefore(link,freeze); else nav.appendChild(link);
  }

  var core=document.createElement('script');
  core.src='beta-program-core.js?v=20260819-market-tools';
  core.async=false;
  document.body.appendChild(core);
})();
