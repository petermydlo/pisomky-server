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
      const triedy = (trieda.length ? trieda : ['cela']).map(v => v.replaceAll('.', '_').trim());
      elSkupina.querySelectorAll('option:not(.cela)').forEach(o => o.disabled = true);
      elSkupina.querySelectorAll('option.' + triedy.map(t => CSS.escape(t)).join('.')).forEach(o => {
         const predmetSkupiny = o.dataset.predmet ?? '';   //moznost "cela trieda" nema data-predmet a nesmie sa zakazat
         o.disabled = predmetSkupiny !== '' && predmetSkupiny !== predmetVal;
      });
      //zakazana vybrana skupina sa neodosle a server by potichu vytvoril sadu pre celu triedu
      if (elSkupina.selectedOptions[0]?.disabled) elSkupina.value = '-';
   };

   elPredmet.addEventListener('change', () => {
      const predmetVal = elPredmet.value;
      elKapitola.querySelectorAll('option').forEach(o => o.disabled = true);
      elKapitola.querySelectorAll('option.' + CSS.escape(predmetVal)).forEach(o => o.disabled = false);
      const first = elKapitola.querySelector('option:not([disabled])');
      if (first) first.selected = true;
      updateSkupinaOptions();
   });

   document.getElementById('trieda').addEventListener('change', updateSkupinaOptions);

   elPredmet.dispatchEvent(new Event('change'));
});
