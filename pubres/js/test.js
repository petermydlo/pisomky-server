document.addEventListener('DOMContentLoaded', () => {
   // Rating hviezdicky - postupne rozsvecovanie
   document.querySelectorAll('.rating-wrap').forEach(wrap => {
      const stars = wrap.querySelectorAll('.rating-star');
      const radios = Array.from(wrap.querySelectorAll('input[type=radio]'));
      radios.forEach(radio => {
         radio.addEventListener('change', () => {
            const idx = radios.indexOf(radio);
            stars.forEach((star, j) => {
               star.style.color = j < idx ? 'var(--bs-warning)' : 'var(--bs-secondary-bg)';
            });
         });
      });
   });

   function deaktivujZiarovky() {
      document.querySelectorAll('.ai-napoveda-btn').forEach(el => el.classList.add('hint-vycerpany'));
   }

   // Kliknutie na ikonu žiarovky
   document.querySelectorAll('.ai-napoveda-btn').forEach(btn => {
      btn.addEventListener('click', () => {
         if (btn.classList.contains('hint-vycerpany')) return;
         const otazkaId = btn.dataset.otazkaId;
         const testId = btn.dataset.testId;
         btn.style.opacity = '0.5';
         btn.style.pointerEvents = 'none';

         poziadajAINapovedu(otazkaId, testId).finally(() => {
            btn.style.opacity = '';
            btn.style.pointerEvents = '';
         });

         document.querySelectorAll('#toastFeedback .feedback-btn').forEach(el => {
            el.dataset.testId = testId;
         });
      });
   });

   //odosle otazku na AI a zobrazi odpoved cez SSE streaming
   function poziadajAINapovedu(otazkaId, testId) {
      const toast = zabezpecToastKontajner('warning', 'AI Help (experimental)', false);
      const toastMessage = document.getElementById('toastMessage');
      const toastFeedback = document.getElementById('toastFeedback');
      toastMessage.innerHTML = '<strong>AI is thinking...</strong>';
      toastFeedback.classList.add('d-none');
      toastFeedback.classList.remove('d-flex');
      toast.show();
      const toastEl = document.getElementById('liveToast');

      return new Promise((resolve) => {
         const params = new URLSearchParams({ test_id: testId, otazka_id: otazkaId });
         const es = new EventSource(`/ai/napoveda?${params.toString()}`);
         let hintText = '';
         let completed = false;

         toastEl.addEventListener('hidden.bs.toast', () => {
            if (!completed) {
               completed = true;
               es.close();
               resolve();
            }
         }, { once: true });

         es.addEventListener('meta', (e) => {
            const data = JSON.parse(e.data);
            toastFeedback.querySelectorAll('.feedback-btn').forEach(el => el.dataset.zapisId = data.zapis_id);
            if (typeof data.remaining === 'number') {
               document.querySelectorAll('.ai-napoveda-btn').forEach(el => el.title = `AI help (zostatok: ${data.remaining})`);
               if (data.remaining <= 0) deaktivujZiarovky();
            }
         });

         es.addEventListener('chunk', (e) => {
            const data = JSON.parse(e.data);
            hintText += data.text;
            const newlineIdx = hintText.indexOf('\n');
            toastMessage.textContent = newlineIdx > -1 ? hintText.slice(0, newlineIdx) : hintText;
         });

         es.addEventListener('done', () => {
            completed = true;
            es.close();
            toastFeedback.classList.remove('d-none');
            toastFeedback.classList.add('d-flex');
            setTimeout(() => {
               if (toastEl && toastEl.isConnected) toast.hide();
            }, 20000);
            resolve();
         });

         es.addEventListener('napoveda_limit', () => {
            completed = true;
            toastMessage.textContent = 'Vyčerpal si všetky nápovede pre tento test.';
            deaktivujZiarovky();
            es.close();
            setTimeout(() => {
               if (toastEl && toastEl.isConnected) toast.hide();
            }, 5000);
            resolve();
         });

         es.addEventListener('napoveda_error', (e) => {
            completed = true;
            const data = JSON.parse(e.data);
            toastMessage.textContent = data.error;
            es.close();
            resolve();
         });

         es.onerror = () => {
            if (completed) return;
            toastMessage.textContent = 'Chyba pri spojení s AI.';
            es.close();
            resolve();
         };
      });
   }

   //zmeni farbu pozadia otazky podla zaskrtnuteho pomocneho radia
   document.addEventListener('change', (e) => {
      if (!e.target.matches('.radio.col-up input')) return;
      const div = e.target.closest('.flex-container-table-znenie');
      div.className = 'flex-container-table-znenie ' + e.target.value;
   });

   //uzamkne test, a vrati uzivatela na domovsku stranku
   document.getElementById('home').addEventListener('click', async () => {
      const params = new URLSearchParams(window.location.search);
      let hlaska = 'POZOR! Chystáte sa ukončiť písomku!\nChcete pokračovať?';
      if (params.has('edit'))
         hlaska = 'POZOR! Všetky neodoslané zmeny v písomke budú zahodené!\nChcete pokračovať?';
      if (!confirm(hlaska)) return;
      const hlavicka = document.getElementById('hlavicka');
      const kluc = hlavicka.getAttribute('kluc');
      const data = new URLSearchParams({
         predmet:  hlavicka.getAttribute('predmet'),
         trieda:   hlavicka.getAttribute('trieda'),
         skupina:  hlavicka.getAttribute('skupina'),
         kapitola: hlavicka.getAttribute('kapitola'),
         fileid:   hlavicka.getAttribute('fileid'),
         stop:     terazFormatovany()
      });
      try {
         const resp = await fetch('/stoptime/' + kluc, { method: 'POST', body: data,
            headers: {'Content-Type': 'application/x-www-form-urlencoded'} });
         if (!resp.ok) {
            if (resp.status === 404) zobrazNotifikaciu('Test nenájdený!');
            else if (resp.status === 403) zobrazNotifikaciu('Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!');
            else if (resp.status === 500) zobrazNotifikaciu('Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.');
            else zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
         }
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });
});
