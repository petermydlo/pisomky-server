$(function() {
   //podla vybrateho predmetu povoli len kapitoly obsiahnute v tomto predmete
   $("#predmet").on("change", function(e) {
      const predmetVal = $(this).val();
      $("#kapitola option").prop("disabled", true);
      $("#kapitola").find("option." + predmetVal).prop("disabled", false);
      $("#kapitola option:not([disabled]):first").attr("selected", "selected");
   });

   //podla vybratej triedy povoli len skupiny z tejto triedy
   $("#trieda").on("change", function(e) {
      let trieda = $(".selectpicker").selectpicker("val");
      trieda = trieda != "" ? trieda : ["cela"];
      const triedy = trieda.map(function(value) {
         return value.replace(".", "_").trim();
      });
      $("#skupina option").not(".cela").prop("disabled", true);
      $("#skupina").find("option." + triedy.join(".")).prop("disabled", false);
   });

   //spusti prvotny vyber predmetu pri nacitani stranky
   $("#predmet").trigger("change");
   //$("#trieda").trigger("change");
});
