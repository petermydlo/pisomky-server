//Vkladanie tabulky zo schranky: TSV (tabulkovy procesor) alebo Markdown -> pole riadkov (pole retazcov), vsetky rovnako dlhe
function parsujCsv(text, oddelovac) {
   const riadky = [];
   let riadok = [];
   let bunka = '';
   let vUvodzovkach = false;
   for (let i = 0; i < text.length; i++) {
      const z = text[i];
      if (vUvodzovkach) {
         if (z === '"' && text[i + 1] === '"') {
            bunka += '"';
            i++;
         } else if (z === '"') {
            vUvodzovkach = false;
         } else {
            bunka += z;
         }
      } else if (z === '"' && bunka === '') {
         vUvodzovkach = true;
      } else if (z === oddelovac) {
         riadok.push(bunka);
         bunka = '';
      } else if (z === '\n') {
         riadok.push(bunka);
         riadky.push(riadok);
         riadok = [];
         bunka = '';
      } else if (z !== '\r') {
         bunka += z;
      }
   }
   if (bunka !== '' || riadok.length) {
      riadok.push(bunka);
      riadky.push(riadok);
   }
   return riadky;
}

function parsujMarkdown(text) {
   return text.split('\n').map(r => r.trim()).filter(r => r !== '').map(r => {
      const vnutro = r.replace(/^\|/, '').replace(/\|$/, '');
      return vnutro.split(/(?<!\\)\|/).map(b => b.trim().replace(/\\\|/g, '|'));
   }).filter(bunky => !bunky.every(b => /^:?-+:?$/.test(b)));
}

//oddelovac: '' = automaticky (tabulator, potom Markdown '|', potom ';', potom ','), inak jeden znak (tabulator, ';' alebo ',')
function parsujSchranku(text, oddelovac = '') {
   if (oddelovac === '') {
      oddelovac = ['\t', '|', ';', ','].find(z => text.includes(z)) || '\t';
   }
   const riadky = oddelovac === '|' ? parsujMarkdown(text) : parsujCsv(text, oddelovac);
   const siroka = Math.max(0, ...riadky.map(r => r.length));
   return riadky.map(r => Array.from({length: siroka}, (_, i) => (r[i] || '').trim()));
}

function escapujXml(text) {
   return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

//vystup: Set retazcov "riadok,stlpec" (indexy do pola riadkov) s bunkami, ktore su polom na vyplnenie
function zostavXmlTabulky(riadky, maHlavicku, vystup, povolene) {
   const casti = [`<tabulka povolene="${escapujXml(povolene)}">`];
   riadky.forEach((r, i) => {
      const element = maHlavicku && i === 0 ? 'hlavicka' : 'riadok';
      casti.push(`   <${element}>`);
      r.forEach((text, c) => casti.push(vystup.has(`${i},${c}`)
         ? `      <bunka odpoved="${escapujXml(text)}"/>`
         : `      <bunka>${escapujXml(text)}</bunka>`));
      casti.push(`   </${element}>`);
   });
   casti.push('</tabulka>');
   return casti.join('\n');
}

//--- Stav editora tabulky (mriezka vo formulari otazky); bez DOM, testuje sa v tests/js/ ---
//stav: {riadky: pole poli retazcov, vystup: Set "riadok,stlpec" poli na vyplnenie, maHlavicku: bool, povolene: retazec}

//predvolena tabulka: hlavicka a dva riadky, tri stlpce
function novyStavTabulky(riadkov = 3, stlpcov = 3) {
   return {riadky: Array.from({length: riadkov}, () => Array(stlpcov).fill('')), vystup: new Set(), maHlavicku: true, povolene: ''};
}

//stav z vlozenej tabulky (parsujSchranku); po hlavicke musi ostat aspon jeden riadok tela
function stavZRiadkov(riadky, maHlavicku) {
   const stav = {riadky: riadky.map(r => r.slice()), vystup: new Set(), maHlavicku, povolene: ''};
   if (!stav.riadky.length) return novyStavTabulky();
   if (stav.riadky.length < prvyRiadokTela(stav) + 1) pridajRiadokTabulky(stav);
   return stav;
}

function prvyRiadokTela(stav) {
   return stav.maHlavicku ? 1 : 0;
}

function pridajRiadokTabulky(stav) {
   stav.riadky.push(Array(stav.riadky[0].length).fill(''));
}

function pridajStlpecTabulky(stav) {
   stav.riadky.forEach(r => r.push(''));
}

//zahodi indexy poli v odstranenom riadku/stlpci a posunie vyssie; os: 0 = riadok, 1 = stlpec
function posunVystup(stav, os, index) {
   stav.vystup = new Set(Array.from(stav.vystup).map(k => k.split(',').map(Number)).filter(p => p[os] !== index)
      .map(p => { if (p[os] > index) p[os]--; return p.join(','); }));
}

//hlavicka sa neodstranuje (riadi ju prepinac) a musi ostat aspon jeden riadok tela; vrati true, ak sa riadok odstranil
function odstranRiadokTabulky(stav, r) {
   if (r < prvyRiadokTela(stav) || stav.riadky.length - prvyRiadokTela(stav) <= 1) return false;
   stav.riadky.splice(r, 1);
   posunVystup(stav, 0, r);
   return true;
}

//musi ostat aspon jeden stlpec
function odstranStlpecTabulky(stav, c) {
   if (stav.riadky[0].length <= 1) return false;
   stav.riadky.forEach(r => r.splice(c, 1));
   posunVystup(stav, 1, c);
   return true;
}

//bunka hlavicky nemoze byt polom na vyplnenie
function prepniBunkuTabulky(stav, r, c) {
   if (r < prvyRiadokTela(stav)) return false;
   const kluc = `${r},${c}`;
   if (!stav.vystup.delete(kluc)) stav.vystup.add(kluc);
   return true;
}

//cely stlpec tela: ak su uz vsetky bunky polami, zrusi ich, inak ich nastavi vsetky
function prepniStlpecTabulky(stav, c) {
   const kluce = stav.riadky.map((_, r) => r).filter(r => r >= prvyRiadokTela(stav)).map(r => `${r},${c}`);
   const vsetky = kluce.every(k => stav.vystup.has(k));
   kluce.forEach(k => vsetky ? stav.vystup.delete(k) : stav.vystup.add(k));
}

function nastavHlavickuTabulky(stav, maHlavicku) {
   stav.maHlavicku = maHlavicku;
   if (maHlavicku) stav.riadky[0].forEach((_, c) => stav.vystup.delete(`0,${c}`));
   if (stav.riadky.length < prvyRiadokTela(stav) + 1) pridajRiadokTabulky(stav);
}

//znaky z textov poli na vyplnenie, kazdy raz, v poradi vyskytu (predvyplnenie povolenych znakov)
function povoleneZVystupu(stav) {
   const znaky = [];
   stav.riadky.forEach((r, i) => r.forEach((text, c) => {
      if (stav.vystup.has(`${i},${c}`)) Array.from(text).forEach(z => { if (!znaky.includes(z)) znaky.push(z); });
   }));
   return znaky.join('');
}

//ziadne pole a vsetky bunky prazdne (prepisanie takej tabulky sa nepotvrdzuje)
function stavJePrazdny(stav) {
   return stav.vystup.size === 0 && stav.riadky.every(r => r.every(text => text.trim() === ''));
}

function xmlTabulky(stav) {
   return zostavXmlTabulky(stav.riadky, stav.maHlavicku, stav.vystup, stav.povolene);
}
