document.addEventListener('DOMContentLoaded', () => {
   const elPredmet = document.getElementById('predmet');

   const addIcon = document.querySelector('.addPredmetIcon');
   if (addIcon) {
      addIcon.addEventListener('click', () => {
         otvorDialog({
            nadpis: 'Nový predmet',
            polia: [{id: 'predmet', popis: 'Skratka predmetu', povinne: true, vzor: /^[A-Z0-9]{2,10}$/, chyba: 'Skratka má mať 2 až 10 veľkých písmen alebo číslic.', pomocka: 'napr. SXT4', maxDlzka: 10}],
            potvrdit: 'Vytvoriť',
            ulozit: ({predmet}) => postForm('/admin/process_predmet', {predmet, operacia: 'create'})
               .then(() => {
                  const option = document.createElement('option');
                  option.value = predmet;
                  option.textContent = predmet;
                  elPredmet.appendChild(option);
                  elPredmet.value = predmet;
               }),
         });
      });
   }

   const delIcon = document.querySelector('.delPredmetIcon');
   if (delIcon) {
      delIcon.addEventListener('click', () => {
         const predmet = elPredmet.value;
         const deletep = (elPredmet.dataset.deletep || '').split(/\s+/);
         if (!deletep.includes(predmet)) {
            oznamDialog({text: `Nemáte oprávnenie na vymazanie predmetu ${predmet}.`});
            return;
         }
         potvrdDialog({nadpis: 'Vymazať predmet', text: `Naozaj vymazať CELÝ predmet ${predmet}? Otázky budú pred vymazaním zálohované.`, potvrdit: 'Vymazať', nebezpecne: true}).then(potvrdene => {
            if (!potvrdene) return;
            postForm('/admin/process_predmet', {predmet, operacia: 'delete'})
               .then(() => {
                  const option = elPredmet.querySelector(`option[value="${CSS.escape(predmet)}"]`);
                  if (option) option.remove();
               })
               .catch(err => oznamDialog({text: err.message}));
         });
      });
   }
});
