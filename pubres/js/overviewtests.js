$(function() {
   //vykona zmenu tabu podla hash v URL
   function onHashChange() {
      const hash = window.location.hash;
      const $tab = hash ? $("div.nav").find("[data-bs-toggle='tab'][href='" + hash + "']") : null;
      if ($tab && $tab.length)
         $tab.tab("show");
      else {
         history.replaceState(null, '', window.location.pathname);
         $("div.nav").find("[data-bs-toggle='tab']:first").tab("show");
      }
   };

   //zmeni fragment pri vybrati tabu
   $("[data-bs-toggle='tab']").on("click", function(e) {
      parent.location.hash = $(this).attr("href");
   });

   //formatuje aktualny cas na YYYY-MM-DDTHH:MM
   function terazFormatovany() {
      const coeff = 1000 * 60;
      const teraz = new Date(Math.round(Date.now() / coeff) * coeff);
      return teraz.getFullYear() + "-" + (teraz.getMonth()+1).toString().padStart(2, '0') + "-" + teraz.getDate().toString().padStart(2, '0') + "T" + teraz.getHours().toString().padStart(2, '0') + ":" + teraz.getMinutes().toString().padStart(2, '0');
   }

   //validuje format YYYY-MM-DDTHH:MM
   function jeValidnyCas(val) {
      return /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(val.trim());
   }

   //odosle zmenu casu na server
   function odosliZmenuCasu(trigger, starypolicko, novy) {
      const data = {
         predmet: trigger.closest(".tab-pane.active").attr("id"),
         trieda:  trigger.closest("div.skupina").find("#trieda").text(),
         skupina: trigger.closest("div.skupina").find("#skupina").text(),
         kapitola:trigger.closest("div.skupina").find("#kapitola").text()
      };
      if (trigger.is(".startT, .stopT"))
         data.kluc = trigger.attr("id");
      if (trigger.is(".startS, .startT"))
         data.start = novy;
      else
         data.stop = novy;

      $.ajax({ url: "/admin/changetime", data: data, method: "POST" })
      .done(function() {
         starypolicko.text(novy);
         const cell = starypolicko.closest("div");
         cell.css("background-color", "rgba(var(--bs-success-rgb), 0.5)");
         setTimeout(function() { cell.css("background-color", ""); }, 1500);
      })
      .fail(function(xhr, statusText, error) {
         console.error("AJAX Error:", {
            status: xhr.status,
            statusText: statusText,
            error: error,
            response: xhr.responseText
         });
         const cell = starypolicko.closest("div");
         cell.css("background-color", "rgba(var(--bs-danger-rgb), 0.5)");
         setTimeout(function() { cell.css("background-color", ""); }, 1500);
         switch(xhr.status) {
            case 404: zobrazNotifikaciu("Testy nenájdené!"); break;
            case 403: zobrazNotifikaciu("Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!"); break;
            case 500: zobrazNotifikaciu("Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr."); break;
            default:  zobrazNotifikaciu("Vyskytla sa chyba! Skúste to prosím neskôr.");
         }
      });
   }

   //zmeni cas skupiny testov alebo jedneho testu
   $(".startS, .stopS, .startT, .stopT").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();

      //zatvorime vsetky ostatne otvorene inputy
      $(".casInput").each(function() {
         const fn = $(this).data("zavriet");
         if (fn) fn();
      });

      //ak uz je otvoreny input v tejto bunke, ignorujeme klik
      const $parentDiv = $(this).parent();
      if ($parentDiv.find(".casInput").length) return;

      const $pen = $(this);
      const starypolicko = $pen.siblings("span").first();
      const stary = starypolicko.text().trim();

      //CTRL+click prefilluje aktualny cas ale este neodosle
      const predvyplneny = event.ctrlKey ? terazFormatovany() : stary;

      //vytvorime inline input s potvrdenim a zrusenim
      const $input = $("<input>").addClass("casInput").attr("type", "text").attr("title", "Formát: YYYY-MM-DDTHH:MM").val(predvyplneny);
      const $btns   = $("<div>").addClass("casBtns");
      const $btnOk  = $("<span>").addClass("casBtn casBtn-ok").attr("title", "Potvrdiť").html("✔");
      const $btnDel = $("<span>").addClass("casBtn casBtn-del").attr("title", "Vymazať čas").html("🗑");
      const $btnX   = $("<span>").addClass("casBtn casBtn-cancel").attr("title", "Zrušiť").html("✖");
      $btns.append($btnOk, $btnDel, $btnX);

      //skryjeme stary text a pero
      starypolicko.hide();
      $pen.hide();
      $parentDiv.append($input, $btns);
      $input.trigger("focus").trigger("select");

      //docasne vypneme collapse na rodicovskom div
      const $collapseTarget = $parentDiv.closest("[data-bs-toggle='collapse']");
      $collapseTarget.attr("data-bs-toggle-disabled", $collapseTarget.attr("data-bs-toggle"));
      $collapseTarget.removeAttr("data-bs-toggle");

      function zavriet() {
         $input.remove(); $btns.remove();
         starypolicko.show();
         $pen.css("display", "");
         //obnovime collapse
         $collapseTarget.attr("data-bs-toggle", $collapseTarget.attr("data-bs-toggle-disabled"));
         $collapseTarget.removeAttr("data-bs-toggle-disabled");
      }

      //ulozime zavriet na input aby sme ho mohli volat zvonka
      $input.data("zavriet", zavriet);

      function potvrdit() {
         const novy = $input.val().trim();
         if (novy === stary) { zavriet(); return; }
         if (novy !== '' && !jeValidnyCas(novy)) {
            $input.addClass("is-invalid");
            $input.attr("title", "Neplatný formát. Použite YYYY-MM-DDTHH:MM");
            return;
         }
         zavriet();
         odosliZmenuCasu($pen, starypolicko, novy);
      }

      $btnOk.on("click",  function(e) { e.stopPropagation(); potvrdit(); });
      $btnDel.on("click", function(e) { e.stopPropagation(); zavriet(); odosliZmenuCasu($pen, starypolicko, " "); });
      $btnX.on("click",   function(e) { e.stopPropagation(); zavriet(); });

      $input.on("keydown", function(e) {
         if (e.key === "Enter")  { e.stopPropagation(); potvrdit(); }
         if (e.key === "Escape") { e.stopPropagation(); zavriet(); }
      });
   });

   //odhlasi uzivatela a presmeruje na uvodnu obrazovku
   $(".autor").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();
         $.ajax({
            method: "GET",
            url: "/admin",
            username: "user",
            password: "password",
            headers: {"Authorization": "Basic xxx"}
         })
         .done(function(data, status, xhr) {
            zobrazNotifikaciu("Na odhlásenie, prosím, zatvorte toto okno prezerača.", "info", "Informácia");
         })
         .fail(function(xhr) {
            window.location = "/";
         });
   });

   //vymaze skupinu testov
   $(".del").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();
      const predmet = $(this).closest(".tab-pane.active").attr("id");
      const trieda = $(this).closest("div.grid").find("#trieda").text();
      const skupina = $(this).closest("div.grid").find("#skupina").text();
      const kapitola = $(this).closest("div.grid").find("#kapitola").text();
      const potvrdenie = confirm("Naozaj chcete vymazať test " + predmet + ':' + trieda + skupina + ':' + kapitola + "?");
      if (potvrdenie)
         $.ajax({
            method: "DELETE",
            url: "/admin/deletetests",
            data: {
               predmet:predmet,
               trieda:trieda,
               skupina:skupina,
               kapitola:kapitola
            }
         })
         .done(function(data, status, xhr) {
            parent.location.hash = xhr.responseText;
            location.reload();
         })
         .fail(function(xhr, statusText, error) {
            console.error("AJAX Error:", {
               status: xhr.status,
               statusText: statusText,
               error: error,
               response: xhr.responseText
            });
            switch(xhr.status) {
               case 404: zobrazNotifikaciu("Testy nenájdené!"); break;
               case 403: zobrazNotifikaciu("Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!"); break;
               case 500: zobrazNotifikaciu("Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr."); break;
               default: zobrazNotifikaciu("Vyskytla sa chyba! Skúste to prosím neskôr.");
            };
         });
   });

   //zobrazi statistiku pre skupinu testov
   $(".groupstatistics").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();
      const predmet = $(this).closest(".tab-pane.active").attr("id");
      const trieda = $(this).closest("div.grid").find("#trieda").text();
      const skupina = $(this).closest("div.grid").find("#skupina").text();
      const kapitola = $(this).closest("div.grid").find("#kapitola").text();
      const $form = $("<form method='POST' action='/admin/groupstatistics'>");
      $form.append($('<input type="hidden" name="predmet">').val(predmet));
      $form.append($('<input type="hidden" name="trieda">').val(trieda));
      $form.append($('<input type="hidden" name="skupina">').val(skupina));
      $form.append($('<input type="hidden" name="kapitola">').val(kapitola));
      $('body').append($form);
      $form.submit();
   });

   //zobrazi feedback report pre skupinu testov
   $(".feedback").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();
      const predmet = $(this).closest(".tab-pane.active").attr("id");
      const trieda = $(this).closest("div.grid").find("#trieda").text();
      const skupina = $(this).closest("div.grid").find("#skupina").text();
      const kapitola = $(this).closest("div.grid").find("#kapitola").text();
      const $form = $("<form method='POST' action='/admin/feedbackreport'>");
      $form.append($('<input type="hidden" name="predmet">').val(predmet));
      $form.append($('<input type="hidden" name="trieda">').val(trieda));
      $form.append($('<input type="hidden" name="skupina">').val(skupina));
      $form.append($('<input type="hidden" name="kapitola">').val(kapitola));
      $('body').append($form);
      $form.submit();
   });

   //vytlaci skupinu kodov, testov alebo rieseni
   $(".codes, .tests, .results").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();
      const predmet = $(this).closest(".tab-pane.active").attr("id");
      const trieda = $(this).closest("div.grid").find("#trieda").text();
      const skupina = $(this).closest("div.grid").find("#skupina").text();
      const kapitola = $(this).closest("div.grid").find("#kapitola").text();
      const url = $(this).hasClass("results") ? "/admin/downloadresults" : $(this).hasClass("tests") ? "/admin/downloadtests" : "/admin/downloadcodes";
      $.ajax({
         method: "POST",
         url: url,
         data: {
            predmet:predmet,
            trieda:trieda,
            skupina:skupina,
            kapitola:kapitola
         },
         xhr: function() {
            const xhr = new XMLHttpRequest();
            xhr.responseType = "blob";
            return xhr;
         }
      })
      .done(function(data, status, xhr) {
         const type = xhr.getResponseHeader('Content-Type');
         let filename = "";
         const disposition = xhr.getResponseHeader('Content-Disposition');
         if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1])
               filename = matches[1].replace(/['"]/g, '');
         }
         const blob = new Blob([data], {type: type});
         const url = window.URL || window.webkitURL;
         const link = url.createObjectURL(blob);
         const $a = $("<a/>", {"download": filename, "href": link});
         $("body").append($a);
         $a[0].click();
         $a.remove();
         url.revokeObjectURL(link);
      })
      .fail(function(xhr, statusText, error) {
         console.error("AJAX Error:", {
            status: xhr.status,
            statusText: statusText,
            error: error,
            response: xhr.responseText
         });
         switch(xhr.status) {
            case 404: zobrazNotifikaciu("Testy nenájdené!"); break;
            case 403: zobrazNotifikaciu("Nemáte oprávnenie na danú akciu. Kontaktujte svojho administrátora!"); break;
            case 500: zobrazNotifikaciu("Vyskytla sa vnútorná chyba servera! Skúste to prosím neskôr."); break;
            default: zobrazNotifikaciu("Vyskytla sa chyba! Skúste to prosím neskôr.");
         };
      });
   });

   //regeneruje otazky v skupine testov (len ak nie su odpovede)
   $(".regenerate:not(.disabled)").on("click", function(event) {
      event.stopPropagation();
      event.preventDefault();
      const predmet = $(this).closest(".tab-pane.active").attr("id");
      const trieda = $(this).closest("div.grid").find("#trieda").text();
      const skupina = $(this).closest("div.grid").find("#skupina").text();
      const kapitola = $(this).closest("div.grid").find("#kapitola").text();
      const potvrdenie = confirm("Naozaj chcete regenerovať otázky pre " + predmet + ":" + trieda + skupina + ":" + kapitola + "?");
      if (potvrdenie) {
         const $form = $("<form method='POST' action='/admin/regeneratetests'>");
         $form.append($('<input type="hidden" name="predmet">').val(predmet));
         $form.append($('<input type="hidden" name="trieda">').val(trieda));
         $form.append($('<input type="hidden" name="skupina">').val(skupina));
         $form.append($('<input type="hidden" name="kapitola">').val(kapitola));
         $('body').append($form);
         $form.submit();
      }
   });

   window.addEventListener('hashchange', onHashChange, false);
   //spusti prvotny vyber tabu
   onHashChange();
});
