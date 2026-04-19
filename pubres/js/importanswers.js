$(function() {

   const ODPOVEDE = ['a', 'b', 'c', 'd'];

   // nahladove obrazky pri vybere suborov
   $('#obrazky').on('change', function() {
      const files = this.files;
      $('#nahlady').empty();
      if (files.length > 0) {
         $.each(files, function(i, file) {
            if (file.type === 'application/pdf') {
               $('#nahlady').append(
                  $('<div>').addClass('rounded d-flex flex-column align-items-center justify-content-center bg-light border')
                     .css({height: '80px', width: '80px', fontSize: '10px', overflow: 'hidden'})
                     .append($('<div>').text('📄').css('fontSize', '32px'))
                     .append($('<div>').text(file.name).css({wordBreak: 'break-all', textAlign: 'center', padding: '0 2px'}))
               );
            } else {
               const url = URL.createObjectURL(file);
               $('#nahlady').append(
                  $('<img>').attr('src', url).addClass('rounded').css({height: '80px', width: '80px', objectFit: 'cover'})
               );
            }
         });
         $('#btnImport').prop('disabled', false);
      } else {
         $('#btnImport').prop('disabled', true);
      }
   });

   // import
   $('#btnImport').on('click', function() {
      const files = $('#obrazky')[0].files;
      if (!files.length) return;

      $('#uploadSekcia').addClass('d-none');
      $('#priebehSekcia').removeClass('d-none');
      $('#vysledkySekcia').addClass('d-none');
      $('#vysledky').empty();

      const formData = new FormData();
      $.each(files, function(i, file) {
         formData.append('obrazky', file);
      });

      nastavPriebeh(0, `Spracovávam ${files.length} fotiek...`);

      $.ajax({
         url: '/admin/ai/importanswers',
         method: 'POST',
         data: formData,
         processData: false,
         contentType: false,
         xhr: function() {
            const xhr = new XMLHttpRequest();
            return xhr;
         }
      })
      .done(function(data) {
         nastavPriebeh(100, 'Hotovo.');
         zobrazVysledky(data.vysledky);
      })
      .fail(function(xhr) {
         nastavPriebeh(100, 'Chyba!');
         zobrazVysledky([{chyba: xhr.responseJSON?.detail || 'Neznáma chyba'}]);
      });
   });

   function nastavPriebeh(pct, text) {
      $('#priebehText').text(text);
      $('#priebehBar').css('width', pct + '%').text(pct + '%');
   }

   function zobrazVysledky(vysledky) {
      $('#priebehSekcia').addClass('d-none');
      $('#vysledkySekcia').removeClass('d-none');

      const $cont = $('#vysledky');
      $cont.empty();

      $.each(vysledky, function(i, v) {
         const $blok = $('<div>').addClass('okraj mb-2');

         if (v.chyba) {
            $blok.addClass('bg-danger-subtle');
            $blok.append($('<div>').addClass('hrubo').text(v.subor || 'Chyba'));
            $blok.append($('<div>').text(v.chyba));
         } else {
            $blok.addClass(v.nejasnosti && v.nejasnosti.length > 0 ? 'bg-warning-subtle' : 'bg-success-subtle');
            $blok.append(
               $('<div>').addClass('hrubo').text(
                  `${v.test_id} — ${v.predmet} ${v.trieda}${v.skupina} ${v.kapitola} — zapísané: ${v.zapisane}`
               )
            );

            // nejasnosti
            if (v.nejasnosti && v.nejasnosti.length > 0) {
               $blok.append($('<div>').addClass('hrubo mt-2').text('Nejasnosti — skontrolujte a potvrďte:'));
               $.each(v.nejasnosti, function(j, n) {
                  const $riadok = $('<div>').addClass('d-flex align-items-center gap-2 mt-1');
                  $riadok.append($('<span>').addClass('hrubo').text(n.id + ':'));
                  $riadok.append($('<span>').text(n.znenie));
                  if (n.dovod) {
                     $riadok.append($('<span>').addClass('text-muted').text('(' + n.dovod + ')'));
                  }
                  // vyber odpovede
                  const $select = $('<select>').addClass('form-select form-select-sm').css('width', 'auto');
                  $select.append($('<option>').val('').text('—'));
                  $.each(ODPOVEDE, function(k, pism) {
                     $select.append($('<option>').val(pism).text(pism));
                  });
                  $select.data('test-id', v.test_id);
                  $select.data('otazka-id', n.id);
                  $select.data('predmet', v.predmet);
                  $select.data('trieda', v.trieda);
                  $select.data('skupina', v.skupina);
                  $select.data('kapitola', v.kapitola);
                  $riadok.append($select);

                  // tlacidlo ulozit
                  const $btn = $('<button>').addClass('btn btn-sm btn-outline-success').text('Uložiť').prop('disabled', true);
                  $select.on('change', function() {
                     $btn.prop('disabled', !$(this).val());
                  });
                  $btn.on('click', function() {
                     const sel = $riadok.find('select');
                     ulozNejasnost(sel.data('test-id'), sel.data('otazka-id'), sel.val(),
                        sel.data('predmet'), sel.data('trieda'), sel.data('skupina'), sel.data('kapitola'),
                        $btn, $riadok);
                  });
                  $riadok.append($btn);
                  $blok.append($riadok);
               });
            }
         }

         $cont.append($blok);
      });

      // tlacidlo pre novy import
      $cont.append(
         $('<button>').addClass('btn btn-outline-info mt-2').text('Importovať ďalšie')
            .on('click', function() {
               $('#obrazky').val('');
               $('#nahlady').empty();
               $('#btnImport').prop('disabled', true);
               $('#vysledkySekcia').addClass('d-none');
               $('#uploadSekcia').removeClass('d-none');
            })
      );
   }

   function ulozNejasnost(testId, otazkaId, odpoved, predmet, trieda, skupina, kapitola, $btn, $riadok) {
      const data = new FormData();
      data.append('predmet', predmet);
      data.append('trieda', trieda);
      data.append('skupina', skupina);
      data.append('kapitola', kapitola);
      data.append(otazkaId, odpoved);

      $.ajax({
         url: '/admin/ai/importmanual/' + testId,
         method: 'POST',
         data: data,
         processData: false,
         contentType: false
      })
      .done(function() {
         $riadok.find('select, button').prop('disabled', true);
         $riadok.append($('<span>').addClass('text-success hrubo').text(' ✓'));
      })
      .fail(function(xhr) {
         zobrazNotifikaciu(xhr.responseJSON?.detail || 'Chyba pri ukladaní!');
      });
   }

});
