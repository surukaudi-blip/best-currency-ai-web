(function(){
  var navScript=document.createElement('script');
  navScript.src='asset-nav.js?v=20260819-readiness-fix2';
  navScript.async=false;
  document.body.appendChild(navScript);

  var core=document.createElement('script');
  core.src='beta-program-core.js?v=20260819-market-tools';
  core.async=false;
  core.onload=function(){
    var refresh=document.createElement('script');
    refresh.src='asset-nav.js?v=20260819-readiness-fix2b';
    refresh.async=false;
    document.body.appendChild(refresh);
  };
  document.body.appendChild(core);
})();
