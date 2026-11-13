document.addEventListener('DOMContentLoaded', () => {
   document.getElementById('loginForm').addEventListener('submit', (e) => {
      e.preventDefault();
      const kluc = document.getElementById('kluc').value;
      let adresa = '/' + encodeURIComponent(kluc.trim());
      if (document.getElementById('wm').checked)
         adresa += '?edit=true';
      window.location = adresa;
   });
});

//Obnovenie stranky testu: prehliadac zahodi staru stranku (a jej beacon /uvolni) az po odpovedi na novy GET, takze ten dostane 423.
//Token z predchadzajuceho nacitania ma len tato karta (sessionStorage); uvolnime nim vlastny prenajom a nacitame test znova.
//Token sa pouzije raz, takze pri dalsom 423 sa uz neopakuje. Stranka s 423 je pocas toho skryta (data-obsadene), aby obnovenie
//nebolo vidiet; ukaze sa az ked obnova nie je mozna (ziadny token, zlyhanie, alebo test naozaj drzi iny prehliadac).
document.addEventListener('DOMContentLoaded', async () => {
   const skryte = document.querySelectorAll('[data-obsadene]');
   if (skryte.length === 0) return;
   const ukaz = () => skryte.forEach(el => el.classList.remove('skryte'));
   const polozka = 'relacia_' + location.pathname;
   let token = null;
   try {
      token = sessionStorage.getItem(polozka);
      sessionStorage.removeItem(polozka);
   } catch (e) { /* bez sessionStorage sa obnovenie nepozna */ }
   if (!token) return ukaz();
   try {
      await fetch('/uvolni/' + location.pathname.slice(1), { method: 'POST', body: new URLSearchParams({ token }) });
   } catch (e) {
      return ukaz();
   }
   location.reload();
});
