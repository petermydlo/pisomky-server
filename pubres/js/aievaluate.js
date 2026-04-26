document.addEventListener('DOMContentLoaded', () => {
   document.getElementById('ai-evaluate-btn').addEventListener('click', async (e) => {
      e.preventDefault();
      const btn = e.currentTarget;
      const hlavicka = document.getElementById('hlavicka');
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
            input.dispatchEvent(new Event('change'));
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
