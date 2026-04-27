document.addEventListener('DOMContentLoaded', () => {
   const vyhodnotenie = document.getElementById('vyhodnotenie');
   const min1 = parseInt(vyhodnotenie.dataset.min1, 10);
   const min2 = parseInt(vyhodnotenie.dataset.min2, 10);
   const min3 = parseInt(vyhodnotenie.dataset.min3, 10);
   const min4 = parseInt(vyhodnotenie.dataset.min4, 10);
   const hlavicka = document.getElementById('hlavicka');

   document.addEventListener('change', (e) => {
      if (e.target.matches('.radio.col-up input')) {
         const div = e.target.closest('.flex-container-table-znenie');
         div.className = 'flex-container-table-znenie ' + e.target.value;
      }

      if (e.target.matches("input[type='number'][id^='h_'], input[type='number'][id^='bh_']")) {
         let maxPoints = 0;
         document.querySelectorAll("input[type='number'][id^='h_']").forEach(el => {
            maxPoints += parseInt(el.getAttribute('max'), 10);
         });
         let totalPoints = 0;
         document.querySelectorAll("input[type='number'][id^='h_'], input[type='number'][id^='bh_']").forEach(el => {
            totalPoints += parseInt(el.value, 10);
         });
         totalPoints = Math.max(Math.min(totalPoints, maxPoints), 0);
         const percenta = totalPoints / maxPoints * 100;
         document.getElementById('pocetbodov').textContent = totalPoints;
         document.getElementById('pocetpercent').textContent = Math.floor(percenta);
         const znamka = document.getElementById('znamka');
         if (percenta >= min1) {
            znamka.textContent = '1';
            vyhodnotenie.className = 'flex-container-head-part bg-success bg-opacity-50';
         } else if (percenta >= min2) {
            znamka.textContent = '2';
            vyhodnotenie.className = 'flex-container-head-part bg-success-subtle';
         } else if (percenta >= min3) {
            znamka.textContent = '3';
            vyhodnotenie.className = 'flex-container-head-part bg-warning-subtle';
         } else if (percenta >= min4) {
            znamka.textContent = '4';
            vyhodnotenie.className = 'flex-container-head-part bg-danger-subtle';
         } else {
            znamka.textContent = '5';
            vyhodnotenie.className = 'flex-container-head-part bg-danger bg-opacity-50';
         }
      }
   });

   document.querySelectorAll('.radio.col-up input:checked').forEach(el => {
      el.dispatchEvent(new Event('change'));
   });
   document.querySelector("input[type='number'][id^='h_']")?.dispatchEvent(new Event('change', { bubbles: true }));

   document.getElementById('ulozit').addEventListener('click', async (e) => {
      e.preventDefault();
      const kluc = hlavicka.getAttribute('kluc');
      const udaje = new FormData();
      udaje.append('predmet',  hlavicka.getAttribute('predmet'));
      udaje.append('trieda',   hlavicka.getAttribute('trieda'));
      udaje.append('skupina',  hlavicka.getAttribute('skupina'));
      udaje.append('kapitola', hlavicka.getAttribute('kapitola'));
      udaje.append('fileid',   hlavicka.getAttribute('fileid'));
      udaje.append('dat',      hlavicka.getAttribute('dat'));
      document.querySelectorAll("#odpovede input[type='number'][id^='h_'], #odpovede input[type='number'][id^='bh_'], #odpovede input[type='text'][id^='k_']").forEach(el => {
         udaje.append(el.id, el.value);
      });
      try {
         const resp = await fetch('/admin/savemarks/' + kluc, { method: 'POST', body: udaje });
         if (resp.ok) {
            zobrazNotifikaciu('Známky úspešne uložené.', 'success', 'Úspech');
         } else {
            if (resp.status === 500) zobrazNotifikaciu('Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.');
            else zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
         }
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });

   document.getElementById('ai-evaluate-btn').addEventListener('click', async (e) => {
      e.preventDefault();
      const btn = e.currentTarget;
      btn.querySelector('i').classList.replace('bi-robot', 'bi-hourglass-split');
      zobrazNotifikaciu('AI vyhodnocuje otázky...', 'info', 'AI', 10000);

      const udaje = new FormData();
      udaje.append('test_id',  hlavicka.getAttribute('kluc'));
      udaje.append('predmet',  hlavicka.getAttribute('predmet'));
      udaje.append('trieda',   hlavicka.getAttribute('trieda'));
      udaje.append('skupina',  hlavicka.getAttribute('skupina'));
      udaje.append('kapitola', hlavicka.getAttribute('kapitola'));
      udaje.append('fileid',   hlavicka.getAttribute('fileid'));

      try {
         const resp = await fetch('/admin/ai/evaluate-open', { method: 'POST', body: udaje });
         const data = await resp.json();

         if (!data.ok) {
            const msg = data.kod === 'no_questions'
               ? 'Žiadne otvorené otázky so vzorom na vyhodnotenie.'
               : `Chyba: ${data.error}`;
            zobrazNotifikaciu(msg, 'warning', 'AI');
            return;
         }

         const otvorene = document.querySelectorAll("input[type='number'][id^='h_'], input[type='number'][id^='bh_']").length;
         let uspesne = 0;
         for (const vysledok of data.vysledky) {
            const bh = document.getElementById('bh_' + vysledok.id);
            const input = bh ?? document.getElementById('h_' + vysledok.id);
            input.value = vysledok.body;
            input.dispatchEvent(new Event('change', { bubbles: true }));
            document.getElementById('k_' + vysledok.id).value = vysledok.dovod;
            uspesne++;
         }
         const preskocene = otvorene - uspesne;
         const msg = preskocene > 0
            ? `AI vyhodnotila ${uspesne} otázok, ${preskocene} preskočila (bez vzoru). Skontrolujte a uložte.`
            : `AI vyhodnotila ${uspesne} otázok. Skontrolujte a uložte.`;
         zobrazNotifikaciu(msg, 'success', 'AI');
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Chyba pri komunikácii so serverom.', 'danger', 'AI');
      } finally {
         btn.querySelector('i').classList.replace('bi-hourglass-split', 'bi-robot');
      }
   });
});
