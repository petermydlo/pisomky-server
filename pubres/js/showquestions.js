$(function() {
   $(document).on("change", "input.pause-check", function(e) {
      e.stopPropagation();
      var cb = $(this);
      var id = cb.data("id");
      var typ = cb.data("typ");
      var paused = cb.is(":checked") ? "0" : "1";
      $.post("/admin/setpaused", { id: id, typ: typ, paused: paused })
         .fail(function() {
            cb.prop("checked", !cb.is(":checked"));
         });
   });
});
