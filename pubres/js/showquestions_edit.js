function getJson(url) {
   return fetch(url).then(resp => {
      if (!resp.ok) throw new Error('Požiadavka zlyhala');
      return resp.json();
   });
}

//Odosle formular (POST) a pri chybe ukaze spravu priamo vo formulari, ktory ostane otvoreny
function odosliFormular(form, url, params) {
   const chyba = form.querySelector('.dialog-chyba');
   chyba.textContent = '';
   return postForm(url, params)
      .then(() => reloadZachovajKapitolu())
      .catch(err => {
         chyba.textContent = err.message;
         chyba.scrollIntoView({block: 'nearest'});
      });
}

function reloadZachovajKapitolu() {
   const aktivna = document.querySelector('.tab-pane.active');
   if (aktivna) {
      location.hash = aktivna.id;
   }
   location.reload();
}

function confirmZmazanie(typ, id, nazov) {
   return getJson(`/admin/is_used?id=${encodeURIComponent(id)}&typ=${typ}`).then(data => {
      const text = data.used
         ? `${nazov} je použitá v teste — bude len archivovaná, pokračovať?`
         : `Naozaj zmazať ${nazov}?`;
      return potvrdDialog({nadpis: 'Zmazať', text, potvrdit: data.used ? 'Archivovať' : 'Zmazať', nebezpecne: true});
   });
}

// --- kapitola ---

function pridajKapitolu(predmet) {
   otvorDialog({
      nadpis: `Nová kapitola (${predmet})`,
      polia: [
         {id: 'kapitola_id', popis: 'ID kapitoly', povinne: true, vzor: /^[A-Za-z0-9_.-]+$/, chyba: 'ID smie obsahovať len písmená, číslice, _, - a bodku.', pomocka: 'napr. 05 alebo 02.5'},
         {id: 'nazov', popis: 'Názov (voliteľné)'},
      ],
      potvrdit: 'Vytvoriť',
      ulozit: ({kapitola_id, nazov}) => postForm('/admin/process_chapter', {predmet, kapitola_id, operacia: 'create', nazov})
         .then(() => reloadZachovajKapitolu()),
   });
}

function upravKapitolu(predmet, kapitolaId, nazov) {
   otvorDialog({
      nadpis: `Upraviť kapitolu ${kapitolaId}`,
      polia: [{id: 'nazov', popis: 'Názov kapitoly', hodnota: nazov}],
      potvrdit: 'Uložiť',
      ulozit: ({nazov}) => postForm('/admin/process_chapter', {predmet, kapitola_id: kapitolaId, operacia: 'update', nazov})
         .then(() => reloadZachovajKapitolu()),
   });
}

function zmazKapitolu(predmet, kapitolaId) {
   potvrdDialog({nadpis: 'Zmazať kapitolu', text: `Naozaj zmazať kapitolu ${kapitolaId}?`, potvrdit: 'Zmazať', nebezpecne: true}).then(potvrdene => {
      if (!potvrdene) return;
      postForm('/admin/process_chapter', {predmet, kapitola_id: kapitolaId, operacia: 'delete'})
         .then(() => reloadZachovajKapitolu())
         .catch(err => oznamDialog({text: err.message}));
   });
}

// --- kategória ---

function vytvorFormularKategorie(data) {
   data = data || {};
   const form = document.createElement('form');
   form.className = 'otazka-formular kat-formular';
   form.innerHTML = `
      <label>Názov (voliteľné, inak sa zobrazuje id)
         <input type="text" class="kat-nazov"/>
      </label>
      <div class="otazka-atributy-riadok">
         <label>Počet otázok na výber <input type="number" class="kat-pocet" min="0"/></label>
         <label>Body <input type="number" class="kat-body" min="0" step="any"/></label>
         <label><input type="checkbox" class="kat-static"/> statická</label>
         <label><input type="checkbox" class="kat-bonus"/> bonusová</label>
         <label class="deprecated-checkbox"><input type="checkbox" class="kat-deprecated"/> deprecated</label>
      </div>
      <div class="dialog-chyba"></div>
      <button type="button" class="kat-uloz">Uložiť</button>
      <button type="button" class="kat-zrus">Zrušiť</button>
   `;
   form.querySelector('.kat-nazov').value = data.nazov || '';
   form.querySelector('.kat-pocet').value = data.pocet || '';
   form.querySelector('.kat-body').value = data.body || '';
   form.querySelector('.kat-static').checked = data.static === '1';
   form.querySelector('.kat-bonus').checked = data.bonus === '1';
   form.querySelector('.kat-deprecated').checked = data.deprecated === '1';
   return form;
}

function pridajKategoriu(predmet) {
   const aktivnaKapitola = document.querySelector('.tab-pane.active');
   if (!aktivnaKapitola) {
      oznamDialog({text: 'Najprv vyber kapitolu.'});
      return;
   }
   const kapitolaId = aktivnaKapitola.id;
   const cielovyKontajner = aktivnaKapitola.querySelector('.flex-container-table');
   if (!cielovyKontajner || cielovyKontajner.querySelector('.kat-formular')) return;
   const form = vytvorFormularKategorie({});
   cielovyKontajner.insertAdjacentElement('afterbegin', form);
   form.querySelector('.kat-zrus').addEventListener('click', () => form.remove());
   form.querySelector('.kat-uloz').addEventListener('click', () => {
      const pocet = form.querySelector('.kat-pocet').value;
      if (!pocet) {
         form.querySelector('.dialog-chyba').textContent = 'Počet otázok na výber je povinný.';
         return;
      }
      const params = {
         predmet, kapitola_id: kapitolaId, operacia: 'create',
         pocet,
         body: form.querySelector('.kat-body').value,
         static: form.querySelector('.kat-static').checked ? '1' : '',
         bonus: form.querySelector('.kat-bonus').checked ? '1' : '',
         nazov: form.querySelector('.kat-nazov').value,
         deprecated: form.querySelector('.kat-deprecated').checked ? '1' : '',
      };
      odosliFormular(form, '/admin/process_category', params);
   });
}

function upravKategoriu(predmet, kategoriaId) {
   const icon = document.querySelector(`.editKategoriaIcon[data-id="${kategoriaId}"]`);
   const pauseRow = icon ? icon.closest('.pause-row') : null;
   if (!pauseRow) return;
   if (pauseRow.nextElementSibling && pauseRow.nextElementSibling.classList.contains('kat-formular')) return;
   getJson(`/admin/category?id=${encodeURIComponent(kategoriaId)}`).then(data => {
      const form = vytvorFormularKategorie(data);
      pauseRow.insertAdjacentElement('afterend', form);
      form.querySelector('.kat-zrus').addEventListener('click', () => form.remove());
      form.querySelector('.kat-uloz').addEventListener('click', () => {
         const params = {
            predmet, kategoria_id: kategoriaId, operacia: 'update',
            pocet: form.querySelector('.kat-pocet').value,
            body: form.querySelector('.kat-body').value,
            static: form.querySelector('.kat-static').checked ? '1' : '',
            bonus: form.querySelector('.kat-bonus').checked ? '1' : '',
            nazov: form.querySelector('.kat-nazov').value,
            deprecated: form.querySelector('.kat-deprecated').checked ? '1' : '',
         };
         odosliFormular(form, '/admin/process_category', params);
      });
   }).catch(err => oznamDialog({text: err.message}));
}

function zmazKategoriu(predmet, kategoriaId, nazov) {
   confirmZmazanie('kategoria', kategoriaId, nazov).then(potvrdene => {
      if (!potvrdene) return;
      postForm('/admin/process_category', {predmet, kategoria_id: kategoriaId, operacia: 'delete'})
         .then(() => reloadZachovajKapitolu())
         .catch(err => oznamDialog({text: err.message}));
   });
}

function obnovKategoriu(predmet, kategoriaId) {
   postForm('/admin/process_category', {predmet, kategoria_id: kategoriaId, operacia: 'restore'})
      .then(() => reloadZachovajKapitolu())
      .catch(err => oznamDialog({text: err.message}));
}

// --- otázka: dynamický formulár ---

function riadokOdpoved(odp) {
   odp = odp || {text: '', spravna: '0', napovedy: []};
   const div = document.createElement('fieldset');
   div.className = 'odpoved-riadok';
   div.innerHTML = `
      <legend>Odpoveď</legend>
      <i class="bi bi-trash odp-odstran" title="Odstrániť odpoveď"></i>
      <label>Text odpovede (môže obsahovať &lt;bold&gt;/&lt;italic&gt;/&lt;underline&gt;)
         <textarea class="odp-text" rows="2"></textarea>
      </label>
      <label><input type="checkbox" class="odp-spravna"/> správna</label>
      <div class="odp-napovedy"></div>
      <button type="button" class="odp-pridaj-napovedu">+ nápoveda k tejto odpovedi</button>
   `;
   div.querySelector('.odp-text').value = odp.text;
   div.querySelector('.odp-spravna').checked = odp.spravna === '1';
   const napovedyWrap = div.querySelector('.odp-napovedy');
   (odp.napovedy || []).forEach(text => napovedyWrap.appendChild(riadokNapoveda(text)));
   div.querySelector('.odp-odstran').addEventListener('click', () => div.remove());
   div.querySelector('.odp-pridaj-napovedu').addEventListener('click', () => napovedyWrap.appendChild(riadokNapoveda('')));
   aktualizujViditelnostNapovedi(div);
   div.querySelector('.odp-spravna').addEventListener('change', () => aktualizujViditelnostNapovedi(div));
   return div;
}

function aktualizujViditelnostNapovedi(riadokOdp) {
   const spravna = riadokOdp.querySelector('.odp-spravna').checked;
   riadokOdp.querySelector('.odp-napovedy').style.display = spravna ? '' : 'none';
   riadokOdp.querySelector('.odp-pridaj-napovedu').style.display = spravna ? '' : 'none';
}

function riadokNapoveda(text) {
   const div = document.createElement('div');
   div.className = 'napoveda-riadok';
   div.innerHTML = `<textarea class="napoveda-text" rows="1"></textarea><button type="button" class="napoveda-odstran">×</button>`;
   div.querySelector('.napoveda-text').value = text || '';
   div.querySelector('.napoveda-odstran').addEventListener('click', () => div.remove());
   return div;
}

function riadokVzor(text) {
   const div = document.createElement('div');
   div.className = 'napoveda-riadok';
   div.innerHTML = `<textarea class="vzor-text" rows="2"></textarea><button type="button" class="napoveda-odstran">×</button>`;
   div.querySelector('.vzor-text').value = text || '';
   div.querySelector('.napoveda-odstran').addEventListener('click', () => div.remove());
   return div;
}

function zostavVzory(form) {
   return Array.from(form.querySelectorAll('.vzor-text')).map(t => t.value).filter(t => t.trim() !== '');
}

function zostavOdpovede(form) {
   return Array.from(form.querySelectorAll('.odp-text')).map((textEl, i) => {
      const riadok = textEl.closest('.odpoved-riadok');
      const spravna = riadok.querySelector('.odp-spravna').checked ? '1' : '0';
      const napovedy = Array.from(riadok.querySelectorAll('.napoveda-text')).map(t => t.value).filter(t => t.trim() !== '');
      return {text: textEl.value, spravna, napovedy};
   });
}

function zostavCeloplosneNapovede(form) {
   return Array.from(form.querySelectorAll('.otazka-napovedy .napoveda-text')).map(t => t.value).filter(t => t.trim() !== '');
}

const SABLONA_TABULKY = `<tabulka povolene="">
   <hlavicka>
      <bunka></bunka>
   </hlavicka>
   <riadok>
      <bunka></bunka>
   </riadok>
</tabulka>`;

//XML tabulky, alebo prazdny retazec (odstrani tabulku z otazky); text v textarei ostava aj po odskrtnuti checkboxu
function zostavTabulku(form) {
   return form.querySelector('.otazka-ma-tabulku').checked ? form.querySelector('.otazka-tabulka').value : '';
}

function pripojVkladanieTabulky(form) {
   const panel = form.querySelector('.tabulka-vkladanie');
   const vstup = panel.querySelector('.tabulka-vloz-text');
   const hlavickaCheck = panel.querySelector('.tabulka-vloz-hlavicka');
   const povolenePole = panel.querySelector('.tabulka-vloz-povolene');
   const oddelovacPole = panel.querySelector('.tabulka-vloz-oddelovac');
   const nahlad = panel.querySelector('.tabulka-vloz-nahlad');
   const chyba = panel.querySelector('.tabulka-vloz-chyba');
   let riadky = [];
   let vystup = new Set();
   let povoleneRucne = false;

   const prvyTelo = () => hlavickaCheck.checked ? 1 : 0;
   const dalsiaPovolene = () => {
      if (povoleneRucne) return;
      const znaky = [];
      riadky.forEach((r, i) => r.forEach((text, c) => {
         if (vystup.has(`${i},${c}`)) Array.from(text).forEach(z => { if (!znaky.includes(z)) znaky.push(z); });
      }));
      povolenePole.value = znaky.join('');
   };

   function vykresli() {
      nahlad.textContent = '';
      if (!riadky.length) return;
      const tabulka = document.createElement('table');
      const stlpce = riadky[0].length;
      const tlacidla = tabulka.createTHead().insertRow();
      for (let c = 0; c < stlpce; c++) {
         const th = document.createElement('th');
         const tlacidlo = document.createElement('button');
         tlacidlo.type = 'button';
         tlacidlo.className = 'tabulka-vloz-stlpec';
         tlacidlo.dataset.c = String(c);
         tlacidlo.title = 'Označiť/zrušiť celý stĺpec ako polia na vyplnenie';
         tlacidlo.textContent = 'stĺpec';
         th.appendChild(tlacidlo);
         tlacidla.appendChild(th);
      }
      const telo = tabulka.createTBody();
      riadky.forEach((r, i) => {
         const tr = telo.insertRow();
         r.forEach((text, c) => {
            const td = tr.insertCell();
            td.textContent = text;
            if (i < prvyTelo()) {
               td.className = 'hlavicka';
            } else if (text === '') {
               td.className = 'prazdna';
            } else {
               td.className = vystup.has(`${i},${c}`) ? 'bunka vystup' : 'bunka';
               td.dataset.r = String(i);
               td.dataset.c = String(c);
            }
         });
      });
      nahlad.appendChild(tabulka);
   }

   function nacitaj() {
      riadky = parsujSchranku(vstup.value, oddelovacPole.value);
      vystup = new Set();
      povoleneRucne = false;
      chyba.textContent = '';
      dalsiaPovolene();
      vykresli();
   }

   vstup.addEventListener('input', nacitaj);
   oddelovacPole.addEventListener('change', nacitaj);
   hlavickaCheck.addEventListener('change', () => {
      riadky.forEach((_, i) => i < prvyTelo() && riadky[i].forEach((__, c) => vystup.delete(`${i},${c}`)));
      dalsiaPovolene();
      vykresli();
   });
   povolenePole.addEventListener('input', () => {
      povoleneRucne = povolenePole.value !== '';
      if (!povoleneRucne) dalsiaPovolene();
   });
   nahlad.addEventListener('click', (e) => {
      const cielova = e.target.closest('.tabulka-vloz-stlpec, td.bunka');
      if (!cielova) return;
      const c = Number(cielova.dataset.c);
      if (cielova.matches('td.bunka')) {
         const kluc = `${cielova.dataset.r},${c}`;
         if (!vystup.delete(kluc)) vystup.add(kluc);
      } else {
         const kluce = riadky.map((r, i) => [i, r[c]]).filter(([i, text]) => i >= prvyTelo() && text !== '').map(([i]) => `${i},${c}`);
         const vsetky = kluce.length > 0 && kluce.every(k => vystup.has(k));
         kluce.forEach(k => vsetky ? vystup.delete(k) : vystup.add(k));
      }
      chyba.textContent = '';
      dalsiaPovolene();
      vykresli();
   });

   form.querySelector('.otazka-tabulka-vloz').addEventListener('click', () => {
      panel.showModal();
      vstup.focus();
   });
   panel.querySelector('.tabulka-vloz-zrus').addEventListener('click', () => panel.close());
   panel.querySelector('.tabulka-vloz-vloz').addEventListener('click', () => {
      if (!riadky.length) {
         chyba.textContent = 'Najprv vložte tabuľku zo schránky.';
         return;
      }
      if (!vystup.size) {
         chyba.textContent = 'Označte aspoň jednu bunku alebo stĺpec ako pole na vyplnenie.';
         return;
      }
      const povolene = povolenePole.value;
      const nepovolena = Array.from(vystup).map(k => riadky[Number(k.split(',')[0])][Number(k.split(',')[1])])
         .find(text => povolene && Array.from(text).some(z => !povolene.includes(z)));
      if (nepovolena !== undefined) {
         chyba.textContent = `Odpoveď "${nepovolena}" obsahuje znak, ktorý nie je medzi povolenými (${povolene}).`;
         return;
      }
      const textarea = form.querySelector('.otazka-tabulka');
      const prazdna = textarea.value.trim() === '' || textarea.value === SABLONA_TABULKY;
      const vloz = () => {
         textarea.value = zostavXmlTabulky(riadky, hlavickaCheck.checked, vystup, povolene);
         const maTabulku = form.querySelector('.otazka-ma-tabulku');
         maTabulku.checked = true;
         maTabulku.dispatchEvent(new Event('change'));
         panel.close();
      };
      if (prazdna) {
         vloz();
      } else {
         potvrdDialog({nadpis: 'Prepísať tabuľku', text: 'Prepísať súčasné XML tabuľky vloženou tabuľkou?', potvrdit: 'Prepísať'}).then(potvrdene => potvrdene && vloz());
      }
   });
}

function vytvorFormularOtazky(data, jeMcq) {
   const form = document.createElement('form');
   form.className = 'otazka-formular';
   form.innerHTML = `
      <label>Názov (voliteľné, inak sa zobrazuje id)
         <input type="text" class="otazka-nazov"/>
      </label>
      <label>Znenie (môže obsahovať markup tagy)
         <textarea class="otazka-znenie" rows="3"></textarea>
      </label>
      <div class="otazka-atributy-riadok">
         <label>Body <input type="number" class="otazka-body" min="0" step="any"/></label>
         <label><input type="checkbox" class="otazka-static"/> statická</label>
         <label><input type="checkbox" class="otazka-bonus"/> bonusová</label>
         <label><input type="checkbox" class="otazka-rating"/> rating</label>
         <label class="deprecated-checkbox"><input type="checkbox" class="otazka-deprecated"/> deprecated</label>
      </div>
      <div class="otazka-napovedy">
         <div class="otazka-napovedy-zoznam"></div>
         <button type="button" class="otazka-pridaj-napovedu">+ celoplošná nápoveda</button>
      </div>
      <label><input type="checkbox" class="otazka-ma-odpovede"/> má odpovede (MCQ)</label>
      <label><input type="checkbox" class="otazka-ma-tabulku"/> má tabuľku</label>
      <fieldset class="otazka-tabulka-fieldset">
         <legend>Tabuľka (XML)</legend>
         <button type="button" class="otazka-tabulka-vloz">Vložiť zo schránky</button>
         <dialog class="tabulka-vkladanie">
            <div class="tabulka-vloz-nastavenia">
               <label><input type="checkbox" class="tabulka-vloz-hlavicka" checked/> prvý riadok je hlavička</label>
               <label>Oddeľovač
                  <select class="tabulka-vloz-oddelovac">
                     <option value="">automaticky</option>
                     <option value="&#9;">tabulátor</option>
                     <option value=";">bodkočiarka ;</option>
                     <option value=",">čiarka ,</option>
                  </select>
               </label>
               <label>Povolené znaky <input type="text" class="tabulka-vloz-povolene" spellcheck="false"/></label>
            </div>
            <textarea class="tabulka-vloz-text" rows="5" spellcheck="false" placeholder="Sem vložte (Ctrl+V) tabuľku skopírovanú z tabuľkového procesora alebo Markdown"></textarea>
            <div class="tabulka-vloz-nahlad"></div>
            <div class="tabulka-vloz-chyba"></div>
            <div class="tabulka-vloz-tlacidla">
               <button type="button" class="tabulka-vloz-zrus">Zrušiť</button>
               <button type="button" class="tabulka-vloz-vloz">Vložiť</button>
            </div>
         </dialog>
         <textarea class="otazka-tabulka" rows="12" spellcheck="false"></textarea>
      </fieldset>
      <fieldset class="otazka-odpovede-fieldset">
         <legend>Odpovede</legend>
         <div class="otazka-odpovede"></div>
         <button type="button" class="otazka-pridaj-odpoved">+ odpoveď</button>
      </fieldset>
      <div class="otazka-otvorena">
         <div class="otazka-vzory">
            Vzory (každý je samostatná správna odpoveď, môže mať viac riadkov)
            <div class="otazka-vzory-zoznam"></div>
            <button type="button" class="otazka-pridaj-vzor">+ vzor</button>
         </div>
         <label>Kľúčové slová (oddelené čiarkou)
            <input type="text" class="otazka-klucove-slova"/>
         </label>
      </div>
      <div class="dialog-chyba"></div>
      <button type="button" class="otazka-uloz">Uložiť</button>
      <button type="button" class="otazka-zrus">Zrušiť</button>
   `;
   const znenieRaw = (data.znenie || '').replace(/^<znenie[^>]*>/, '').replace(/<\/znenie>$/, '');
   form.querySelector('.otazka-znenie').value = znenieRaw;
   form.querySelector('.otazka-nazov').value = data.nazov || '';
   const jeTabulka = !!data.tabulka;
   form.querySelector('.otazka-ma-odpovede').checked = !!jeMcq && !jeTabulka;
   form.querySelector('.otazka-ma-tabulku').checked = jeTabulka;
   form.querySelector('.otazka-tabulka').value = data.tabulka || SABLONA_TABULKY;
   form.querySelector('.otazka-klucove-slova').value = (data.klucove_slova || []).join(', ');
   form.querySelector('.otazka-body').value = data.body || '';
   form.querySelector('.otazka-static').checked = data.static === '1';
   form.querySelector('.otazka-bonus').checked = data.bonus === '1';
   form.querySelector('.otazka-rating').checked = data.rating === '1';
   form.querySelector('.otazka-deprecated').checked = data.deprecated === '1';

   const odpovedeWrap = form.querySelector('.otazka-odpovede');
   (data.odpovede || []).forEach(odp => odpovedeWrap.appendChild(riadokOdpoved(odp)));
   form.querySelector('.otazka-pridaj-odpoved').addEventListener('click', () => odpovedeWrap.appendChild(riadokOdpoved()));

   const napovedyWrap = form.querySelector('.otazka-napovedy-zoznam');
   (data.napovede || []).forEach(text => napovedyWrap.appendChild(riadokNapoveda(text)));
   form.querySelector('.otazka-pridaj-napovedu').addEventListener('click', () => napovedyWrap.appendChild(riadokNapoveda('')));

   const vzoryWrap = form.querySelector('.otazka-vzory-zoznam');
   const vzory = data.vzory && data.vzory.length ? data.vzory : [''];
   vzory.forEach(text => vzoryWrap.appendChild(riadokVzor(text)));
   form.querySelector('.otazka-pridaj-vzor').addEventListener('click', () => vzoryWrap.appendChild(riadokVzor('')));

   function aktualizujVetvu() {
      const mcq = form.querySelector('.otazka-ma-odpovede').checked;
      const tabulka = form.querySelector('.otazka-ma-tabulku').checked;
      form.querySelector('.otazka-odpovede-fieldset').style.display = mcq ? '' : 'none';
      form.querySelector('.otazka-tabulka-fieldset').style.display = tabulka ? '' : 'none';
      form.querySelector('.otazka-otvorena').style.display = mcq || tabulka ? 'none' : '';
   }
   //otazka ma najviac jednu z vetiev (MCQ alebo tabulka); obsah vypnutej vetvy ostava vo formulari
   form.querySelector('.otazka-ma-odpovede').addEventListener('change', (e) => {
      if (e.target.checked) form.querySelector('.otazka-ma-tabulku').checked = false;
      aktualizujVetvu();
   });
   form.querySelector('.otazka-ma-tabulku').addEventListener('change', (e) => {
      if (e.target.checked) form.querySelector('.otazka-ma-odpovede').checked = false;
      aktualizujVetvu();
   });
   aktualizujVetvu();
   pripojVkladanieTabulky(form);

   return form;
}

function otvorFormularOtazky(otazkaId) {
   const riadok = document.querySelector(`.editOtazkaIcon[data-id="${otazkaId}"]`).closest('.collapse');
   if (!riadok || riadok.querySelector('.otazka-formular')) return;
   getJson(`/admin/question?id=${encodeURIComponent(otazkaId)}`).then(data => {
      const jeMcq = (data.odpovede || []).length > 0;
      const form = vytvorFormularOtazky(data, jeMcq);
      riadok.appendChild(form);
      form.querySelector('.otazka-zrus').addEventListener('click', () => form.remove());
      form.querySelector('.otazka-uloz').addEventListener('click', () => {
         const mcq = form.querySelector('.otazka-ma-odpovede').checked;
         const znenieText = form.querySelector('.otazka-znenie').value;
         const params = {
            operacia: 'update',
            otazka_id: otazkaId,
            znenie: `<znenie>${znenieText}</znenie>`,
            body: form.querySelector('.otazka-body').value,
            static: form.querySelector('.otazka-static').checked ? '1' : '',
            bonus: form.querySelector('.otazka-bonus').checked ? '1' : '',
            rating: form.querySelector('.otazka-rating').checked ? '1' : '',
            nazov: form.querySelector('.otazka-nazov').value,
            deprecated: form.querySelector('.otazka-deprecated').checked ? '1' : '',
            odpovede: JSON.stringify(mcq ? zostavOdpovede(form) : []),
            tabulka: zostavTabulku(form),
            napovede: JSON.stringify(zostavCeloplosneNapovede(form)),
            vzory: JSON.stringify(mcq ? [] : zostavVzory(form)),
            klucove_slova: JSON.stringify(mcq ? [] : form.querySelector('.otazka-klucove-slova').value.split(',').map(s => s.trim()).filter(Boolean)),
         };
         odosliFormular(form, '/admin/process_question', params);
      });
   }).catch(err => oznamDialog({text: err.message}));
}

function pridajOtazku(kategoriaId) {
   const icon = document.querySelector(`.addOtazkaIcon[data-id="${kategoriaId}"]`);
   const pauseRow = icon.closest('.pause-row');
   if (!pauseRow) return;
   if (pauseRow.nextElementSibling && pauseRow.nextElementSibling.classList.contains('otazka-formular')) return;
   const form = vytvorFormularOtazky({}, true);
   pauseRow.insertAdjacentElement('afterend', form);
   form.querySelector('.otazka-zrus').addEventListener('click', () => form.remove());
   form.querySelector('.otazka-uloz').addEventListener('click', () => {
      const mcq = form.querySelector('.otazka-ma-odpovede').checked;
      const znenieText = form.querySelector('.otazka-znenie').value;
      const params = {
         operacia: 'create',
         kategoria_id: kategoriaId,
         znenie: `<znenie>${znenieText}</znenie>`,
         body: form.querySelector('.otazka-body').value,
         static: form.querySelector('.otazka-static').checked ? '1' : '',
         bonus: form.querySelector('.otazka-bonus').checked ? '1' : '',
         rating: form.querySelector('.otazka-rating').checked ? '1' : '',
         nazov: form.querySelector('.otazka-nazov').value,
         deprecated: form.querySelector('.otazka-deprecated').checked ? '1' : '',
         odpovede: JSON.stringify(mcq ? zostavOdpovede(form) : []),
         tabulka: zostavTabulku(form),
         napovede: JSON.stringify(zostavCeloplosneNapovede(form)),
         vzory: JSON.stringify(mcq ? [] : zostavVzory(form)),
         klucove_slova: JSON.stringify(mcq ? [] : form.querySelector('.otazka-klucove-slova').value.split(',').map(s => s.trim()).filter(Boolean)),
      };
      odosliFormular(form, '/admin/process_question', params);
   });
}

function zmazOtazku(otazkaId, znenie) {
   confirmZmazanie('otazka', otazkaId, znenie).then(potvrdene => {
      if (!potvrdene) return;
      postForm('/admin/process_question', {otazka_id: otazkaId, operacia: 'delete'})
         .then(() => reloadZachovajKapitolu())
         .catch(err => oznamDialog({text: err.message}));
   });
}

function obnovOtazku(otazkaId) {
   postForm('/admin/process_question', {otazka_id: otazkaId, operacia: 'restore'})
      .then(() => reloadZachovajKapitolu())
      .catch(err => oznamDialog({text: err.message}));
}

function aktivujKapitoluPodlaHash() {
   if (!location.hash) return;
   const kapitolaId = location.hash.slice(1);
   const odkaz = document.querySelector(`a.nav-link[href="#${CSS.escape(kapitolaId)}"]`);
   if (odkaz && window.bootstrap) {
      new bootstrap.Tab(odkaz).show();
   }
}

document.addEventListener('DOMContentLoaded', () => {
   aktivujKapitoluPodlaHash();
   document.addEventListener('click', (e) => {
      const kap = e.target.closest('.addKapitolaIcon, .editKapitolaIcon, .delKapitolaIcon');
      if (kap) {
         e.stopPropagation();
         const predmet = kap.dataset.predmet;
         if (kap.matches('.addKapitolaIcon')) pridajKapitolu(predmet);
         else if (kap.matches('.editKapitolaIcon')) upravKapitolu(predmet, kap.dataset.id, kap.dataset.nazov);
         else if (kap.matches('.delKapitolaIcon') && !kap.classList.contains('disabled')) zmazKapitolu(predmet, kap.dataset.id);
         return;
      }

      const addKat = e.target.closest('.addKategoriaIcon');
      if (addKat) {
         e.stopPropagation();
         pridajKategoriu(addKat.dataset.predmet);
         return;
      }

      const kat = e.target.closest('.editKategoriaIcon, .delKategoriaIcon, .restoreKategoriaIcon');
      if (kat) {
         e.stopPropagation();
         const predmet = kat.dataset.predmet;
         const nazov = kat.closest('.okraj')?.querySelector('.nazov-alebo-id')?.textContent?.trim() || kat.dataset.id;
         if (kat.matches('.editKategoriaIcon')) upravKategoriu(predmet, kat.dataset.id);
         else if (kat.matches('.delKategoriaIcon')) zmazKategoriu(predmet, kat.dataset.id, nazov);
         else if (kat.matches('.restoreKategoriaIcon')) obnovKategoriu(predmet, kat.dataset.id);
         return;
      }

      const addOt = e.target.closest('.addOtazkaIcon');
      if (addOt) {
         e.stopPropagation();
         pridajOtazku(addOt.dataset.id);
         return;
      }

      const ot = e.target.closest('.editOtazkaIcon, .delOtazkaIcon, .restoreOtazkaIcon');
      if (ot) {
         e.stopPropagation();
         const nazovOt = ot.closest('.okraj')?.querySelector('.nazov-alebo-id')?.textContent?.trim() || ot.dataset.id;
         if (ot.matches('.editOtazkaIcon')) otvorFormularOtazky(ot.dataset.id);
         else if (ot.matches('.delOtazkaIcon')) zmazOtazku(ot.dataset.id, nazovOt);
         else if (ot.matches('.restoreOtazkaIcon')) obnovOtazku(ot.dataset.id);
         return;
      }
   });
});
