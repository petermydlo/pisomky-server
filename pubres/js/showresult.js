$(function() {
   //zmeni farbu pozadia otazky podla zaskrtnuteho pomocneho radia
   $(".radio.col-up input").on("change", function() {
      const $checked_radio = $(this);
      const $changed_div = $(this).closest(".flex-container-table-znenie");
      $changed_div.removeClass().addClass("flex-container-table-znenie").addClass($checked_radio.val());
   });

   const min1 = parseInt($("#vyhodnotenie").data("min1"), 10);
   const min2 = parseInt($("#vyhodnotenie").data("min2"), 10);
   const min3 = parseInt($("#vyhodnotenie").data("min3"), 10);
   const min4 = parseInt($("#vyhodnotenie").data("min4"), 10);

   //zmeni ziskane body a znamku podla vyhodnotenia jednotlivych otazok
   $("input[type='number'][id^='h_'], input[type='number'][id^='bh_']").on("change", function() {
      let maxPoints = 0;
      $("input[type='number'][id^='h_']").each(function(){
         maxPoints += parseInt($(this).attr("max"), 10);
      });

      let totalPoints = 0;
      $("input[type='number'][id^='h_'], input[type='number'][id^='bh_']").each(function(){
         totalPoints += parseInt($(this).val(), 10);
      });
      totalPoints = Math.max(Math.min(totalPoints, maxPoints), 0);

      const percenta = totalPoints / maxPoints * 100;
      $("#pocetbodov").text(totalPoints);
      $("#pocetpercent").text(percenta.toFixed(2));
      //$("#znamka").text(totalPoints >= 85 ? "1" : (totalPoints >= 70 ? "2" : (totalPoints >= 55 ? "3" : (totalPoints >= 40 ? "4" : "5"))));
      if (percenta >= min1) {
         $("#znamka").text("1");
         $("#vyhodnotenie").removeClass().addClass("flex-container-head-part bg-success bg-opacity-50");
      }
      else if(percenta >= min2) {
         $("#znamka").text("2");
         $("#vyhodnotenie").removeClass().addClass("flex-container-head-part bg-success-subtle");
      }
      else if(percenta >= min3) {
         $("#znamka").text("3");
         $("#vyhodnotenie").removeClass().addClass("flex-container-head-part bg-warning-subtle");
      }
      else if(percenta >= min4) {
         $("#znamka").text("4");
         $("#vyhodnotenie").removeClass().addClass("flex-container-head-part bg-danger-subtle");
      }
      else {
         $("#znamka").text("5");
         $("#vyhodnotenie").removeClass().addClass("flex-container-head-part bg-danger bg-opacity-50");
      }
   });

   //spusti prvotnu zmenu farby pomocnych radii
   $(".radio.col-up input:checked").each(function() {
      $(this).trigger("change");
   });

   //spusti prvotny vypocet znamky
   $("input[type='number'][id^='h_']:first").trigger("change");
});
