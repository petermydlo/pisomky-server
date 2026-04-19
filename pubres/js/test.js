$(function() {
   // Rating hviezdicky - postupne rozsvecovanie
   $('.rating-wrap').each(function() {
      const $wrap = $(this);
      const $stars = $wrap.find('.rating-star');
      $wrap.find('input[type=radio]').on('change', function() {
         const idx = $wrap.find('input[type=radio]').index($(this));
         $stars.each(function(j) {
            $(this).css('color', j < idx ? '#ffc107' : '#ccc');
         });
      });
   });

   // Kliknutie na ikonu žiarovky
   $(".ai-napoveda-btn").on("click", function() {
      const $btn = $(this);
      const otazkaId = $btn.attr("data-otazka-id");
      const testId = $btn.attr("data-test-id");
      $btn.css("opacity", "0.5").css("pointer-events", "none");

      poziadajAINapovedu(otazkaId, testId).finally(() => {
         $btn.css("opacity", "1").css("pointer-events", "auto");
      });

      // uloz do feedback tlacidiel
      $("#toastFeedback").find(".feedback-btn")
         .attr("data-test-id", testId);
      });

   //odosle otazku na AI a zobrazi odpoved cez SSE streaming
   function poziadajAINapovedu(otazkaId, testId) {
      const toast = zabezpecToastKontajner("warning", "AI Help (experimental)", false);
      const $toastMessage = $("#toastMessage");
      $toastMessage.html("<strong>AI is thinking...</strong>");
      const $toastFeedback = $("#toastFeedback");
      $toastFeedback.addClass("d-none").removeClass("d-flex");
      toast.show();

      return new Promise((resolve) => {
         const params = new URLSearchParams({ test_id: testId, otazka_id: otazkaId });
         const es = new EventSource(`/ai/napoveda?${params.toString()}`);
         let hintText = '';
         let completed = false;

         es.addEventListener('meta', (e) => {
            const data = JSON.parse(e.data);
            $toastFeedback.find(".feedback-btn").attr("data-zapis-id", data.zapis_id);
         });

         es.addEventListener('chunk', (e) => {
            const data = JSON.parse(e.data);
            hintText += data.text;
            const newlineIdx = hintText.indexOf('\n');
            $toastMessage.text(newlineIdx > -1 ? hintText.slice(0, newlineIdx) : hintText);
         });

         es.addEventListener('done', (e) => {
            completed = true;
            es.close();
            $toastFeedback.removeClass("d-none").addClass("d-flex");
            setTimeout(() => toast.hide(), 20000);
            resolve();
         });

         es.addEventListener('napoveda_error', (e) => {
            completed = true;
            const data = JSON.parse(e.data);
            $toastMessage.text(data.error);
            es.close();
            resolve();
         });

         es.onerror = () => {
            if (completed) return;
            $toastMessage.text("Chyba pri spojení s AI.");
            es.close();
            resolve();
         };
      });
   }

   //zmeni farbu pozadia otazky podla zaskrtnuteho pomocneho radia
   $(".radio.col-up input").on("change", function() {
      const $checked_radio = $(this);
      const $changed_div = $(this).closest(".flex-container-table-znenie");
      $changed_div.removeClass().addClass("flex-container-table-znenie").addClass($checked_radio.val());
   });

   //uzamkne test, a vrati uzivatela na domovsku stranku
   $("#home").on("click", function() {
      const params = new URLSearchParams(window.location.search);
      let hlaska = "POZOR! Chystáte sa ukončiť písomku!\nChcete pokračovať?";
      if (params.get("q") === "w")
         hlaska = "POZOR! Všetky neodoslané zmeny v písomke budú zahodené!\nChcete pokračovať?";
      if(confirm(hlaska)) {
         const coeff = 1000 * 60 * 1; // zaokruhlovanie na 1 minutu
         const teraz = new Date(Math.round(Date.now() / coeff) * coeff);
         const novy = teraz.getFullYear() + "-" + (teraz.getMonth()+1).toString().padStart(2, '0') + "-" + teraz.getDate().toString().padStart(2, '0') + "T" + teraz.getHours().toString().padStart(2, '0') + ":" + teraz.getMinutes().toString().padStart(2, '0');
         const data = {
            predmet:$("#hlavicka").attr("predmet"),
            trieda:$("#hlavicka").attr("trieda"),
            skupina:$("#hlavicka").attr("skupina"),
            kapitola:$("#hlavicka").attr("kapitola")
         };
         const kluc = $("#hlavicka").attr("kluc");
         data.stop = novy;
         $.ajax({
            url: "/stoptime/" + kluc,
            data: data,
            method: "POST"
         })
         .fail(function(xhr, statusText, error) {
            console.error("AJAX Error:", {
               status: xhr.status,
               statusText: statusText,
               error: error,
               response: xhr.responseText
            });
            switch(xhr.status) {
               case 404: zobrazNotifikaciu("Test nenájdený!"); break;
               case 403: zobrazNotifikaciu("Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!"); break;
               case 500: zobrazNotifikaciu("Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr."); break;
               default: zobrazNotifikaciu("Vyskytla sa chyba! Skúste to prosím neskôr.");
            };
         });
         return true;
      }
      else
         return false;
   });
});
