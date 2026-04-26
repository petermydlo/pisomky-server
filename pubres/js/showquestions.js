document.addEventListener('DOMContentLoaded', () => {
   document.addEventListener('change', (e) => {
      if (!e.target.matches('input.pause-check')) return;
      e.stopPropagation();
      const cb = e.target;
      const id = cb.dataset.id;
      const typ = cb.dataset.typ;
      const paused = cb.checked ? '0' : '1';
      fetch('/admin/setpaused', {
         method: 'POST',
         headers: {'Content-Type': 'application/x-www-form-urlencoded'},
         body: new URLSearchParams({ id, typ, paused })
      }).catch(() => {
         cb.checked = !cb.checked;
      });
   });
});
