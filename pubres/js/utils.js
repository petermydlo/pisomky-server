function terazFormatovany() {
   const teraz = new Date();
   teraz.setSeconds(0, 0);
   return teraz.getFullYear() + '-' + (teraz.getMonth()+1).toString().padStart(2, '0') + '-' + teraz.getDate().toString().padStart(2, '0') + 'T' + teraz.getHours().toString().padStart(2, '0') + ':' + teraz.getMinutes().toString().padStart(2, '0');
}

function zobrazNotifikaciu(text, typ = 'danger', hlavicka = 'Chyba', trvanie = 5000) {
   zabezpecToastKontajner(typ, hlavicka);
   document.getElementById('toastMessage').textContent = text;
   const feedback = document.getElementById('toastFeedback');
   feedback.classList.add('d-none');
   feedback.classList.remove('d-flex');

   setTimeout(() => {
      const el = document.getElementById('liveToast');
      const toast = new bootstrap.Toast(el, {autohide: false});
      toast.show();
      setTimeout(() => {
         bootstrap.Toast.getInstance(document.getElementById('liveToast'))?.hide();
      }, trvanie);
   }, 50);
}

function zabezpecToastKontajner(typ = 'danger', hlavicka = 'Chyba') {
   const staryToast = document.getElementById('liveToast');
   if (staryToast) {
      staryToast.dispatchEvent(new Event('hidden.bs.toast'));
      bootstrap.Toast.getInstance(staryToast)?.dispose();
      staryToast.closest('.toast-container').remove();
   }

   const toastHTML = `
      <div class="toast-container position-fixed top-0 end-0 mt-5 p-3">
         <div id="liveToast" class="toast hide border-0 shadow" data-bs-autohide="false" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header d-flex justify-content-between align-items-center border-0 py-1 text-bg-${typ}">
               <strong class="me-auto text-truncate">${hlavicka}</strong>
               <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body bg-${typ}-subtle">
               <div id="toastMessage" class="toast-text-area"></div>
            </div>
            <div id="toastFeedback" class="toast-footer border-top p-2 d-none justify-content-center gap-2 bg-light text-center">
               <small class="text-muted">Pomohlo?</small>
               <button class="btn btn-sm btn-outline-success feedback-btn" data-val="1">Ano</button>
               <button class="btn btn-sm btn-outline-danger feedback-btn" data-val="0">Nie</button>
            </div>
         </div>
      </div>`;
   const tpl = document.createElement('template');
   tpl.innerHTML = toastHTML.trim();
   const container = tpl.content.firstElementChild;
   document.body.appendChild(container);
   return new bootstrap.Toast(container.querySelector('#liveToast'));
}

document.addEventListener('click', (e) => {
   if (!e.target.matches('.feedback-btn')) return;
   const btn = e.target;
   const pomohlo = btn.dataset.val;
   const testId = btn.dataset.testId;
   const zapisId = btn.dataset.zapisId;
   document.getElementById('toastFeedback').innerHTML = "<small class='text-success fw-bold'>Ďakujeme!</small>";
   fetch('/ai/feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({ test_id: testId, val: pomohlo, zapis_id: zapisId })
   });
   setTimeout(() => {
      bootstrap.Toast.getInstance(document.getElementById('liveToast'))?.hide();
   }, 1500);
});
