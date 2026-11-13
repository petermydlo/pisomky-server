//Maly modalny dialog s textovymi polami (nahrada prompt()).
//polia: [{id, popis, hodnota, povinne, vzor (RegExp), chyba (text pri nesplnenom vzore), pomocka, maxDlzka}]
//ulozit(hodnoty) vrati Promise: po uspechu sa dialog zavrie, pri chybe sa jej sprava ukaze v dialogu a ostane otvoreny
function otvorDialog({nadpis, polia, potvrdit, ulozit}) {
   const dialog = document.createElement('dialog');
   dialog.className = 'dialog-okno';
   const form = document.createElement('form');
   dialog.appendChild(form);

   const hlavicka = document.createElement('h2');
   hlavicka.textContent = nadpis;
   form.appendChild(hlavicka);

   const vstupy = polia.map(pole => {
      const label = document.createElement('label');
      label.append(pole.popis);
      const vstup = document.createElement('input');
      vstup.type = 'text';
      vstup.className = 'form-control';
      vstup.value = pole.hodnota || '';
      vstup.autocomplete = 'off';
      vstup.spellcheck = false;
      if (pole.maxDlzka) vstup.maxLength = pole.maxDlzka;
      label.append(vstup);
      if (pole.pomocka) {
         const pomocka = document.createElement('small');
         pomocka.textContent = pole.pomocka;
         label.append(pomocka);
      }
      form.appendChild(label);
      return vstup;
   });

   const chyba = document.createElement('div');
   chyba.className = 'dialog-chyba';
   form.appendChild(chyba);

   const tlacidla = document.createElement('div');
   tlacidla.className = 'dialog-tlacidla';
   const zrus = document.createElement('button');
   zrus.type = 'button';
   zrus.className = 'btn btn-outline-secondary';
   zrus.textContent = 'Zrušiť';
   const ok = document.createElement('button');
   ok.type = 'submit';
   ok.className = 'btn btn-outline-primary';
   ok.textContent = potvrdit;
   tlacidla.append(zrus, ok);
   form.appendChild(tlacidla);

   const hodnota = (i) => vstupy[i].value.trim();
   const hodnoty = () => Object.fromEntries(polia.map((pole, i) => [pole.id, hodnota(i)]));
   const zlyVzor = () => polia.find((pole, i) => hodnota(i) !== '' && pole.vzor && !pole.vzor.test(hodnota(i)));
   const chybaPovinne = () => polia.some((pole, i) => pole.povinne && hodnota(i) === '');

   function aktualizuj() {
      const zle = zlyVzor();
      chyba.textContent = zle ? zle.chyba : '';
      ok.disabled = !!zle || chybaPovinne();
   }
   vstupy.forEach(vstup => vstup.addEventListener('input', aktualizuj));

   form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (ok.disabled) return;
      ok.disabled = true;
      Promise.resolve(ulozit(hodnoty()))
         .then(() => dialog.close())
         .catch(err => {
            chyba.textContent = err.message;
            ok.disabled = false;
         });
   });
   zrus.addEventListener('click', () => dialog.close());
   dialog.addEventListener('close', () => dialog.remove());

   aktualizuj();
   document.body.appendChild(dialog);
   dialog.showModal();
   vstupy[0].select();
}

//Modalne potvrdenie (nahrada confirm()); vrati Promise<boolean>: true len po stlaceni potvrdzovacieho tlacidla, Esc a Zrusit davaju false
//nebezpecne: potvrdzovacie tlacidlo je cervene a predvoleny fokus je na Zrusit (Enter nic nezmaze)
function potvrdDialog({nadpis, text, potvrdit = 'Potvrdiť', zrusit = 'Zrušiť', nebezpecne = false}) {
   return new Promise(resolve => {
      const dialog = document.createElement('dialog');
      dialog.className = 'dialog-okno';
      const form = document.createElement('form');
      dialog.appendChild(form);

      const hlavicka = document.createElement('h2');
      hlavicka.textContent = nadpis;
      const odstavec = document.createElement('p');
      odstavec.className = 'dialog-text';
      odstavec.textContent = text;
      form.append(hlavicka, odstavec);

      const tlacidla = document.createElement('div');
      tlacidla.className = 'dialog-tlacidla';
      const zrus = document.createElement('button');
      zrus.type = 'button';
      zrus.className = 'btn btn-outline-secondary';
      zrus.textContent = zrusit;
      const ok = document.createElement('button');
      ok.type = 'submit';
      ok.className = 'btn btn-outline-primary';
      ok.textContent = potvrdit;
      if (nebezpecne) ok.className = 'btn btn-outline-danger';
      tlacidla.append(zrus, ok);
      form.appendChild(tlacidla);

      form.addEventListener('submit', (e) => {
         e.preventDefault();
         dialog.close('ano');
      });
      zrus.addEventListener('click', () => dialog.close());
      dialog.addEventListener('close', () => {
         resolve(dialog.returnValue === 'ano');
         dialog.remove();
      });

      document.body.appendChild(dialog);
      dialog.showModal();
      (nebezpecne ? zrus : ok).focus();
   });
}

//Modalne oznamenie s jednym tlacidlom (nahrada alert()); vrati Promise, ktory sa splni po zatvoreni
function oznamDialog({nadpis = 'Chyba', text}) {
   return new Promise(resolve => {
      const dialog = document.createElement('dialog');
      dialog.className = 'dialog-okno';
      const form = document.createElement('form');
      dialog.appendChild(form);

      const hlavicka = document.createElement('h2');
      hlavicka.textContent = nadpis;
      const odstavec = document.createElement('p');
      odstavec.className = 'dialog-text';
      odstavec.textContent = text;
      const tlacidla = document.createElement('div');
      tlacidla.className = 'dialog-tlacidla';
      const ok = document.createElement('button');
      ok.type = 'submit';
      ok.className = 'btn btn-outline-primary';
      ok.textContent = 'Zavrieť';
      tlacidla.appendChild(ok);
      form.append(hlavicka, odstavec, tlacidla);

      form.addEventListener('submit', (e) => {
         e.preventDefault();
         dialog.close();
      });
      dialog.addEventListener('close', () => {
         dialog.remove();
         resolve();
      });

      document.body.appendChild(dialog);
      dialog.showModal();
      ok.focus();
   });
}

//Modalny vyber zaskrtavacich poli (napr. co vymazat); vrati Promise: objekt {id: boolean} po potvrdeni, inak null
//moznosti: [{id, popis, zapnute, aktivne}]; neaktivna moznost sa nezobrazi ako zaskrtnuta ani sa neda zmenit
//asponJedno: potvrdit sa da len so zaskrtnutou aspon jednou moznostou (pri volitelnych moznostiach false)
function vyberDialog({nadpis, text, moznosti, potvrdit, nebezpecne = false, asponJedno = true}) {
   return new Promise(resolve => {
      const dialog = document.createElement('dialog');
      dialog.className = 'dialog-okno';
      const form = document.createElement('form');
      dialog.appendChild(form);

      const hlavicka = document.createElement('h2');
      hlavicka.textContent = nadpis;
      const odstavec = document.createElement('p');
      odstavec.className = 'dialog-text';
      odstavec.textContent = text;
      form.append(hlavicka, odstavec);

      const vstupy = moznosti.map(m => {
         const label = document.createElement('label');
         label.className = 'dialog-moznost';
         const vstup = document.createElement('input');
         vstup.type = 'checkbox';
         vstup.checked = m.aktivne && m.zapnute;
         vstup.disabled = !m.aktivne;
         label.append(vstup, m.popis);
         form.appendChild(label);
         return vstup;
      });

      const tlacidla = document.createElement('div');
      tlacidla.className = 'dialog-tlacidla';
      const zrus = document.createElement('button');
      zrus.type = 'button';
      zrus.className = 'btn btn-outline-secondary';
      zrus.textContent = 'Zrušiť';
      const ok = document.createElement('button');
      ok.type = 'submit';
      ok.className = 'btn btn-outline-primary';
      ok.textContent = potvrdit;
      if (nebezpecne) ok.className = 'btn btn-outline-danger';
      tlacidla.append(zrus, ok);
      form.appendChild(tlacidla);

      const aktualizuj = () => { ok.disabled = asponJedno && !vstupy.some(v => v.checked); };
      vstupy.forEach(v => v.addEventListener('change', aktualizuj));
      aktualizuj();

      form.addEventListener('submit', (e) => {
         e.preventDefault();
         dialog.close('ano');
      });
      zrus.addEventListener('click', () => dialog.close());
      dialog.addEventListener('close', () => {
         resolve(dialog.returnValue === 'ano' ? Object.fromEntries(moznosti.map((m, i) => [m.id, vstupy[i].checked])) : null);
         dialog.remove();
      });

      document.body.appendChild(dialog);
      dialog.showModal();
      (nebezpecne ? zrus : ok).focus();
   });
}
