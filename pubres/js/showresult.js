document.addEventListener('DOMContentLoaded', () => {
   const vyhodnotenie = document.getElementById('vyhodnotenie');
   const min1 = parseInt(vyhodnotenie.dataset.min1, 10);
   const min2 = parseInt(vyhodnotenie.dataset.min2, 10);
   const min3 = parseInt(vyhodnotenie.dataset.min3, 10);
   const min4 = parseInt(vyhodnotenie.dataset.min4, 10);

   document.addEventListener('change', (e) => {
      if (e.target.matches('.radio.col-up input')) {
         const div = e.target.closest('.flex-container-table-znenie');
         div.className = 'flex-container-table-znenie ' + e.target.value;
      }

      if (e.target.matches("input[type='number'][id^='h_'], input[type='number'][id^='bh_']")) {
         let maxPoints = 0;
         document.querySelectorAll("input[type='number'][id^='h_']").forEach(el => {
            maxPoints += parseInt(el.getAttribute('max'), 10);
         });
         let totalPoints = 0;
         document.querySelectorAll("input[type='number'][id^='h_'], input[type='number'][id^='bh_']").forEach(el => {
            totalPoints += parseInt(el.value, 10);
         });
         totalPoints = Math.max(Math.min(totalPoints, maxPoints), 0);
         const percenta = totalPoints / maxPoints * 100;
         document.getElementById('pocetbodov').textContent = totalPoints;
         document.getElementById('pocetpercent').textContent = percenta.toFixed(2);
         const znamka = document.getElementById('znamka');
         if (percenta >= min1) {
            znamka.textContent = '1';
            vyhodnotenie.className = 'flex-container-head-part bg-success bg-opacity-50';
         } else if (percenta >= min2) {
            znamka.textContent = '2';
            vyhodnotenie.className = 'flex-container-head-part bg-success-subtle';
         } else if (percenta >= min3) {
            znamka.textContent = '3';
            vyhodnotenie.className = 'flex-container-head-part bg-warning-subtle';
         } else if (percenta >= min4) {
            znamka.textContent = '4';
            vyhodnotenie.className = 'flex-container-head-part bg-danger-subtle';
         } else {
            znamka.textContent = '5';
            vyhodnotenie.className = 'flex-container-head-part bg-danger bg-opacity-50';
         }
      }
   });

   document.querySelectorAll('.radio.col-up input:checked').forEach(el => {
      el.dispatchEvent(new Event('change'));
   });
   document.querySelector("input[type='number'][id^='h_']")?.dispatchEvent(new Event('change'));
});
