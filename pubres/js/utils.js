function zobrazNotifikaciu(text, typ = "danger", hlavicka = "Chyba", trvanie = 5000) {
   zabezpecToastKontajner(typ, hlavicka);
   $("#toastMessage").text(text);
   $("#toastFeedback").addClass("d-none").removeClass("d-flex");

   setTimeout(() => {
      const el = $("#liveToast")[0];
      const toast = new bootstrap.Toast(el, {autohide: false});
      toast.show();

      setTimeout(() => {
         if ($("#liveToast").length) bootstrap.Toast.getInstance($("#liveToast")[0])?.hide();
      }, trvanie);
   }, 50);
}

function zabezpecToastKontajner(typ = "danger", hlavicka = "Chyba") {
   const $staryToast = $("#liveToast");
   if ($staryToast.length > 0) {
      const inst = bootstrap.Toast.getInstance($staryToast[0]);
      if (inst) inst.dispose();
      $staryToast.closest('.toast-container').remove();
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
   const $novyToastContainer = $(toastHTML);
   $("body").append($novyToastContainer);
   const toastEl = $novyToastContainer.find('#liveToast')[0];
   const bsToast = new bootstrap.Toast(toastEl);
   return bsToast;
}

$(document).on("click", ".feedback-btn", function() {
   const $btn = $(this);
   const pomohlo = $btn.data("val");
   const testId = $btn.data("test-id");
   const zapisId = $btn.data("zapis-id");
   const $footer = $("#toastFeedback");
   $footer.html("<small class='text-success fw-bold'>Ďakujeme!</small>");
   $.post("/ai/feedback", {
      test_id: testId,
      val: pomohlo,
      zapis_id: zapisId
   });
   setTimeout(() => {
      const inst = bootstrap.Toast.getInstance($("#liveToast")[0]);
      if (inst) inst.hide();
   }, 1500);
});
