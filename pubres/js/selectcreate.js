document.addEventListener('DOMContentLoaded', () => {
   // toggle vyberu bez nutnosti drzat Ctrl
   document.getElementById('trieda').addEventListener('mousedown', (e) => {
      if (!e.target.matches('option')) return;
      e.preventDefault();
      e.target.selected = !e.target.selected;
      e.target.closest('select').dispatchEvent(new Event('change'));
   });

   const elPredmet = document.getElementById('predmet');
   const elKapitola = document.getElementById('kapitola');
   const elSkupina = document.getElementById('skupina');

   const updateSkupinaOptions = () => {
      const predmetVal = elPredmet.value.toLowerCase();
      const trieda = Array.from(document.getElementById('trieda').selectedOptions).map(o => o.value);
      const triedy = (trieda.length ? trieda : ['cela']).map(v => v.replace('.', '_').trim());
      elSkupina.querySelectorAll('option:not(.cela)').forEach(o => o.disabled = true);
      elSkupina.querySelectorAll('option.' + triedy.join('.')).forEach(o => {
         const predmetSkupiny = o.dataset.predmet;
         o.disabled = predmetSkupiny !== '' && predmetSkupiny !== predmetVal;
      });
   };

   elPredmet.addEventListener('change', () => {
      const predmetVal = elPredmet.value;
      elKapitola.querySelectorAll('option').forEach(o => o.disabled = true);
      elKapitola.querySelectorAll('option.' + predmetVal).forEach(o => o.disabled = false);
      const first = elKapitola.querySelector('option:not([disabled])');
      if (first) first.selected = true;
      updateSkupinaOptions();
   });

   document.getElementById('trieda').addEventListener('change', updateSkupinaOptions);

   elPredmet.dispatchEvent(new Event('change'));
});
