document.addEventListener('DOMContentLoaded', () => {
   const hlavicka = document.getElementById('hlavicka');

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
   document.getElementById('home').addEventListener('click', async (e) => {
      e.preventDefault();
      const params = new URLSearchParams(window.location.search);
      let hlaska = 'POZOR! Chystáte sa ukončiť písomku!\nChcete pokračovať?';
      if (params.has('edit'))
         hlaska = 'POZOR! Všetky neodoslané zmeny v písomke budú zahodené!\nChcete pokračovať?';
      if (!confirm(hlaska)) return;
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

   let autosaveTimer = null;
   const ikonClassy = ['bi-cloud-check', 'bi-cloud-upload', 'bi-cloud-slash', 'text-success', 'text-warning', 'text-primary', 'text-danger'];

   function setIcon(stav) {
      const icon = document.getElementById('save-icon');
      if (!icon) return;
      icon.classList.remove(...ikonClassy);
      if (stav === 'ok')           icon.classList.add('bi-cloud-check', 'text-success');
      else if (stav === 'saving')  icon.classList.add('bi-cloud-upload', 'text-primary');
      else if (stav === 'unsaved') icon.classList.add('bi-cloud-slash', 'text-warning');
      else if (stav === 'error')   icon.classList.add('bi-cloud-slash', 'text-danger');
   }

   async function saveAnswers(withAnswers, withFiles) {
      setIcon('saving');
      const kluc = hlavicka.getAttribute('kluc');
      const udaje = new FormData();
      udaje.append('predmet',  hlavicka.getAttribute('predmet'));
      udaje.append('trieda',   hlavicka.getAttribute('trieda'));
      udaje.append('skupina',  hlavicka.getAttribute('skupina'));
      udaje.append('kapitola', hlavicka.getAttribute('kapitola'));
      udaje.append('fileid',   hlavicka.getAttribute('fileid'));
      if (withAnswers) {
         document.querySelectorAll("#odpovede input[type='radio']:checked:not([form])").forEach(el => {
            udaje.append(el.name, el.value);
         });
         document.querySelectorAll("#odpovede input[type='text'].odpoved").forEach(el => {
            udaje.append(el.id, el.value);
         });
         const filesEl = document.getElementById('files');
         if (withFiles && filesEl) {
            Array.from(filesEl.files).forEach(file => udaje.append('subory', file));
         }
      }
      try {
         const resp = await fetch('/saveanswers/' + kluc, { method: 'POST', body: udaje });
         if (resp.ok) {
            setIcon('ok');
         } else {
            setIcon('error');
            if (resp.status === 403) zobrazNotifikaciu('Čas na odovzdanie odpovedí vypršal!');
            else if (resp.status === 500) zobrazNotifikaciu('Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.');
            else zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
         }
      } catch {
         setIcon('error');
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   }

   function scheduleAutosave() {
      clearTimeout(autosaveTimer);
      setIcon('unsaved');
      autosaveTimer = setTimeout(() => saveAnswers(true, false), 3000);
   }

   const saveStatus = document.getElementById('save-status');
   if (saveStatus) {
      saveStatus.addEventListener('click', (e) => {
         const btn = e.currentTarget;
         if (btn.dataset.disabled) return;
         btn.dataset.disabled = 'true';
         btn.classList.add('disabled');
         setTimeout(() => { delete btn.dataset.disabled; btn.classList.remove('disabled'); }, 10000);
         clearTimeout(autosaveTimer);
         saveAnswers(true, true);
      });
   }

   const odpovede = document.getElementById('odpovede');
   if (odpovede) {
      odpovede.addEventListener('change', (e) => {
         if (e.target.matches('input.odpoved')) scheduleAutosave();
      });
      odpovede.addEventListener('input', (e) => {
         if (e.target.matches("input[type='text'].odpoved")) scheduleAutosave();
      });
   }

   if (!window.location.pathname.includes('/admin'))
      saveAnswers(false, false);
});
