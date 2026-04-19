$(function() {
   $("#ai-evaluate-btn").on("click", async function(e) {
      e.preventDefault();
      const btn = $(this);
      const hlavicka = $("#hlavicka");
      btn.find("i").removeClass("bi-robot").addClass("bi-hourglass-split");
      zobrazNotifikaciu("AI vyhodnocuje otázky...", "info", "AI", 10000);

      const udaje = new FormData();
      udaje.append("test_id",  hlavicka.attr("kluc"));
      udaje.append("predmet",  hlavicka.attr("predmet"));
      udaje.append("trieda",   hlavicka.attr("trieda"));
      udaje.append("skupina",  hlavicka.attr("skupina"));
      udaje.append("kapitola", hlavicka.attr("kapitola"));

      try {
         const resp = await fetch("/admin/ai/evaluate-open", {
            method: "POST",
            body: udaje
         });
         const data = await resp.json();

         if (!data.ok) {
            const msg = data.kod === "no_questions"
               ? "Žiadne otvorené otázky so vzorom na vyhodnotenie."
               : `Chyba: ${data.error}`;
            zobrazNotifikaciu(msg, "warning", "AI");
            return;
         }

         const otvorene = $("input[type='number'][id^='h_'], input[type='number'][id^='bh_']").length;
         let uspesne = 0;
         for (const vysledok of data.vysledky) {
            const $bh = $(`#bh_${vysledok.id}`);
            const $input = $bh.length ? $bh : $(`#h_${vysledok.id}`);
            $input.val(vysledok.body).trigger("change");
            $(`#k_${vysledok.id}`).val(vysledok.dovod);
            uspesne++;
         }
         const preskocene = otvorene - uspesne;
         const msg = preskocene > 0
            ? `AI vyhodnotila ${uspesne} otázok, ${preskocene} preskočila (bez vzoru). Skontrolujte a uložte.`
            : `AI vyhodnotila ${uspesne} otázok. Skontrolujte a uložte.`;
         zobrazNotifikaciu(msg, "success", "AI");
      } catch (e) {
         console.error("AI evaluate chyba:", e);
         zobrazNotifikaciu("Chyba pri komunikácii so serverom.", "danger", "AI");
      } finally {
         btn.find("i").removeClass("bi-hourglass-split").addClass("bi-robot");
      }
   });
});
