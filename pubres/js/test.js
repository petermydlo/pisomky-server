document.addEventListener('DOMContentLoaded', () => {
   const hlavicka = document.getElementById('hlavicka');
   const klucTestu = hlavicka.getAttribute('kluc');
   const token = hlavicka.getAttribute('token') || '';
   const PING_INTERVAL = 15000;

   //prenajom testu (relacie.py): ping drzi prenajom, pri zatvoreni stranky sa uvolni; ak ho prevzal iny, server odpoveda 423
   let pingTimer = null;
   let prenajomStraceny = false;
   function prenajomPrevzaty() {
      if (prenajomStraceny) return;
      prenajomStraceny = true;
      clearInterval(pingTimer);
      oznamDialog({nadpis: 'Test je otvorený inde', text: 'Tento test sa otvoril na inom mieste, preto sa odpovede z tejto stránky už neuložia. Zostanú tu zobrazené; otvorte test znovu až keď ho inde zatvoríte.'});
   }
   if (token) {
      pingTimer = setInterval(() => {
         fetch('/ping/' + klucTestu, { method: 'POST', body: new URLSearchParams({ token }) })
            .then(resp => { if (resp.status === 423) prenajomPrevzaty(); })
            .catch(() => {});
      }, PING_INTERVAL);
      window.addEventListener('pagehide', () => navigator.sendBeacon('/uvolni/' + klucTestu, new URLSearchParams({ token })));
   }

   // Odkazy a.okno-odkaz sa otvoria v samostatnom okne (rovnake meno = jedno okno); bez JS ostava nova karta
   document.querySelectorAll('a.okno-odkaz').forEach(a => {
      a.addEventListener('click', (e) => {
         const okno = window.open(a.href, 'okno-odkaz', 'popup=yes,width=880,height=380,resizable=yes');
         if (okno) {
            e.preventDefault();
            okno.focus();
         }
      });
   });

   // Rating hviezdicky - postupne rozsvecovanie
   document.querySelectorAll('.rating-wrap').forEach(wrap => {
      const stars = wrap.querySelectorAll('.rating-star');
      const radios = Array.from(wrap.querySelectorAll('input[type=radio]'));
      //prve radio je skryte "-" (nezodpovedane); hviezdy pred vybranym radiom svietia
      function rozsvietHviezdy(radio) {
         const idx = radios.indexOf(radio);
         stars.forEach((star, j) => {
            star.classList.toggle('rating-zapnuta', j < idx);
            star.classList.toggle('rating-vypnuta', j >= idx);
         });
      }
      radios.forEach(radio => radio.addEventListener('change', () => rozsvietHviezdy(radio)));
      const vybrane = radios.find(r => r.checked);
      if (vybrane && radios.indexOf(vybrane) > 0) rozsvietHviezdy(vybrane);
   });

   // Zelená fajka pri otázke s vybranou odpoveďou (skryté radio "-" = nezodpovedané)
   document.querySelectorAll('.odpovedane').forEach(fajka => {
      const otazka = fajka.closest('.flex-container-table-otazka');
      const radia = otazka.querySelectorAll('input[type=radio].odpoved');
      radia.forEach(radio => {
         radio.addEventListener('change', () => {
            fajka.classList.toggle('skryte', !Array.from(radia).some(r => r.checked));
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
         btn.classList.add('caka');

         poziadajAINapovedu(otazkaId, testId).finally(() => btn.classList.remove('caka'));

         document.querySelectorAll('#toastFeedback .feedback-btn').forEach(el => {
            el.dataset.testId = testId;
         });
      });
   });

   //ukonci rozpracovanu napovedu, nova ju nahradi (server zrusi generovanie, ak este nezacalo)
   let ukonciPredchadzajucu = null;

   //odosle otazku na AI a zobrazi odpoved cez SSE streaming
   function poziadajAINapovedu(otazkaId, testId) {
      if (ukonciPredchadzajucu) ukonciPredchadzajucu();
      const toast = zabezpecToastKontajner('warning', 'AI Help (experimental)');
      const toastMessage = document.getElementById('toastMessage');
      const toastFeedback = document.getElementById('toastFeedback');
      toastMessage.innerHTML = '<strong>AI is thinking...</strong>';
      toastFeedback.classList.add('d-none');
      toastFeedback.classList.remove('d-flex');
      toast.show();
      const toastEl = document.getElementById('liveToast');

      return new Promise((resolve) => {
         const params = new URLSearchParams({ test_id: testId, otazka_id: otazkaId, token });
         const es = new EventSource(`/ai/napoveda?${params.toString()}`);
         let hintText = '';
         let completed = false;

         ukonciPredchadzajucu = () => {
            if (completed) return;
            completed = true;
            es.close();
            resolve();
         };

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

         es.addEventListener('caka', (e) => {
            const data = JSON.parse(e.data);
            toastMessage.textContent = `AI je vyťažená, čakám na odpoveď… (${data.sekundy} s)`;
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

         es.addEventListener('napoveda_obsadena', () => {
            completed = true;
            toastMessage.textContent = 'Predchádzajúca nápoveda sa ešte spracúva, skús to o chvíľu.';
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
      let hlaska = 'Po ukončení už písomku nebudete môcť znova otvoriť.';
      if (params.has('edit'))
         hlaska = 'Neodoslané zmeny sa zahodia a písomku už nebudete môcť znova otvoriť.';
      if (!await potvrdDialog({nadpis: 'Ukončiť písomku?', text: hlaska, potvrdit: 'Ukončiť písomku', zrusit: 'Späť k písomke', nebezpecne: true})) return;
      const kluc = hlavicka.getAttribute('kluc');
      const data = new URLSearchParams({
         token,
         predmet:  hlavicka.getAttribute('predmet'),
         trieda:   hlavicka.getAttribute('trieda'),
         skupina:  hlavicka.getAttribute('skupina'),
         kapitola: hlavicka.getAttribute('kapitola'),
         fileid:   hlavicka.getAttribute('fileid')
      });
      try {
         const resp = await fetch('/stoptime/' + kluc, { method: 'POST', body: data,
            headers: {'Content-Type': 'application/x-www-form-urlencoded'} });
         if (!resp.ok) {
            if (resp.status === 423) prenajomPrevzaty();
            else if (resp.status === 404) zobrazNotifikaciu('Test nenájdený!');
            else if (resp.status === 403) zobrazNotifikaciu('Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!');
            else if (resp.status === 500) zobrazNotifikaciu('Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.');
            else zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
            return;
         }
         window.location.href = '/' + kluc;
      } catch (err) {
         console.error('Chyba:', err);
         zobrazNotifikaciu('Vyskytla sa chyba! Skúste to prosím neskôr.');
      }
   });

   let autosaveTimer = null;
   let suborCaka = false;
   const filesInput = document.getElementById('files');
   const ikonClassy = ['bi-cloud-check', 'bi-cloud-upload', 'bi-cloud-slash', 'bi-cloud-arrow-up', 'text-success', 'text-warning', 'text-primary', 'text-danger'];

   function setIcon(stav) {
      const icon = document.getElementById('save-icon');
      if (!icon) return;
      icon.classList.remove(...ikonClassy);
      if (stav === 'ok')           icon.classList.add('bi-cloud-check', 'text-success');
      else if (stav === 'saving')  icon.classList.add('bi-cloud-upload', 'text-primary');
      else if (stav === 'unsaved') icon.classList.add(suborCaka ? 'bi-cloud-arrow-up' : 'bi-cloud-slash', 'text-warning');
      else if (stav === 'error')   icon.classList.add('bi-cloud-slash', 'text-danger');
   }

   //naraz bezi najviac jedno ulozenie, aby pomalsie starsie nepredbehlo a neprepisalo novsie; ulozenie vyziadane pocas behu
   //sa spusti po jeho skonceni (a zozbiera aktualny stav formulara)
   let ukladaSa = false;
   let cakajuceUkladanie = null;
   async function saveAnswers(withAnswers, withFiles) {
      if (ukladaSa) {
         cakajuceUkladanie = {
            withAnswers: withAnswers || !!cakajuceUkladanie?.withAnswers,
            withFiles: withFiles || !!cakajuceUkladanie?.withFiles
         };
         return;
      }
      ukladaSa = true;
      try {
         await odosliOdpovede(withAnswers, withFiles);
      } finally {
         ukladaSa = false;
         if (cakajuceUkladanie) {
            const dalsie = cakajuceUkladanie;
            cakajuceUkladanie = null;
            saveAnswers(dalsie.withAnswers, dalsie.withFiles);
         }
      }
   }

   async function odosliOdpovede(withAnswers, withFiles) {
      setIcon('saving');
      const kluc = hlavicka.getAttribute('kluc');
      const udaje = new FormData();
      let odoslaneSubory = [];
      udaje.append('predmet',  hlavicka.getAttribute('predmet'));
      udaje.append('trieda',   hlavicka.getAttribute('trieda'));
      udaje.append('skupina',  hlavicka.getAttribute('skupina'));
      udaje.append('kapitola', hlavicka.getAttribute('kapitola'));
      udaje.append('fileid',   hlavicka.getAttribute('fileid'));
      udaje.append('token', token);
      if (withAnswers) {
         document.querySelectorAll("#odpovede input[type='radio']:checked:not([form])").forEach(el => {
            udaje.append(el.name, el.value);
         });
         document.querySelectorAll("#odpovede input[type='text'].odpoved").forEach(el => {
            udaje.append(el.id, el.value);
         });
         if (withFiles && filesInput) {
            odoslaneSubory = Array.from(filesInput.files);
            odoslaneSubory.forEach(file => udaje.append('subory', file));
         }
      }
      try {
         const resp = await fetch('/saveanswers/' + kluc, { method: 'POST', body: udaje });
         if (resp.ok) {
            //odoslane subory zmiznu z vyberu, ostanu len tie vybrate pocas odosielania
            const kluceSuboru = odoslaneSubory.map(f => `${f.name}|${f.size}|${f.lastModified}`);
            if (odoslaneSubory.length) nastavSubory(Array.from(filesInput.files).filter(f => !kluceSuboru.includes(`${f.name}|${f.size}|${f.lastModified}`)));
            setIcon(suborCaka ? 'unsaved' : 'ok');
         } else {
            setIcon('error');
            if (resp.status === 423) prenajomPrevzaty();
            else if (resp.status === 403) zobrazNotifikaciu('Čas na odovzdanie odpovedí vypršal!');
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

   //vybraty, ale este neodoslany subor; zoznam vybratych suborov pod ikonou s moznostou odstranenia
   function vykresliSubory() {
      const zoznam = document.getElementById('files-zoznam');
      if (!zoznam) return;
      zoznam.replaceChildren(...Array.from(filesInput.files).map((file, i) => {
         const li = document.createElement('li');
         const nazov = document.createElement('span');
         nazov.textContent = file.name;
         nazov.title = file.name;
         const odstran = document.createElement('button');
         odstran.type = 'button';
         odstran.title = 'Odstrániť zo zoznamu';
         odstran.innerHTML = '<i class="bi bi-x"></i>';
         odstran.addEventListener('click', () => {
            nastavSubory(Array.from(filesInput.files).filter((_, j) => j !== i));
            if (!suborCaka) scheduleAutosave();
         });
         li.append(nazov, odstran);
         return li;
      }));
      zoznam.hidden = filesInput.files.length === 0;
   }

   function nastavSubory(subory) {
      const dt = new DataTransfer();
      subory.forEach(file => dt.items.add(file));
      filesInput.files = dt.files;
      zmenaSuborov();
   }

   function zmenaSuborov() {
      suborCaka = filesInput.files.length > 0;
      vykresliSubory();
      if (suborCaka) setIcon('unsaved');
   }

   if (filesInput) {
      filesInput.addEventListener('change', () => {
         zmenaSuborov();
         //po vyprazdneni vyberu autosave vrati ikonu do skutocneho stavu odpovedi
         if (!suborCaka) scheduleAutosave();
      });
   }

   //tabulka: polia sa skladaju do jedneho skryteho pola otazky (hodnoty oddelene "|"), ktore sa odosiela ako ostatne odpovede
   function zlozTabulku(bunka) {
      const povolene = bunka.dataset.povolene;
      if (povolene) bunka.value = Array.from(bunka.value).filter(z => povolene.includes(z)).join('');
      bunka.value = bunka.value.replaceAll('|', '');
      const tabulka = bunka.closest('table.tabulka');
      const skryte = tabulka.parentElement.querySelector('input.tabulka-hodnota');
      skryte.value = Array.from(tabulka.querySelectorAll('input.bunka-vstup')).map(el => el.value.trim()).join('|');
      skryte.dispatchEvent(new Event('input', { bubbles: true }));
   }

   const odpovede = document.getElementById('odpovede');
   if (odpovede) {
      odpovede.addEventListener('input', (e) => {
         if (e.target.matches('input.bunka-vstup')) zlozTabulku(e.target);
      });
      //oznacena hodnota sa po napisani prepise, nepripisuje sa k nej
      odpovede.addEventListener('focusin', (e) => {
         if (e.target.matches('input.bunka-vstup')) e.target.select();
      });
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
