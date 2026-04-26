document.addEventListener('DOMContentLoaded', () => {
   let autosaveTimer = null;
   const ikonClassy = ['bi-cloud-check', 'bi-cloud-upload', 'bi-cloud-slash', 'text-success', 'text-warning', 'text-primary', 'text-danger'];

   function setIcon(stav) {
      const icon = document.getElementById('save-icon');
      icon.classList.remove(...ikonClassy);
      if (stav === 'ok')           icon.classList.add('bi-cloud-check', 'text-success');
      else if (stav === 'saving')  icon.classList.add('bi-cloud-upload', 'text-primary');
      else if (stav === 'unsaved') icon.classList.add('bi-cloud-slash', 'text-warning');
      else if (stav === 'error')   icon.classList.add('bi-cloud-slash', 'text-danger');
   }

   async function saveAnswers(withAnswers, withFiles) {
      setIcon('saving');
      const hlavicka = document.getElementById('hlavicka');
      const kluc = hlavicka.getAttribute('kluc');
      const udaje = new FormData();
      udaje.append('predmet',  hlavicka.getAttribute('predmet'));
      udaje.append('trieda',   hlavicka.getAttribute('trieda'));
      udaje.append('skupina',  hlavicka.getAttribute('skupina'));
      udaje.append('kapitola', hlavicka.getAttribute('kapitola'));
      udaje.append('fileid',   hlavicka.getAttribute('fileid'));
      if (withAnswers) {
         document.querySelectorAll("#odpovede input[type='radio']:checked:not([form])").forEach(el => {
            udaje.append(el.getAttribute('name'), el.getAttribute('value'));
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

   document.getElementById('save-status').addEventListener('click', (e) => {
      const btn = e.currentTarget;
      if (btn.dataset.disabled) return;
      btn.dataset.disabled = 'true';
      btn.classList.add('disabled');
      setTimeout(() => { delete btn.dataset.disabled; btn.classList.remove('disabled'); }, 10000);
      clearTimeout(autosaveTimer);
      saveAnswers(true, true);
   });

   const odpovede = document.getElementById('odpovede');
   odpovede.addEventListener('change', (e) => {
      if (e.target.matches('input.odpoved')) scheduleAutosave();
   });
   odpovede.addEventListener('input', (e) => {
      if (e.target.matches("input[type='text'].odpoved")) scheduleAutosave();
   });

   if (!window.location.pathname.includes('/admin'))
      saveAnswers(false, false);
});
