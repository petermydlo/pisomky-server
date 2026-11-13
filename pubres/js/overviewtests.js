document.addEventListener('DOMContentLoaded', () => {

   function skupinaData(el) {
      const skupinaDiv = el.closest('div.skupina');
      const skupinaRows = skupinaDiv.closest('[data-trieda]');
      return {
         predmet:  el.closest('.tab-pane.active').id,
         trieda:   skupinaRows.dataset.trieda,
         skupina:  skupinaRows.dataset.skupina,
         kapitola: skupinaDiv.querySelector('.kapitola').firstChild.textContent,
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
      else if (status === 409) zobrazNotifikaciu('Testy už majú odovzdané odpovede, nie je možné ich regenerovať!');
      else if (status === 500) zobrazNotifikaciu('Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.');
      else zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
   }

   //vykona zmenu tabu podla hash v URL
   function onHashChange() {
      const hash = window.location.hash;
      const tab = hash ? Array.from(document.querySelectorAll("div.nav [data-bs-toggle='tab']")).find(t => t.getAttribute('href') === hash) : null;
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

   //na chvilu zafarbi bunku (trieda cas-ok / cas-chyba)
   function zablikaj(cell, trieda) {
      cell.classList.add(trieda);
      setTimeout(() => cell.classList.remove(trieda), 1500);
   }

   //odosle zmenu casu na server
   async function odosliZmenuCasu(trigger, starypolicko, novy) {
      const data = skupinaData(trigger);
      if (trigger.matches('.startT, .stopT')) data.kluc = trigger.dataset.kluc;
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
            zablikaj(cell, 'cas-ok');
         } else {
            zablikaj(cell, 'cas-chyba');
            chybaNotifikaciu(resp.status);
         }
      } catch (err) {
         console.error('Chyba:', err);
         zablikaj(cell, 'cas-chyba');
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
      starypolicko.hidden = true;
      pen.hidden = true;
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
         starypolicko.hidden = false;
         pen.hidden = false;
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
   document.addEventListener('click', async (event) => {
      if (!event.target.closest('.del')) return;
      event.stopPropagation();
      event.preventDefault();
      const el = event.target.closest('.del');
      const data = skupinaData(el);
      const deleteEl = el.closest('div.skupina');
      const ikony = deleteEl.querySelector('.subory-ikony');
      const vyber = await vyberDialog({
         nadpis: 'Vymazať súbory',
         text: `Čo vymazať pre ${data.predmet}:${data.trieda}${data.skupina}:${data.kapitola}?`,
         moznosti: [
            {id: 'test', popis: 'Test', zapnute: true, aktivne: !!ikony.querySelector('.bi-journal-text')},
            {id: 'answers', popis: 'Odpovede (aj odovzdané súbory)', zapnute: true, aktivne: !!ikony.querySelector('.bi-pencil')},
            {id: 'feedback', popis: 'Feedback', zapnute: true, aktivne: !!ikony.querySelector('.bi-chat-right-text')},
         ],
         potvrdit: 'Vymazať',
         nebezpecne: true,
      });
      if (!vyber) return;
      const d = {
         ...data,
         del_test:     vyber.test ? '1' : '0',
         del_answers:  vyber.answers ? '1' : '0',
         del_feedback: vyber.feedback ? '1' : '0',
      };
      try {
         const resp = await fetch('/admin/deletetests', {
            method: 'DELETE',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(d)
         });
         if (resp.ok) {
            const tabPane = deleteEl.closest('.tab-pane');
            const bolPosledny = tabPane.querySelectorAll('div.skupina').length <= 1;

            if (bolPosledny) {
               parent.location.hash = await resp.text();
               location.reload();
            } else {
               const collapseGroup = deleteEl.closest('.collapse[data-trieda]');
               deleteEl.remove();
               //ak bol posledny v ramci trieda/skupina, zmaz aj prazdny toggle header
               if (collapseGroup && !collapseGroup.querySelector('div.skupina')) {
                  collapseGroup.previousElementSibling?.remove();
                  collapseGroup.remove();
               }
            }
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
      if (!event.target.closest('.feedback:not(.disabled)')) return;
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
      if (btn.classList.contains('caka')) return;   //PDF sa uz generuje
      btn.classList.add('caka');
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
      } finally {
         btn.classList.remove('caka');
      }
   });

   //regeneruje otazky v skupine testov (len ak nie su odpovede)
   document.addEventListener('click', async (event) => {
      const btn = event.target.closest('.regenerate:not(.disabled)');
      if (!btn) return;
      event.stopPropagation();
      event.preventDefault();
      const d = skupinaData(btn);
      if (!await potvrdDialog({nadpis: 'Regenerovať otázky', text: `Naozaj chcete regenerovať otázky pre ${d.predmet}:${d.trieda}${d.skupina}:${d.kapitola}?`, potvrdit: 'Regenerovať', nebezpecne: true})) return;
      try {
         const resp = await fetch('/admin/regeneratetests', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(d)
         });
         if (resp.ok) {
            const novyGendat = await resp.text();
            btn.closest('div.skupina').querySelector('.gendat').textContent = novyGendat;
         } else {
            chybaNotifikaciu(resp.status);
         }
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });

   //predgenerovanie AI napovedi: siva = ziadne, zlta = cast, zelena = vsetky (stav sa odvodzuje z cache na serveri)
   const NAPOVEDY_POLL_MS = 10000;
   const napovedyCasovace = new WeakMap();

   function napovedyStav(ikona, stav) {
      ikona.classList.remove('napovedy-ciastocne', 'napovedy-hotove', 'napovedy-bezi');
      if (stav.hotove > 0 && stav.hotove < stav.celkom) ikona.classList.add('napovedy-ciastocne');
      if (stav.celkom > 0 && stav.hotove === stav.celkom) ikona.classList.add('napovedy-hotove');
      if (stav.bezi) ikona.classList.add('napovedy-bezi');
      let text = `AI nápovedy: ${stav.hotove}/${stav.celkom} hotových`;
      if (stav.bezi) text += ' (generuje sa…)';
      else if (stav.hotove < stav.celkom) text += ' — kliknutím predgenerovať';
      ikona.title = text;
      naplanujKontrolu(ikona, stav.bezi);
   }

   function naplanujKontrolu(ikona, bezi) {
      clearTimeout(napovedyCasovace.get(ikona));
      if (bezi) napovedyCasovace.set(ikona, setTimeout(() => nacitajNapovedy(ikona), NAPOVEDY_POLL_MS));
   }

   async function nacitajNapovedy(ikona) {
      try {
         const resp = await fetch('/admin/napovedy/stav?' + new URLSearchParams(skupinaData(ikona)));
         if (resp.ok) napovedyStav(ikona, await resp.json());
         else {
            ikona.title = 'AI nápovedy: stav sa nepodarilo načítať';
            naplanujKontrolu(ikona, ikona.classList.contains('napovedy-bezi'));
         }
      } catch (err) {
         console.error('Chyba:', err);
         //prechodna chyba siete nesmie zastavit sledovanie bezacej ulohy
         naplanujKontrolu(ikona, ikona.classList.contains('napovedy-bezi'));
      }
   }

   //nacita stav postupne (po jednej sade), aby sa server nezahltil; len pre aktivnu kartu predmetu
   let napovedyNacitava = false;
   async function nacitajNapovedyKarty() {
      if (napovedyNacitava) return;
      napovedyNacitava = true;
      try {
         let ikona;
         while ((ikona = document.querySelector('.tab-pane.active .napovedy:not([data-nacitane])'))) {
            ikona.dataset.nacitane = '1';
            await nacitajNapovedy(ikona);
         }
      } finally {
         napovedyNacitava = false;
      }
   }

   document.addEventListener('shown.bs.tab', nacitajNapovedyKarty);

   //predgeneruje AI napovede pre vsetky otazky sady (kliknutie pocas behu len obnovi stav)
   document.addEventListener('click', async (event) => {
      const btn = event.target.closest('.napovedy');
      if (!btn) return;
      event.stopPropagation();
      event.preventDefault();
      if (btn.classList.contains('napovedy-bezi') || btn.classList.contains('napovedy-hotove')) {
         await nacitajNapovedy(btn);
         return;
      }
      const d = skupinaData(btn);
      if (!await potvrdDialog({nadpis: 'Predgenerovať AI nápovede', text: `Predgenerovať AI nápovede pre ${d.predmet}:${d.trieda}${d.skupina}:${d.kapitola}?\nGenerovanie trvá niekoľko minút a beží na pozadí; kým žiaci čakajú na nápovedu, pozastaví sa.`, potvrdit: 'Predgenerovať'})) return;
      try {
         const resp = await fetch('/admin/napovedy/pregeneruj', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(d)
         });
         if (resp.ok) napovedyStav(btn, await resp.json());
         else chybaNotifikaciu(resp.status);
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });

   //odhalenie spravnych odpovedi zakom: checkbox pri teste a hlavickovy checkbox sady
   function aktualizujHlavicku(kontajner) {
      const hlavicka = kontajner.querySelector('.odhalit-vsetky');
      if (!hlavicka) return;
      const boxy = [...kontajner.querySelectorAll('.odhalit-test:not(:disabled)')];
      const zaskrtnute = boxy.filter(b => b.checked).length;
      hlavicka.disabled = boxy.length === 0;
      hlavicka.checked = boxy.length > 0 && zaskrtnute === boxy.length;
      hlavicka.indeterminate = zaskrtnute > 0 && zaskrtnute < boxy.length;
   }

   //ikona oka v stlpci Trieda: je tam, ak je odhalený aspoň jeden test riadka
   function aktualizujOko(kontajner) {
      const ikony = kontajner.closest('.skupina')?.querySelector('.subory-ikony');
      if (!ikony) return;
      const maOdhalene = !!kontajner.querySelector('.odhalit-test:checked');
      let oko = ikony.querySelector('.bi-eye');
      if (maOdhalene && !oko) {
         oko = document.createElement('i');
         oko.className = 'bi bi-eye text-success';
         oko.title = 'Správne odpovede odhalené aspoň pri jednom teste';
         ikony.prepend(oko);
      } else if (!maOdhalene && oko) {
         oko.remove();
      }
   }

   document.addEventListener('change', async (event) => {
      const box = event.target.closest('.odhalit-test, .odhalit-vsetky');
      if (!box) return;
      const kontajner = box.closest('.collapse');
      const jeTest = box.classList.contains('odhalit-test');
      const data = {...skupinaData(box), odhalene: box.checked ? '1' : '0'};
      if (jeTest) data.kluc = box.value;
      try {
         const resp = await fetch('/admin/setrevealed', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams(data)
         });
         if (resp.ok) {
            if (!jeTest) kontajner.querySelectorAll('.odhalit-test:not(:disabled)').forEach(b => { b.checked = box.checked; });
         } else {
            if (jeTest) box.checked = !box.checked;
            if (resp.status === 409) zobrazNotifikaciu('Správne odpovede sa dajú odhaliť až po skončení testu!');
            else chybaNotifikaciu(resp.status);
         }
      } catch (err) {
         console.error('Chyba:', err);
         if (jeTest) box.checked = !box.checked;
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
      aktualizujHlavicku(kontajner);
      aktualizujOko(kontajner);
   });

   document.querySelectorAll('.odhalit-vsetky').forEach(h => aktualizujHlavicku(h.closest('.collapse')));

   window.addEventListener('hashchange', onHashChange, false);
   onHashChange();
   nacitajNapovedyKarty();
});
