document.addEventListener('DOMContentLoaded', () => {
   // toggle vyberu bez nutnosti drzat Ctrl
   document.getElementById('trieda').addEventListener('mousedown', (e) => {
      if (e.target.tagName !== 'OPTION') return;
      e.preventDefault();
      e.target.selected = !e.target.selected;
      e.target.closest('select').dispatchEvent(new Event('change'));
   });

   const elPredmet = document.getElementById('predmet');
   const elKapitola = document.getElementById('kapitola');
   const elSkupina = document.getElementById('skupina');

   elPredmet.addEventListener('change', () => {
      const predmetVal = elPredmet.value;
      elKapitola.querySelectorAll('option').forEach(o => o.disabled = true);
      elKapitola.querySelectorAll('option.' + predmetVal).forEach(o => o.disabled = false);
      const first = elKapitola.querySelector('option:not([disabled])');
      if (first) first.selected = true;
   });

   document.getElementById('trieda').addEventListener('change', () => {
      const select = document.getElementById('trieda');
      let trieda = Array.from(select.selectedOptions).map(o => o.value);
      if (!trieda.length) trieda = ['cela'];
      const triedy = trieda.map(v => v.replace('.', '_').trim());
      elSkupina.querySelectorAll('option:not(.cela)').forEach(o => o.disabled = true);
      elSkupina.querySelectorAll('option.' + triedy.join('.')).forEach(o => o.disabled = false);
   });

   elPredmet.dispatchEvent(new Event('change'));
});
