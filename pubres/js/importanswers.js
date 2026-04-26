document.addEventListener('DOMContentLoaded', () => {

   const ODPOVEDE = ['a', 'b', 'c', 'd'];

   function el(tag, classes = '', text = '') {
      const e = document.createElement(tag);
      if (classes) e.className = classes;
      if (text) e.textContent = text;
      return e;
   }

   // nahladove obrazky pri vybere suborov
   document.getElementById('obrazky').addEventListener('change', function() {
      const files = this.files;
      const nahlady = document.getElementById('nahlady');
      nahlady.innerHTML = '';
      if (files.length > 0) {
         Array.from(files).forEach(file => {
            if (file.type === 'application/pdf') {
               const div = el('div', 'nahladPdf rounded d-flex flex-column align-items-center justify-content-center bg-light border');
               div.appendChild(el('div', 'nahladPdf-icon', '📄'));
               div.appendChild(el('div', 'nahladPdf-nazov', file.name));
               nahlady.appendChild(div);
            } else {
               const img = el('img', 'nahladImg rounded');
               img.src = URL.createObjectURL(file);
               nahlady.appendChild(img);
            }
         });
         document.getElementById('btnImport').disabled = false;
      } else {
         document.getElementById('btnImport').disabled = true;
      }
   });

   // import
   document.getElementById('btnImport').addEventListener('click', async () => {
      const files = document.getElementById('obrazky').files;
      if (!files.length) return;

      document.getElementById('uploadSekcia').classList.add('d-none');
      document.getElementById('priebehSekcia').classList.remove('d-none');
      document.getElementById('vysledkySekcia').classList.add('d-none');
      document.getElementById('vysledky').innerHTML = '';

      const formData = new FormData();
      Array.from(files).forEach(file => formData.append('obrazky', file));

      nastavPriebeh(0, `Spracovávam ${files.length} fotiek...`);

      try {
         const resp = await fetch('/admin/ai/importanswers', { method: 'POST', body: formData });
         if (resp.ok) {
            const data = await resp.json();
            nastavPriebeh(100, 'Hotovo.');
            zobrazVysledky(data.vysledky);
         } else {
            const data = await resp.json().catch(() => ({}));
            nastavPriebeh(100, 'Chyba!');
            zobrazVysledky([{chyba: data?.detail || 'Neznáma chyba'}]);
         }
      } catch {
         nastavPriebeh(100, 'Chyba!');
         zobrazVysledky([{chyba: 'Neznáma chyba'}]);
      }
   });

   function nastavPriebeh(pct, text) {
      document.getElementById('priebehText').textContent = text;
      const bar = document.getElementById('priebehBar');
      bar.style.width = pct + '%';
      bar.textContent = pct + '%';
   }

   function zobrazVysledky(vysledky) {
      document.getElementById('priebehSekcia').classList.add('d-none');
      document.getElementById('vysledkySekcia').classList.remove('d-none');

      const cont = document.getElementById('vysledky');
      cont.innerHTML = '';

      vysledky.forEach(v => {
         const blok = el('div', 'okraj mb-2');

         if (v.chyba) {
            blok.classList.add('bg-danger-subtle');
            blok.appendChild(el('div', 'hrubo', v.subor || 'Chyba'));
            blok.appendChild(el('div', '', v.chyba));
         } else {
            blok.classList.add(v.nejasnosti?.length > 0 ? 'bg-warning-subtle' : 'bg-success-subtle');
            blok.appendChild(el('div', 'hrubo',
               `${v.test_id} — ${v.predmet} ${v.trieda}${v.skupina} ${v.kapitola} — zapísané: ${v.zapisane}`
            ));

            if (v.nejasnosti?.length > 0) {
               blok.appendChild(el('div', 'hrubo mt-2', 'Nejasnosti — skontrolujte a potvrďte:'));
               v.nejasnosti.forEach(n => {
                  const riadok = el('div', 'd-flex align-items-center gap-2 mt-1');
                  riadok.appendChild(el('span', 'hrubo', n.id + ':'));
                  riadok.appendChild(el('span', '', n.znenie));
                  if (n.dovod) riadok.appendChild(el('span', 'text-muted', '(' + n.dovod + ')'));

                  const select = el('select', 'form-select form-select-sm w-auto');
                  const optEmpty = el('option', '', '—');
                  optEmpty.value = '';
                  select.appendChild(optEmpty);
                  ODPOVEDE.forEach(pism => {
                     const opt = el('option', '', pism);
                     opt.value = pism;
                     select.appendChild(opt);
                  });
                  select.dataset.testId = v.test_id;
                  select.dataset.otazkaId = n.id;
                  select.dataset.predmet = v.predmet;
                  select.dataset.trieda = v.trieda;
                  select.dataset.skupina = v.skupina;
                  select.dataset.kapitola = v.kapitola;
                  select.dataset.fileid = v.fileid;
                  riadok.appendChild(select);

                  const btn = el('button', 'btn btn-sm btn-outline-success', 'Uložiť');
                  btn.disabled = true;
                  select.addEventListener('change', () => { btn.disabled = !select.value; });
                  btn.addEventListener('click', () => {
                     ulozNejasnost(select.dataset.testId, select.dataset.otazkaId, select.value,
                        select.dataset.predmet, select.dataset.trieda, select.dataset.skupina,
                        select.dataset.kapitola, select.dataset.fileid, btn, riadok);
                  });
                  riadok.appendChild(btn);
                  blok.appendChild(riadok);
               });
            }
         }

         cont.appendChild(blok);
      });

      const btnNovy = el('button', 'btn btn-outline-info mt-2', 'Importovať ďalšie');
      btnNovy.addEventListener('click', () => {
         document.getElementById('obrazky').value = '';
         document.getElementById('nahlady').innerHTML = '';
         document.getElementById('btnImport').disabled = true;
         document.getElementById('vysledkySekcia').classList.add('d-none');
         document.getElementById('uploadSekcia').classList.remove('d-none');
      });
      cont.appendChild(btnNovy);
   }

   async function ulozNejasnost(testId, otazkaId, odpoved, predmet, trieda, skupina, kapitola, fileid, btn, riadok) {
      const data = new FormData();
      data.append('predmet', predmet);
      data.append('trieda', trieda);
      data.append('skupina', skupina);
      data.append('kapitola', kapitola);
      data.append('fileid', fileid);
      data.append(otazkaId, odpoved);

      try {
         const resp = await fetch('/admin/ai/importmanual/' + testId, { method: 'POST', body: data });
         if (resp.ok) {
            riadok.querySelectorAll('select, button').forEach(e => e.disabled = true);
            const ok = el('span', 'text-success hrubo', ' ✓');
            riadok.appendChild(ok);
         } else {
            const json = await resp.json().catch(() => ({}));
            zobrazNotifikaciu(json?.detail || 'Chyba pri ukladaní!');
         }
      } catch {
         zobrazNotifikaciu('Chyba pri ukladaní!');
      }
   }

});
