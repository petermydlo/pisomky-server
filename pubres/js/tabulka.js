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
