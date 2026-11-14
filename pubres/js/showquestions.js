document.addEventListener('DOMContentLoaded', () => {
   //stav hromadnych checkboxov AI napovedy (kategoria, kapitola) sa odvodzuje od checkboxov otazok
   function nastavStav(box, otazky) {
      const zapnute = otazky.filter(o => o.checked).length;
      box.checked = otazky.length > 0 && zapnute === otazky.length;
      box.indeterminate = zapnute > 0 && zapnute < otazky.length;
   }

   function prepocitajNapovedu() {
      document.querySelectorAll('input.napoveda-check[data-typ="kategoria"]:not(:disabled)').forEach(box => {
         const otazky = [...document.querySelectorAll('input.napoveda-check[data-typ="otazka"]:not(:disabled)')].filter(o => o.dataset.kategoria === box.dataset.id);
         nastavStav(box, otazky);
      });
      const master = document.getElementById('napoveda-kapitola');
      if (master) {
         const otazky = [...aktivnaKapitola().querySelectorAll('input.napoveda-check[data-typ="otazka"]:not(:disabled)')];
         master.disabled = otazky.length === 0;
         nastavStav(master, otazky);
      }
   }

   //hromadny checkbox v riadku predmetu patri aktivnej kapitole (tabu)
   function aktivnaKapitola() {
      return document.querySelector('.tab-pane.active');
   }

   prepocitajNapovedu();
   document.addEventListener('shown.bs.tab', prepocitajNapovedu);

   document.addEventListener('change', async (e) => {
      if (!e.target.matches('input.napoveda-check')) return;
      const cb = e.target;
      const {typ, predmet} = cb.dataset;
      const id = typ === 'kapitola' ? aktivnaKapitola().id : cb.dataset.id;
      const povolene = cb.checked ? '1' : '0';
      const telo = new URLSearchParams({id, typ, povolene});
      if (predmet) telo.set('predmet', predmet);
      let ok = false;
      try {
         const resp = await fetch('/admin/setainapoveda', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: telo
         });
         ok = resp.ok;
      } catch (err) {
         console.error('Chyba:', err);
      }
      if (!ok) {
         if (typ === 'otazka') cb.checked = !cb.checked;
         prepocitajNapovedu();
         return;
      }
      //server zmenil vsetky vhodne otazky, preto sa rovnako zmenia checkboxy otazok pod nim
      if (typ === 'kategoria') {
         document.querySelectorAll(`input.napoveda-check[data-typ="otazka"]:not(:disabled)[data-kategoria="${CSS.escape(id)}"]`).forEach(o => { o.checked = cb.checked; });
      } else if (typ === 'kapitola') {
         aktivnaKapitola().querySelectorAll('input.napoveda-check[data-typ="otazka"]:not(:disabled)').forEach(o => { o.checked = cb.checked; });
      }
      prepocitajNapovedu();
   });

   document.addEventListener('change', (e) => {
      if (!e.target.matches('input.pause-check')) return;
      const cb = e.target;
      const id = cb.dataset.id;
      const typ = cb.dataset.typ;
      const paused = cb.checked ? '0' : '1';
      fetch('/admin/setpaused', {
         method: 'POST',
         headers: {'Content-Type': 'application/x-www-form-urlencoded'},
         body: new URLSearchParams({ id, typ, paused })
      }).then(resp => {
         if (!resp.ok) cb.checked = !cb.checked;
      }).catch(() => {
         cb.checked = !cb.checked;
      });
   });
});
