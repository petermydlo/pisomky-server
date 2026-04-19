$(function() {
   $("#loginForm").on("submit", function(e) {
      e.preventDefault();
      const kluc = $("#kluc").val();
      let adresa = "/" + kluc;
      if ($("#wm").is(":checked"))
         adresa += "?q=w";
      window.location = adresa;
   });
});
