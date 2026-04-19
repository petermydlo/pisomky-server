$(function() {
   var autosaveTimer = null;

   function setIcon(stav) {
      var icon = $("#save-icon");
      icon.removeClass("bi-cloud-check bi-cloud-upload bi-cloud-slash text-success text-warning text-primary text-danger");
      if (stav === "ok")          icon.addClass("bi-cloud-check text-success");
      else if (stav === "saving") icon.addClass("bi-cloud-upload text-primary");
      else if (stav === "unsaved") icon.addClass("bi-cloud-slash text-warning");
      else if (stav === "error")  icon.addClass("bi-cloud-slash text-danger");
   }

   function saveAnswers(withAnswers, withFiles) {
      setIcon("saving");
      var kluc = $("#hlavicka").attr("kluc");
      var udaje = new FormData();
      udaje.append("predmet", $("#hlavicka").attr("predmet"));
      udaje.append("trieda", $("#hlavicka").attr("trieda"));
      udaje.append("skupina", $("#hlavicka").attr("skupina"));
      udaje.append("kapitola", $("#hlavicka").attr("kapitola"));
      if (withAnswers) {
         $("#odpovede input:radio:checked:not([form])").each(function() {
            udaje.append($(this).attr("name"), $(this).attr("value"));
         });
         $("#odpovede input:text.odpoved").each(function() {
            udaje.append($(this).attr("id"), $(this).val());
         });
         if (withFiles && $("#files").length) {
            $.each($("#files")[0].files, function(i, file) {
               udaje.append("subory", file);
            });
         }
      }
      $.ajax({
         url: "/saveanswers/" + kluc,
         method: "POST",
         data: udaje,
         processData: false,
         contentType: false
      })
      .done(function() {
         setIcon("ok");
      })
      .fail(function(xhr) {
         setIcon("error");
         if (xhr.status === 403)
            zobrazNotifikaciu("Čas na odovzdanie odpovedí vypršal!");
         else if (xhr.status === 500)
            zobrazNotifikaciu("Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr.");
         else
            zobrazNotifikaciu("Vyskytla sa chyba! Skúste to prosím neskôr.");
      });
   }

   function scheduleAutosave() {
      clearTimeout(autosaveTimer);
      setIcon("unsaved");
      autosaveTimer = setTimeout(function() {
         saveAnswers(true, false);
      }, 3000);
   }

   $("#save-status").on("click", function() {
      var btn = $(this);
      if (btn.data("disabled")) return;
      btn.data("disabled", true).addClass("disabled");
      setTimeout(function() { btn.data("disabled", false).removeClass("disabled"); }, 10000);
      clearTimeout(autosaveTimer);
      saveAnswers(true, true);
   });

   $("#odpovede").on("change", "input.odpoved", function() {
      scheduleAutosave();
   });

   $("#odpovede").on("input", "input[type='text'].odpoved", function() {
      scheduleAutosave();
   });

   if (!$(location).attr("pathname").includes("/admin"))
      saveAnswers(false, false);
});
