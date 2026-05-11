document.addEventListener('DOMContentLoaded', () => {

   function skupinaData(el) {
      const skupinaDiv = el.closest('div.skupina');
      const skupinaRows = skupinaDiv.closest('[data-trieda]');
      return {
         predmet:  el.closest('.tab-pane.active').id,
         trieda:   skupinaRows.dataset.trieda,
         skupina:  skupinaRows.dataset.skupina,
         kapitola: skupinaDiv.querySelector('#kapitola').firstChild.textContent,
         fileid:   skupinaDiv.dataset.fileid
      };
   }

   function odosliForm(action, data) {
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = action;
      Object.entries(data).forEach(([name, value]) => {
         const input = document.createElement('input');
         input.type = 'hidden';
         input.name = name;
         input.value = value;
         form.appendChild(input);
      });
      document.body.appendChild(form);
      form.submit();
   }

   function chybaNotifikaciu(status) {
      if (status === 404) zobrazNotifikaciu('Testy nenájdené!');
      else if (status === 403) zobrazNotifikaciu('Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!');
      else if (status === 500) zobrazNotifikaciu('Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.');
      else zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
   }

   //vykona zmenu tabu podla hash v URL
   function onHashChange() {
      const hash = window.location.hash;
      const tab = hash ? document.querySelector(`div.nav [data-bs-toggle='tab'][href='${hash}']`) : null;
      if (tab)
         bootstrap.Tab.getOrCreateInstance(tab).show();
      else {
         history.replaceState(null, '', window.location.pathname);
         const first = document.querySelector("div.nav [data-bs-toggle='tab']");
         if (first) bootstrap.Tab.getOrCreateInstance(first).show();
      }
   }

   //zmeni fragment pri vybrati tabu
   document.querySelectorAll("[data-bs-toggle='tab']").forEach(tab => {
      tab.addEventListener('click', () => { parent.location.hash = tab.getAttribute('href'); });
   });

   //validuje format YYYY-MM-DDTHH:MM
   function jeValidnyCas(val) {
      return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(val.trim());
   }

   //odosle zmenu casu na server
   async function odosliZmenuCasu(trigger, starypolicko, novy) {
      const data = skupinaData(trigger);
      if (trigger.matches('.startT, .stopT')) data.kluc = trigger.id;
      if (trigger.matches('.startS, .startT')) data.start = novy;
      else data.stop = novy;

      const cell = starypolicko.closest('div');
      try {
         const resp = await fetch('/admin/changetime', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(data)
         });
         if (resp.ok) {
            starypolicko.textContent = novy;
            cell.style.backgroundColor = 'rgba(var(--bs-success-rgb), 0.5)';
            setTimeout(() => { cell.style.backgroundColor = ''; }, 1500);
         } else {
            cell.style.backgroundColor = 'rgba(var(--bs-danger-rgb), 0.5)';
            setTimeout(() => { cell.style.backgroundColor = ''; }, 1500);
            chybaNotifikaciu(resp.status);
         }
      } catch (err) {
         console.error('Chyba:', err);
         cell.style.backgroundColor = 'rgba(var(--bs-danger-rgb), 0.5)';
         setTimeout(() => { cell.style.backgroundColor = ''; }, 1500);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   }

   //zmeni cas skupiny testov alebo jedneho testu
   document.addEventListener('click', (event) => {
      const pen = event.target.closest('.startS, .stopS, .startT, .stopT');
      if (!pen) return;
      event.stopPropagation();
      event.preventDefault();

      //zatvorime vsetky ostatne otvorene inputy
      document.querySelectorAll('.casInput').forEach(el => { if (el._zavriet) el._zavriet(); });

      const parentDiv = pen.parentElement;
      if (parentDiv.querySelector('.casInput')) return;

      const starypolicko = pen.previousElementSibling;
      const stary = starypolicko.textContent.trim();
      const predvyplneny = event.ctrlKey ? terazFormatovany() : stary;

      //vytvorime inline input s potvrdenim a zrusenim
      const input = document.createElement('input');
      input.className = 'casInput';
      input.type = 'text';
      input.title = 'Formát: YYYY-MM-DDTHH:MM';
      input.value = predvyplneny;

      const btns = document.createElement('div');
      btns.className = 'casBtns';
      const btnOk  = document.createElement('span');
      btnOk.className = 'casBtn casBtn-ok'; btnOk.title = 'Potvrdiť'; btnOk.innerHTML = '✔';
      const btnDel = document.createElement('span');
      btnDel.className = 'casBtn casBtn-del'; btnDel.title = 'Vymazať čas'; btnDel.innerHTML = '🗑';
      const btnX   = document.createElement('span');
      btnX.className = 'casBtn casBtn-cancel'; btnX.title = 'Zrušiť'; btnX.innerHTML = '✖';
      btns.append(btnOk, btnDel, btnX);

      //skryjeme stary text a pero
      starypolicko.style.display = 'none';
      pen.style.display = 'none';
      parentDiv.append(input, btns);
      input.focus(); input.select();

      //docasne vypneme collapse na rodicovskom div
      const collapseTarget = parentDiv.closest("[data-bs-toggle='collapse']");
      if (collapseTarget) {
         collapseTarget.dataset.bsToggleDisabled = collapseTarget.getAttribute('data-bs-toggle');
         collapseTarget.removeAttribute('data-bs-toggle');
      }

      function zavriet() {
         input.remove(); btns.remove();
         starypolicko.style.display = '';
         pen.style.display = '';
         if (collapseTarget) {
            collapseTarget.setAttribute('data-bs-toggle', collapseTarget.dataset.bsToggleDisabled);
            delete collapseTarget.dataset.bsToggleDisabled;
         }
      }

      input._zavriet = zavriet;

      function potvrdit() {
         const novy = input.value.trim();
         if (novy === stary) { zavriet(); return; }
         if (novy !== '' && !jeValidnyCas(novy)) {
            input.classList.add('is-invalid');
            input.title = 'Neplatný formát. Použite YYYY-MM-DDTHH:MM';
            return;
         }
         zavriet();
         odosliZmenuCasu(pen, starypolicko, novy);
      }

      btnOk.addEventListener('click',  (e) => { e.stopPropagation(); potvrdit(); });
      btnDel.addEventListener('click', (e) => { e.stopPropagation(); zavriet(); odosliZmenuCasu(pen, starypolicko, ' '); });
      btnX.addEventListener('click',   (e) => { e.stopPropagation(); zavriet(); });

      input.addEventListener('keydown', (e) => {
         if (e.key === 'Enter')  { e.stopPropagation(); potvrdit(); }
         if (e.key === 'Escape') { e.stopPropagation(); zavriet(); }
      });
   });

   //odhlasi uzivatela a presmeruje na uvodnu obrazovku
   document.addEventListener('click', (event) => {
      if (!event.target.closest('.autor')) return;
      event.stopPropagation();
      event.preventDefault();
      fetch('/admin', { headers: {'Authorization': 'Basic xxx'}, credentials: 'omit' })
         .then(resp => {
            if (resp.ok) zobrazNotifikaciu('Na odhlásenie, prosím, zatvorte toto okno prezerača.', 'info', 'Informácia');
            else window.location = '/';
         })
         .catch(() => { window.location = '/'; });
   });

   //vymaze skupinu testov
   let _deleteData = null;
   document.addEventListener('click', (event) => {
      if (!event.target.closest('.del')) return;
      event.stopPropagation();
      event.preventDefault();
      const el = event.target.closest('.del');
      _deleteData = skupinaData(el);
      document.getElementById('deleteModalDesc').textContent =
         `Čo vymazať pre ${_deleteData.predmet}:${_deleteData.trieda}${_deleteData.skupina}:${_deleteData.kapitola}?`;
      const ikony = el.closest('div.skupina').querySelector('.subory-ikony');
      const maTest     = !!ikony.querySelector('.bi-journal-text');
      const maAnswers  = !!ikony.querySelector('.bi-pencil');
      const maFeedback = !!ikony.querySelector('.bi-chat-right-text');
      for (const [id, exists] of [['delTest', maTest], ['delAnswers', maAnswers], ['delFeedback', maFeedback]]) {
         const chk = document.getElementById(id);
         chk.checked  = exists;
         chk.disabled = !exists;
      }
      bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal')).show();
   });

   document.getElementById('deleteModalConfirm').addEventListener('click', async () => {
      const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('deleteModal'));
      modal.hide();
      if (!_deleteData) return;
      const d = {
         ..._deleteData,
         del_test:     document.getElementById('delTest').checked     ? '1' : '0',
         del_answers:  document.getElementById('delAnswers').checked  ? '1' : '0',
         del_feedback: document.getElementById('delFeedback').checked ? '1' : '0',
      };
      _deleteData = null;
      try {
         const resp = await fetch('/admin/deletetests', {
            method: 'DELETE',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(d)
         });
         if (resp.ok) {
            parent.location.hash = await resp.text();
            location.reload();
         } else {
            chybaNotifikaciu(resp.status);
         }
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });

   //zobrazi statistiku pre skupinu testov
   document.addEventListener('click', (event) => {
      if (!event.target.closest('.groupstatistics')) return;
      event.stopPropagation();
      event.preventDefault();
      odosliForm('/admin/groupstatistics', skupinaData(event.target.closest('.groupstatistics')));
   });

   //zobrazi feedback report pre skupinu testov
   document.addEventListener('click', (event) => {
      if (!event.target.closest('.feedback')) return;
      event.stopPropagation();
      event.preventDefault();
      odosliForm('/admin/feedbackreport', skupinaData(event.target.closest('.feedback')));
   });

   //vytlaci skupinu kodov, testov alebo rieseni
   document.addEventListener('click', async (event) => {
      const btn = event.target.closest('.codes, .tests, .results');
      if (!btn) return;
      event.stopPropagation();
      event.preventDefault();
      const d = skupinaData(btn);
      const url = btn.classList.contains('results') ? '/admin/downloadresults'
                : btn.classList.contains('tests')   ? '/admin/downloadtests'
                : '/admin/downloadcodes';
      try {
         const resp = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(d)
         });
         if (resp.ok) {
            const blob = await resp.blob();
            const disposition = resp.headers.get('Content-Disposition') || '';
            let filename = '';
            const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
            if (match?.[1]) filename = match[1].replace(/['"]/g, '');
            const link = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = link; a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(link);
         } else {
            chybaNotifikaciu(resp.status);
         }
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });

   //regeneruje otazky v skupine testov (len ak nie su odpovede)
   document.addEventListener('click', (event) => {
      const btn = event.target.closest('.regenerate:not(.disabled)');
      if (!btn) return;
      event.stopPropagation();
      event.preventDefault();
      const d = skupinaData(btn);
      if (!confirm(`Naozaj chcete regenerovať otázky pre ${d.predmet}:${d.trieda}${d.skupina}:${d.kapitola}?`)) return;
      odosliForm('/admin/regeneratetests', d);
   });

   window.addEventListener('hashchange', onHashChange, false);
   onHashChange();
});
