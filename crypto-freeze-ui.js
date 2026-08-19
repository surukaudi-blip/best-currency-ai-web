(function(){
  function apply(){
    var status=document.querySelector('.status');
    if(status){
      status.innerHTML='<i></i>FRESH OOS · MODEL FROZEN';
      status.style.borderColor='rgba(59,214,154,.3)';
      status.style.background='rgba(59,214,154,.1)';
      status.style.color='var(--green,#3bd69a)';
      var dot=status.querySelector('i');
      if(dot){dot.style.background='var(--green,#3bd69a)';dot.style.boxShadow='0 0 0 4px rgba(59,214,154,.12)';}
    }
    Array.from(document.querySelectorAll('.kpi')).forEach(function(card){
      var key=card.querySelector('.k');
      var sub=card.querySelector('.s');
      if(key&&sub&&/Active Model/i.test(key.textContent||'')) sub.textContent='Frozen prospective decision layer';
    });
    var hero=document.querySelector('.hero p');
    if(hero&&hero.textContent.indexOf('FROZEN')<0){
      hero.textContent+=' Model v0.4.1 sudah FROZEN; observasi berikutnya adalah Fresh OOS prospective-only tanpa historical backfill.';
    }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',apply,{once:true}); else apply();
})();
