declare namespace xs = "http://www.w3.org/2001/XMLSchema";

declare variable $predmet as xs:string external;
declare variable $trieda as xs:string external;
declare variable $skupina as xs:string external;
declare variable $kapitola as xs:string external;
declare variable $fileid as xs:string external;
declare variable $autor as xs:string external := '';

declare function local:najdiOtazku($predmet, $kapitola, $otazka_id) {
   let $qsubor := doc(concat('../xml/questions/', $predmet, '/', $predmet, '_', $kapitola, '.xml'))
   return $qsubor//otazka[@id = $otazka_id]
};

declare function local:poslednyPokus($testy as element()*) as element()? {
   $testy[1]
};

declare function local:poslednyOhodnotenyPokus($testy as element()*) as element()? {
   $testy[otazka[@body]][1]
};

declare function local:pismeno($pozicia as xs:integer) as xs:string {
   substring('abcdefghij', $pozicia, 1)
};

let $tests_subor := if (doc-available(concat('../xml/tests/', $predmet, '/', $predmet, '_', $trieda, $skupina, '_', $kapitola, '_', $fileid, '.xml')))
                    then doc(concat('../xml/tests/', $predmet, '/', $predmet, '_', $trieda, $skupina, '_', $kapitola, '_', $fileid, '.xml'))
                    else ()
let $answers_subor := if (doc-available(concat('../xml/answers/', $predmet, '/', $predmet, '_', $trieda, $skupina, '_', $kapitola, '_', $fileid, '.xml')))
                      then doc(concat('../xml/answers/', $predmet, '/', $predmet, '_', $trieda, $skupina, '_', $kapitola, '_', $fileid, '.xml'))
                      else ()
let $qsubor := doc(concat('../xml/questions/', $predmet, '/', $predmet, '_', $kapitola, '.xml'))

(: vsetky otazky zo vsetkych testov v skupine :)
let $vsetky_otazky := $tests_subor//test/otazka

(: zaznamy spravnosti pre MCQ otazky :)
let $zaznamy_mcq :=
   for $id in distinct-values($tests_subor//test/@id)
      let $pokusy := $answers_subor//test[@id = $id]
      let $posledny := local:poslednyPokus($pokusy)
      for $ziakova in $posledny/otazka[text()]
         let $otazka_id := $ziakova/@id
         let $test_node := $tests_subor//test[@id = $id]/otazka[@id = $otazka_id]
         where exists($test_node/odpoved)
         let $spravna_pozicia := count($test_node/odpoved[@spravna='1']/preceding-sibling::odpoved) + 1
         let $spravne_pismeno := local:pismeno($spravna_pozicia)
         let $body := xs:integer($test_node/@body)
         return <zaznam id="{$otazka_id}" typ="mcq" spravne="{$ziakova/text() = $spravne_pismeno}" body="{$body}"/>

(: zaznamy bodov pre otvorene otazky :)
let $zaznamy_body :=
   for $id in distinct-values($tests_subor//test/@id)
      let $pokusy := $answers_subor//test[@id = $id]
      let $posledny := local:poslednyOhodnotenyPokus($pokusy)
      where exists($posledny)
      for $ziakova in $posledny/otazka[@body]
         let $otazka_id := $ziakova/@id
         let $test_node := $tests_subor//test[@id = $id]/otazka[@id = $otazka_id]
         where not(exists($test_node/odpoved))
         return <zaznam id="{$otazka_id}" typ="body" body="{$ziakova/@body}" maxbody="{$test_node/@body}"/>

(: unikatne otazka id — kategoria a poradie z questions XML :)
let $otazky :=
   for $otazka_id in distinct-values($vsetky_otazky/@id)
      let $q_otazka := $qsubor//otazka[@id = $otazka_id]
      let $q_kategoria := $q_otazka/..
      let $kategoria_id := $q_kategoria/@id
      let $kat_poradie := count($q_kategoria/preceding-sibling::kategoria) + 1
      let $otazka_poradie := count($q_otazka/preceding-sibling::otazka) + 1
      let $zaz_mcq := $zaznamy_mcq[@id = $otazka_id]
      let $zaz_body := $zaznamy_body[@id = $otazka_id]
      order by $kat_poradie ascending, $otazka_poradie ascending
      return
         if (exists($zaz_mcq)) then
            let $spravne := count($zaz_mcq[@spravne='true'])
            let $nespravne := count($zaz_mcq[@spravne='false'])
            let $body_hodnota := sum($zaz_mcq[@spravne='true']/xs:integer(@body))
            let $maxbody_hodnota := sum($zaz_mcq/xs:integer(@body))
            let $percento := if ($maxbody_hodnota > 0) then round($body_hodnota div $maxbody_hodnota * 100) else 0
            return <otazka id="{$otazka_id}" nazov="{$q_otazka/@nazov}" kategoria="{$kategoria_id}"
                      spravne="{$spravne}"
                      nespravne="{$nespravne}"
                      body="{$body_hodnota}"
                      maxbody="{$maxbody_hodnota}"
                      percento="{$percento}">
                      {$q_otazka/znenie[1]}
                   </otazka>
         else if (exists($zaz_body)) then
            let $suma_body := sum($zaz_body/xs:integer(@body))
            let $pocet := count($zaz_body)
            let $priemer_body := if ($pocet > 0) then round($suma_body div $pocet) else 0
            let $priemer_max := $zaz_body[1]/xs:integer(@maxbody)
            let $percento := if ($priemer_max > 0) then round($priemer_body div $priemer_max * 100) else 0
            return <otazka id="{$otazka_id}" nazov="{$q_otazka/@nazov}" kategoria="{$kategoria_id}"
                      body="{$priemer_body}"
                      maxbody="{$priemer_max}"
                      percento="{$percento}">
                      {$q_otazka/znenie[1]}
                   </otazka>
         else
            <otazka id="{$otazka_id}" nazov="{$q_otazka/@nazov}" kategoria="{$kategoria_id}"
                      body="0"
                      maxbody="0"
                      percento="0">
                      {$q_otazka/znenie[1]}
                   </otazka>

return <statistika predmet="{$predmet}" trieda="{$trieda}" skupina="{$skupina}" kapitola="{$kapitola}" fileid="{$fileid}">
   {
   for $kat_id in distinct-values($otazky/@kategoria)
      let $q_kat := $qsubor//kategoria[@id = $kat_id]
      let $kat_poradie := count($q_kat/preceding-sibling::kategoria) + 1
      order by $kat_poradie ascending
      return <kategoria id="{$kat_id}" nazov="{$q_kat/@nazov}"
                percento="{
                   let $k := $otazky[@kategoria = $kat_id]
                   let $b := sum($k/xs:integer(@body))
                   let $m := sum($k/xs:integer(@maxbody))
                   return if ($m > 0) then round($b div $m * 100) else 0
                }">
         {$otazky[@kategoria = $kat_id]}
      </kategoria>
   }
</statistika>
