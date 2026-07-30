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

document.addEventListener('DOMContentLoaded', () => {
   const elPredmet = document.getElementById('predmet');

   const addIcon = document.querySelector('.addPredmetIcon');
   if (addIcon) {
      addIcon.addEventListener('click', () => {
         const predmet = prompt('Skratka nového predmetu (napr. SXT4):');
         if (!predmet) return;
         postForm('/admin/process_predmet', {predmet, operacia: 'create'})
            .then(() => {
               const option = document.createElement('option');
               option.value = predmet;
               option.textContent = predmet;
               elPredmet.appendChild(option);
               elPredmet.value = predmet;
            })
            .catch(err => alert(err.message));
      });
   }

   const delIcon = document.querySelector('.delPredmetIcon');
   if (delIcon) {
      delIcon.addEventListener('click', () => {
         const predmet = elPredmet.value;
         const deletep = (elPredmet.dataset.deletep || '').split(/\s+/);
         if (!deletep.includes(predmet)) {
            alert(`Nemáte oprávnenie na vymazanie predmetu ${predmet}.`);
            return;
         }
         if (!confirm(`Naozaj vymazať CELÝ predmet ${predmet}? Otázky budú pred vymazaním zálohované.`)) return;
         postForm('/admin/process_predmet', {predmet, operacia: 'delete'})
            .then(() => {
               const option = elPredmet.querySelector(`option[value="${CSS.escape(predmet)}"]`);
               if (option) option.remove();
            })
            .catch(err => alert(err.message));
      });
   }
});
