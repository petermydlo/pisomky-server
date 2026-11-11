//Editor tabulky vo formulari otazky: mriezka (bunky su textove polia), vkladanie zo schranky a zobrazenie XML.
//Stav a jeho zmeny (bez DOM) su v tabulka.js. Skryte pole .otazka-tabulka drzi XML, ktore sa odosiela (zostavTabulku v showquestions_edit.js).
//Ulozene XML sa v poli necha nezmenene, kym ucitel v mriezke nic nezmeni, aby sa nemenila otazka, ktorej sa tabulka nedotkla.

//XML <tabulka> (uz overene serverom) -> stav; pri neocakavanej strukture vyhodi Error
function parsujXmlTabulky(text) {
   const dokument = new DOMParser().parseFromString(text, 'application/xml');
   if (dokument.getElementsByTagName('parsererror').length) throw new Error('XML nie je platné');
   const koren = dokument.documentElement;
   if (koren.tagName !== 'tabulka') throw new Error('koreňový element nie je <tabulka>');
   const riadky = [];
   const vystup = new Set();
   let maHlavicku = false;
   Array.from(koren.children).forEach((el) => {
      if (el.tagName === 'hlavicka') maHlavicku = true;
      else if (el.tagName !== 'riadok') throw new Error(`neznámy element <${el.tagName}>`);
      const r = riadky.length;
      riadky.push(Array.from(el.children).map((bunka, c) => {
         if (bunka.tagName !== 'bunka') throw new Error(`neznámy element <${bunka.tagName}>`);
         if (!bunka.hasAttribute('odpoved')) return bunka.textContent;
         vystup.add(`${r},${c}`);
         return bunka.getAttribute('odpoved');
      }));
   });
   if (!riadky.length || riadky.some(r => r.length !== riadky[0].length || !r.length)) throw new Error('riadky nemajú rovnaký počet buniek');
   return {riadky, vystup, maHlavicku, povolene: koren.getAttribute('povolene') || ''};
}

//dialog s XML len na citanie; text je oznaceny, aby sa dal skopirovat
function zobrazXmlTabulky(xml) {
   const dialog = document.createElement('dialog');
   dialog.className = 'dialog-okno dialog-siroky';
   dialog.innerHTML = `
      <form>
         <h2>XML tabuľky</h2>
         <textarea class="tabulka-xml-text" rows="16" readonly spellcheck="false"></textarea>
         <div class="dialog-tlacidla">
            <span class="tabulka-xml-info"></span>
            <button type="button" class="tabulka-xml-kopiruj">Kopírovať</button>
            <button type="submit">Zavrieť</button>
         </div>
      </form>`;
   const text = dialog.querySelector('.tabulka-xml-text');
   const info = dialog.querySelector('.tabulka-xml-info');
   text.value = xml;
   dialog.querySelector('form').addEventListener('submit', (e) => {
      e.preventDefault();
      dialog.close();
   });
   dialog.querySelector('.tabulka-xml-kopiruj').addEventListener('click', () => {
      (navigator.clipboard ? navigator.clipboard.writeText(xml) : Promise.reject(new Error('schránka nie je dostupná')))
         .then(() => { info.textContent = 'Skopírované do schránky.'; })
         .catch(() => {
            text.select();
            info.textContent = 'Kopírovanie zlyhalo, text je označený (Ctrl+C).';
         });
   });
   dialog.addEventListener('close', () => dialog.remove());
   document.body.appendChild(dialog);
   dialog.showModal();
   text.select();
}

//contenteditable="plaintext-only" vklada len cisty text; ak ho prehliadac nepozna (setter hodi chybu), pouzije sa "true" a text vlozi obsluha paste
const PLAINTEXT_ONLY = (() => {
   try {
      const el = document.createElement('div');
      el.contentEditable = 'plaintext-only';
      return el.contentEditable === 'plaintext-only';
   } catch (err) {
      return false;
   }
})();

const HTML_EDITORA_TABULKY = `
   <div class="tabulka-nastroje">
      <button type="button" class="tabulka-vloz-otvor">Vložiť zo schránky</button>
      <button type="button" class="tabulka-xml-otvor">Zobraz XML tabuľky</button>
   </div>
   <div class="tabulka-nastroje">
      <label><input type="checkbox" class="tabulka-hlavicka"/> prvý riadok je hlavička</label>
      <label>Povolené znaky <input type="text" class="tabulka-povolene" spellcheck="false"/></label>
   </div>
   <div class="tabulka-chyba"></div>
   <div class="tabulka-mriezka"></div>
   <div class="tabulka-nastroje">
      <button type="button" class="tabulka-pridaj-riadok">+ riadok</button>
      <button type="button" class="tabulka-pridaj-stlpec">+ stĺpec</button>
   </div>
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
      </div>
      <textarea class="tabulka-vloz-text" rows="5" spellcheck="false" placeholder="Sem vložte (Ctrl+V) tabuľku skopírovanú z tabuľkového procesora alebo Markdown"></textarea>
      <div class="tabulka-vloz-nahlad"></div>
      <div class="tabulka-vloz-chyba"></div>
      <div class="tabulka-vloz-tlacidla">
         <button type="button" class="tabulka-vloz-zrus">Zrušiť</button>
         <button type="button" class="tabulka-vloz-vloz">Vložiť</button>
      </div>
   </dialog>`;

//povodneXml: ulozene XML tabulky otazky, alebo '' pre novu tabulku
function pripojEditorTabulky(form, povodneXml) {
   const koren = form.querySelector('.tabulka-editor');
   const skryte = form.querySelector('.otazka-tabulka');
   koren.innerHTML = HTML_EDITORA_TABULKY;
   const hlavickaCheck = koren.querySelector('.tabulka-hlavicka');
   const povolenePole = koren.querySelector('.tabulka-povolene');
   const mriezka = koren.querySelector('.tabulka-mriezka');
   const chyba = koren.querySelector('.tabulka-chyba');
   let stav = novyStavTabulky();
   let povoleneRucne = false;   //kym ucitel nezapise povolene znaky, predvyplnaju sa z odpovedi

   //ikonove tlacidlo (Bootstrap Icons) na ovladanie stlpca alebo riadka; i = index stlpca/riadka
   function tlacidlo(trieda, ikona, titulok, index, zakazane) {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = trieda;
      el.title = titulok;
      el.setAttribute('aria-label', titulok);
      el.dataset.i = String(index);
      el.disabled = !!zakazane;
      const i = document.createElement('i');
      i.className = `bi bi-${ikona}`;
      el.appendChild(i);
      return el;
   }

   function vykresli() {
      mriezka.textContent = '';
      const prvy = prvyRiadokTela(stav);
      const stlpcov = stav.riadky[0].length;
      const tabulka = document.createElement('table');
      const ovladanie = tabulka.createTHead().insertRow();
      ovladanie.insertCell();
      for (let c = 0; c < stlpcov; c++) {
         const th = document.createElement('th');
         th.append(
            tlacidlo('tabulka-stlpec-pole', 'check2-square', 'Označiť alebo zrušiť celý stĺpec ako polia na vyplnenie', c),
            tlacidlo('tabulka-stlpec-zmaz', 'x-lg', 'Odstrániť stĺpec', c, stlpcov <= 1),
         );
         ovladanie.appendChild(th);
      }
      const telo = tabulka.createTBody();
      stav.riadky.forEach((riadok, r) => {
         const tr = telo.insertRow();
         const ovl = tr.insertCell();
         if (r >= prvy) ovl.appendChild(tlacidlo('tabulka-riadok-zmaz', 'x-lg', 'Odstrániť riadok', r, stav.riadky.length - prvy <= 1));
         riadok.forEach((text, c) => {
            const td = tr.insertCell();
            const bunka = document.createElement('div');
            bunka.className = 'tabulka-bunka';
            bunka.contentEditable = PLAINTEXT_ONLY ? 'plaintext-only' : 'true';
            bunka.setAttribute('role', 'textbox');
            bunka.setAttribute('aria-label', `Bunka, riadok ${r + 1}, stĺpec ${c + 1}`);
            bunka.spellcheck = false;
            bunka.textContent = text;
            bunka.dataset.r = String(r);
            bunka.dataset.c = String(c);
            td.appendChild(bunka);
            if (r < prvy) {
               td.className = 'hlavicka';
               return;
            }
            const pole = document.createElement('input');
            pole.type = 'checkbox';
            pole.className = 'tabulka-pole';
            pole.title = 'Pole na vyplnenie: text bunky je správna odpoveď';
            pole.checked = stav.vystup.has(`${r},${c}`);
            pole.dataset.r = String(r);
            pole.dataset.c = String(c);
            td.appendChild(pole);
            if (pole.checked) td.className = 'pole';
         });
      });
      mriezka.appendChild(tabulka);
   }

   //po kazdej zmene: povolene znaky (ak ich ucitel nezadal sam) a XML v skrytom poli
   function poZmene() {
      chyba.textContent = '';
      if (!povoleneRucne) {
         stav.povolene = povoleneZVystupu(stav);
         povolenePole.value = stav.povolene;
      }
      skryte.value = xmlTabulky(stav);
   }

   function nastav(novyStav, rucnePovolene) {
      stav = novyStav;
      povoleneRucne = rucnePovolene;
      hlavickaCheck.checked = stav.maHlavicku;
      povolenePole.value = stav.povolene;
      vykresli();
   }

   //presunie kurzor do bunky (r, c) a oznaci jej obsah, aby sa dal hned prepisat; vrati false, ak taka bunka nie je
   function prejdiNaBunku(r, c) {
      const bunka = mriezka.querySelector(`.tabulka-bunka[data-r="${r}"][data-c="${c}"]`);
      if (!bunka) return false;
      bunka.focus();
      window.getSelection().selectAllChildren(bunka);
      return true;
   }

   mriezka.addEventListener('input', (e) => {
      if (!e.target.matches('.tabulka-bunka')) return;
      stav.riadky[Number(e.target.dataset.r)][Number(e.target.dataset.c)] = e.target.textContent.replace(/[\r\n]+/g, ' ');
      poZmene();
   });
   //Enter a sipka dole = bunka pod, Shift+Enter a sipka hore = bunka nad (ako v tabulkovom procesore); bunka je jednoriadkova
   mriezka.addEventListener('keydown', (e) => {
      if (!e.target.matches('.tabulka-bunka') || e.isComposing) return;
      const bezModifikatorov = !e.ctrlKey && !e.altKey && !e.metaKey && !e.shiftKey;
      let smer = 0;
      if (e.key === 'Enter') smer = e.shiftKey ? -1 : 1;
      else if (e.key === 'ArrowDown' && bezModifikatorov) smer = 1;
      else if (e.key === 'ArrowUp' && bezModifikatorov) smer = -1;
      if (!smer) return;
      e.preventDefault();
      prejdiNaBunku(Number(e.target.dataset.r) + smer, Number(e.target.dataset.c));
   });
   mriezka.addEventListener('beforeinput', (e) => {
      if (e.target.matches('.tabulka-bunka') && (e.inputType === 'insertParagraph' || e.inputType === 'insertLineBreak')) e.preventDefault();
   });
   //vlozeny text je vzdy cisty a jednoriadkovy (nove riadky a tabulatory sa nahradia medzerou)
   mriezka.addEventListener('paste', (e) => {
      if (!e.target.matches('.tabulka-bunka')) return;
      e.preventDefault();
      document.execCommand('insertText', false, e.clipboardData.getData('text/plain').replace(/\s*[\r\n\t]+\s*/g, ' ').trim());
   });
   mriezka.addEventListener('change', (e) => {
      if (!e.target.matches('.tabulka-pole')) return;
      prepniBunkuTabulky(stav, Number(e.target.dataset.r), Number(e.target.dataset.c));
      e.target.closest('td').classList.toggle('pole', e.target.checked);
      poZmene();
   });
   mriezka.addEventListener('click', (e) => {
      const tl = e.target.closest('button');
      if (!tl) return;
      const i = Number(tl.dataset.i);
      if (tl.matches('.tabulka-stlpec-pole')) prepniStlpecTabulky(stav, i);
      else if (tl.matches('.tabulka-stlpec-zmaz')) odstranStlpecTabulky(stav, i);
      else if (tl.matches('.tabulka-riadok-zmaz')) odstranRiadokTabulky(stav, i);
      else return;
      vykresli();
      poZmene();
   });
   koren.querySelector('.tabulka-pridaj-riadok').addEventListener('click', () => {
      pridajRiadokTabulky(stav);
      vykresli();
      poZmene();
   });
   koren.querySelector('.tabulka-pridaj-stlpec').addEventListener('click', () => {
      pridajStlpecTabulky(stav);
      vykresli();
      poZmene();
   });
   hlavickaCheck.addEventListener('change', () => {
      nastavHlavickuTabulky(stav, hlavickaCheck.checked);
      vykresli();
      poZmene();
   });
   povolenePole.addEventListener('input', () => {
      povoleneRucne = povolenePole.value !== '';
      stav.povolene = povolenePole.value;
      poZmene();
   });
   koren.querySelector('.tabulka-xml-otvor').addEventListener('click', () => zobrazXmlTabulky(skryte.value));

   //--- vkladanie zo schranky: vlozi sa do mriezky, polia sa oznacuju tam ---
   const panel = koren.querySelector('.tabulka-vkladanie');
   const vstup = panel.querySelector('.tabulka-vloz-text');
   const vlozHlavicka = panel.querySelector('.tabulka-vloz-hlavicka');
   const oddelovac = panel.querySelector('.tabulka-vloz-oddelovac');
   const nahlad = panel.querySelector('.tabulka-vloz-nahlad');
   const vlozChyba = panel.querySelector('.tabulka-vloz-chyba');

   function nahladVlozenej() {
      nahlad.textContent = '';
      vlozChyba.textContent = '';
      const riadky = parsujSchranku(vstup.value, oddelovac.value);
      if (!riadky.length) return;
      const tabulka = document.createElement('table');
      riadky.forEach((r, i) => {
         const tr = tabulka.insertRow();
         r.forEach((text) => {
            const td = tr.insertCell();
            td.textContent = text;
            if (i === 0 && vlozHlavicka.checked) td.className = 'hlavicka';
         });
      });
      nahlad.appendChild(tabulka);
   }
   vstup.addEventListener('input', nahladVlozenej);
   oddelovac.addEventListener('change', nahladVlozenej);
   vlozHlavicka.addEventListener('change', nahladVlozenej);
   koren.querySelector('.tabulka-vloz-otvor').addEventListener('click', () => {
      panel.showModal();
      vstup.focus();
   });
   panel.querySelector('.tabulka-vloz-zrus').addEventListener('click', () => panel.close());
   panel.querySelector('.tabulka-vloz-vloz').addEventListener('click', () => {
      const riadky = parsujSchranku(vstup.value, oddelovac.value);
      if (!riadky.length) {
         vlozChyba.textContent = 'Najprv vložte tabuľku zo schránky.';
         return;
      }
      const vloz = () => {
         nastav(stavZRiadkov(riadky, vlozHlavicka.checked), false);
         poZmene();
         panel.close();
      };
      if (stavJePrazdny(stav)) {
         vloz();
      } else {
         potvrdDialog({nadpis: 'Prepísať tabuľku', text: 'Súčasná tabuľka sa nahradí vloženou tabuľkou.', potvrdit: 'Prepísať'}).then(potvrdene => potvrdene && vloz());
      }
   });

   //--- pociatocny stav ---
   if (povodneXml) {
      skryte.value = povodneXml;
      try {
         nastav(parsujXmlTabulky(povodneXml), true);
      } catch (err) {
         chyba.textContent = `Uloženú tabuľku sa nepodarilo načítať do mriežky (${err.message}). Kým v mriežke nič nezmeníte, uloží sa pôvodná.`;
         nastav(stav, false);
      }
   } else {
      nastav(stav, false);
      poZmene();
   }
}
