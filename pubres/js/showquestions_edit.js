function postForm(url, params) {
   return fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams(params)
   }).then(resp => {
      if (!resp.ok) return resp.json().then(d => { throw new Error(d.detail || 'Požiadavka zlyhala'); });
      return resp.json();
   });
}

function getJson(url) {
   return fetch(url).then(resp => {
      if (!resp.ok) throw new Error('Požiadavka zlyhala');
      return resp.json();
   });
}

function confirmZmazanie(typ, id, nazov) {
   return getJson(`/admin/is_used?id=${encodeURIComponent(id)}&typ=${typ}`).then(data => {
      const text = data.used
         ? `${nazov} je použitá v teste — bude len archivovaná, pokračovať?`
         : `Naozaj zmazať ${nazov}?`;
      return confirm(text);
   });
}

// --- kapitola ---

function pridajKapitolu(predmet) {
   const kapitolaId = prompt('ID novej kapitoly (napr. 05):');
   if (!kapitolaId) return;
   const nazov = prompt('Názov kapitoly (voliteľné):') || '';
   postForm('/admin/process_chapter', {predmet, kapitola_id: kapitolaId, operacia: 'create', nazov})
      .then(() => location.reload())
      .catch(err => alert(err.message));
}

function upravKapitolu(predmet, kapitolaId) {
   const nazov = prompt('Nový názov kapitoly:');
   if (nazov === null) return;
   postForm('/admin/process_chapter', {predmet, kapitola_id: kapitolaId, operacia: 'update', nazov})
      .then(() => location.reload())
      .catch(err => alert(err.message));
}

function zmazKapitolu(predmet, kapitolaId) {
   if (!confirm(`Naozaj zmazať kapitolu ${kapitolaId}?`)) return;
   postForm('/admin/process_chapter', {predmet, kapitola_id: kapitolaId, operacia: 'delete'})
      .then(() => location.reload())
      .catch(err => alert(err.message));
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
         <label>Body <input type="number" class="kat-body" min="0"/></label>
         <label><input type="checkbox" class="kat-static"/> statická</label>
         <label><input type="checkbox" class="kat-bonus"/> bonusová</label>
         <label class="deprecated-checkbox"><input type="checkbox" class="kat-deprecated"/> deprecated</label>
      </div>
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
      alert('Najprv vyber kapitolu.');
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
         alert('Počet otázok na výber je povinný.');
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
      postForm('/admin/process_category', params)
         .then(() => location.reload())
         .catch(err => alert(err.message));
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
         postForm('/admin/process_category', params)
            .then(() => location.reload())
            .catch(err => alert(err.message));
      });
   }).catch(err => alert(err.message));
}

function zmazKategoriu(predmet, kategoriaId, nazov) {
   confirmZmazanie('kategoria', kategoriaId, nazov).then(potvrdene => {
      if (!potvrdene) return;
      postForm('/admin/process_category', {predmet, kategoria_id: kategoriaId, operacia: 'delete'})
         .then(() => location.reload())
         .catch(err => alert(err.message));
   });
}

function obnovKategoriu(predmet, kategoriaId) {
   postForm('/admin/process_category', {predmet, kategoria_id: kategoriaId, operacia: 'restore'})
      .then(() => location.reload())
      .catch(err => alert(err.message));
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
         <label>Body <input type="number" class="otazka-body" min="0"/></label>
         <label><input type="checkbox" class="otazka-static"/> statická</label>
         <label><input type="checkbox" class="otazka-bonus"/> bonusová</label>
         <label class="deprecated-checkbox"><input type="checkbox" class="otazka-deprecated"/> deprecated</label>
      </div>
      <div class="otazka-napovedy">
         <div class="otazka-napovedy-zoznam"></div>
         <button type="button" class="otazka-pridaj-napovedu">+ celoplošná nápoveda</button>
      </div>
      <label><input type="checkbox" class="otazka-ma-odpovede"/> má odpovede (MCQ)</label>
      <fieldset class="otazka-odpovede-fieldset">
         <legend>Odpovede</legend>
         <div class="otazka-odpovede"></div>
         <button type="button" class="otazka-pridaj-odpoved">+ odpoveď</button>
      </fieldset>
      <div class="otazka-otvorena">
         <label>Vzor (vzorová odpoveď)
            <textarea class="otazka-vzor" rows="2"></textarea>
         </label>
         <label>Kľúčové slová (oddelené čiarkou)
            <input type="text" class="otazka-klucove-slova"/>
         </label>
      </div>
      <button type="button" class="otazka-uloz">Uložiť</button>
      <button type="button" class="otazka-zrus">Zrušiť</button>
   `;
   const znenieRaw = (data.znenie || '').replace(/^<znenie[^>]*>/, '').replace(/<\/znenie>$/, '');
   form.querySelector('.otazka-znenie').value = znenieRaw;
   form.querySelector('.otazka-nazov').value = data.nazov || '';
   form.querySelector('.otazka-ma-odpovede').checked = !!jeMcq;
   form.querySelector('.otazka-vzor').value = data.vzor || '';
   form.querySelector('.otazka-klucove-slova').value = (data.klucove_slova || []).join(', ');
   form.querySelector('.otazka-body').value = data.body || '';
   form.querySelector('.otazka-static').checked = data.static === '1';
   form.querySelector('.otazka-bonus').checked = data.bonus === '1';
   form.querySelector('.otazka-deprecated').checked = data.deprecated === '1';

   const odpovedeWrap = form.querySelector('.otazka-odpovede');
   (data.odpovede || []).forEach(odp => odpovedeWrap.appendChild(riadokOdpoved(odp)));
   form.querySelector('.otazka-pridaj-odpoved').addEventListener('click', () => odpovedeWrap.appendChild(riadokOdpoved()));

   const napovedyWrap = form.querySelector('.otazka-napovedy-zoznam');
   (data.napovede || []).forEach(text => napovedyWrap.appendChild(riadokNapoveda(text)));
   form.querySelector('.otazka-pridaj-napovedu').addEventListener('click', () => napovedyWrap.appendChild(riadokNapoveda('')));

   function aktualizujVetvu() {
      const mcq = form.querySelector('.otazka-ma-odpovede').checked;
      form.querySelector('.otazka-odpovede-fieldset').style.display = mcq ? '' : 'none';
      form.querySelector('.otazka-otvorena').style.display = mcq ? 'none' : '';
   }
   form.querySelector('.otazka-ma-odpovede').addEventListener('change', aktualizujVetvu);
   aktualizujVetvu();

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
            nazov: form.querySelector('.otazka-nazov').value,
            deprecated: form.querySelector('.otazka-deprecated').checked ? '1' : '',
            odpovede: JSON.stringify(mcq ? zostavOdpovede(form) : []),
            napovede: JSON.stringify(zostavCeloplosneNapovede(form)),
            vzor: mcq ? '' : form.querySelector('.otazka-vzor').value,
            klucove_slova: JSON.stringify(mcq ? [] : form.querySelector('.otazka-klucove-slova').value.split(',').map(s => s.trim()).filter(Boolean)),
         };
         postForm('/admin/process_question', params)
            .then(() => location.reload())
            .catch(err => alert(err.message));
      });
   }).catch(err => alert(err.message));
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
         nazov: form.querySelector('.otazka-nazov').value,
         deprecated: form.querySelector('.otazka-deprecated').checked ? '1' : '',
         odpovede: JSON.stringify(mcq ? zostavOdpovede(form) : []),
         napovede: JSON.stringify(zostavCeloplosneNapovede(form)),
         vzor: mcq ? '' : form.querySelector('.otazka-vzor').value,
         klucove_slova: JSON.stringify(mcq ? [] : form.querySelector('.otazka-klucove-slova').value.split(',').map(s => s.trim()).filter(Boolean)),
      };
      postForm('/admin/process_question', params)
         .then(() => location.reload())
         .catch(err => alert(err.message));
   });
}

function zmazOtazku(otazkaId, znenie) {
   confirmZmazanie('otazka', otazkaId, znenie).then(potvrdene => {
      if (!potvrdene) return;
      postForm('/admin/process_question', {otazka_id: otazkaId, operacia: 'delete'})
         .then(() => location.reload())
         .catch(err => alert(err.message));
   });
}

function obnovOtazku(otazkaId) {
   postForm('/admin/process_question', {otazka_id: otazkaId, operacia: 'restore'})
      .then(() => location.reload())
      .catch(err => alert(err.message));
}

document.addEventListener('DOMContentLoaded', () => {
   document.addEventListener('click', (e) => {
      const kap = e.target.closest('.addKapitolaIcon, .editKapitolaIcon, .delKapitolaIcon');
      if (kap) {
         e.stopPropagation();
         const predmet = kap.dataset.predmet;
         if (kap.matches('.addKapitolaIcon')) pridajKapitolu(predmet);
         else if (kap.matches('.editKapitolaIcon')) upravKapitolu(predmet, kap.dataset.id);
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
