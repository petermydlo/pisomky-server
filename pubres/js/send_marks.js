document.addEventListener('DOMContentLoaded', () => {
   document.getElementById('ulozit').addEventListener('click', async (e) => {
      e.preventDefault();
      const hlavicka = document.getElementById('hlavicka');
      const kluc = hlavicka.getAttribute('kluc');
      const udaje = new FormData();
      udaje.append('predmet',  hlavicka.getAttribute('predmet'));
      udaje.append('trieda',   hlavicka.getAttribute('trieda'));
      udaje.append('skupina',  hlavicka.getAttribute('skupina'));
      udaje.append('kapitola', hlavicka.getAttribute('kapitola'));
      udaje.append('fileid',   hlavicka.getAttribute('fileid'));
      udaje.append('dat',      hlavicka.getAttribute('dat'));
      document.querySelectorAll("#odpovede input[type='radio'][name^='h_']:checked, #odpovede input[type='radio'][name^='bh_']:checked").forEach(el => {
         udaje.append(el.getAttribute('name'), el.parentElement.textContent);
      });
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
});
