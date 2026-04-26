document.addEventListener('DOMContentLoaded', () => {
   document.getElementById('loginForm').addEventListener('submit', (e) => {
      e.preventDefault();
      const kluc = document.getElementById('kluc').value;
      let adresa = '/' + kluc;
      if (document.getElementById('wm').checked)
         adresa += '?edit=true';
      window.location = adresa;
   });
});
