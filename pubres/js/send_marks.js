$(function() {
   $("#ulozit").on("click", function(e) {
      e.preventDefault();
      const kluc = $("#hlavicka").attr("kluc");
      const udaje = new FormData();
      udaje.append("predmet", $("#hlavicka").attr("predmet"));
      udaje.append("trieda", $("#hlavicka").attr("trieda"));
      udaje.append("skupina", $("#hlavicka").attr("skupina"));
      udaje.append("kapitola", $("#hlavicka").attr("kapitola"));
      udaje.append("dat", $("#hlavicka").attr("dat"));
      $("#odpovede input[type='radio'][name^='h_']:checked, #odpovede input[type='radio'][name^='bh_']:checked").each(function() {
         udaje.append($(this).attr("name"), $(this).parent().text());
      });
      $("#odpovede input[type='number'][id^='h_'], #odpovede input[type='number'][id^='bh_'], #odpovede input[type='text'][id^='k_']").each(function() {
         udaje.append($(this).attr("id"), $(this).val());
      });
      $.ajax({
         url: "/admin/savemarks/" + kluc,
         method: "POST",
         data: udaje,
         processData: false,
         contentType: false
      })
      .done(function(data, status, xhr) {
         zobrazNotifikaciu("Známky úspešne uložené.", "success", "Úspech");
      })
      .fail(function(xhr, statusText, error) {
         console.error("AJAX Error:", {
            status: xhr.status,
            statusText: statusText,
            error: error,
            response: xhr.responseText
         });
         switch(xhr.status) {
            case 500: zobrazNotifikaciu("Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr."); break;
            default: zobrazNotifikaciu("Vyskytla sa chyba! Skúste to prosím neskôr.");
         }
      });
   });
});
