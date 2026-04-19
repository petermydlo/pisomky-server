declare namespace xs = "http://www.w3.org/2001/XMLSchema";

declare variable $predmet as xs:string external;
declare variable $autor as xs:string external := '';

declare function local:poslednyPokus($testy as element()*) as element()? {
   $testy[1]
};

declare function local:poslednyOhodnotenyPokus($testy as element()*) as element()? {
   $testy[otazka[@body]][1]
};

declare function local:pismeno($pozicia as xs:integer) as xs:string {
   substring('abcdefghij', $pozicia, 1)
};

let $answers := try {
                   collection(concat('../xml/answers/', $predmet, '?select=*.xml;on-error=ignore'))
                } catch * { () }
let $tests   := try {
                   collection(concat('../xml/tests/', $predmet, '?select=*.xml;on-error=ignore'))
                } catch * { () }
let $questions := try {
                   collection(concat('../xml/questions/', $predmet, '?select=*.xml;on-error=ignore'))
                } catch * { () }

(: otazky s odpovedami - spravne/nespravne :)
let $odpovede_pismena :=
   for $subor in $answers
   for $id in distinct-values($subor//test/@id)
      let $pokusy := $subor//test[@id = $id]
      let $posledny := local:poslednyPokus($pokusy)
      for $ziakova in $posledny/otazka[text()]
         let $otazka_id := $ziakova/@id
         let $test_node := $tests//test[@id = $id]/otazka[@id = $otazka_id]
         where exists($test_node/odpoved)
         let $spravna_pozicia := count($test_node/odpoved[@spravna='1']/preceding-sibling::odpoved) + 1
         let $spravne_pismeno := local:pismeno($spravna_pozicia)
         let $body := $test_node/@body
         return <zaznam id="{$otazka_id}" spravne="{$ziakova/text() = $spravne_pismeno}" body="{$body}"/>

(: otazky bez odpovedi - body :)
let $odpovede_body :=
   for $subor in $answers
   for $id in distinct-values($subor//test/@id)
      let $pokusy := $subor//test[@id = $id]
      let $posledny := local:poslednyOhodnotenyPokus($pokusy)
      where exists($posledny)
      for $ziakova in $posledny/otazka[@body]
         let $otazka_id := $ziakova/@id
         let $test_node := $tests//test[@id = $id]/otazka[@id = $otazka_id]
         where not(exists($test_node/odpoved))
         return <zaznam id="{$otazka_id}" body="{$ziakova/@body}" maxbody="{$test_node/@body}"/>
let $tests_filtered := if (not($autor) or $autor = '') 
   then $tests
   else $tests[testy/@autor = $autor]

let $vsetky_testy := $tests_filtered//test
let $pocet_ziakov := count($vsetky_testy)

let $vybery :=
   for $test in $vsetky_testy
   for $otazka in $test/otazka
   return <zaznam id="{$otazka/@id}"/>

return <statistika predmet="{$predmet}">
   {
   (: statistika pre otazky s odpovedami :)
   for $id in distinct-values($odpovede_pismena/@id)
      let $zaznamy := $odpovede_pismena[@id = $id]
      let $spravne := count($zaznamy[@spravne='true'])
      let $nespravne := count($zaznamy[@spravne='false'])
      let $celkom := $spravne + $nespravne
      let $body_hodnota := sum($zaznamy[@spravne='true']/@body)
      let $maxbody_hodnota := sum($zaznamy/@body)
      let $kategoria_id := ($questions//otazka[@id = $id]/../@id)[1]
      let $pocet_v_kat := count($questions//kategoria[@id = $kategoria_id]/otazka)
      let $kat_el := ($questions//kategoria[@id = $kategoria_id])[1]
      let $pocet_vyber_kat := if ($kat_el/@pocet) then xs:integer($kat_el/@pocet) else 1
      let $pocet_statickych_v_kat := count($kat_el/otazka[@static])
      let $pocet_nestatickych_v_kat := count($kat_el/otazka[not(@static)])
      let $kat_vybery := count($vybery[@id = $questions//kategoria[@id = $kategoria_id]/otazka/@id])
      let $vyber_kat_percento := if ($kat_vybery > 0) then count($vybery[@id = $id]) div $kat_vybery * 100 else 0
      return <otazka id="{$id}"
               spravne="{$spravne}"
               nespravne="{$nespravne}"
               body="{$body_hodnota}"
               maxbody="{$maxbody_hodnota}"
               percento="{if ($maxbody_hodnota > 0) then $body_hodnota div $maxbody_hodnota * 100 else 0}"
               vyber="{count($vybery[@id = $id])}"
               vyber_percento="{if ($pocet_ziakov > 0) then count($vybery[@id = $id]) div $pocet_ziakov * 100 else 0}"
               vyber_kat_percento="{$vyber_kat_percento}"
               pocet_v_kat="{$pocet_v_kat}"
               pocet_vyber_kat="{$pocet_vyber_kat}"
               pocet_statickych_v_kat="{$pocet_statickych_v_kat}"
               pocet_nestatickych_v_kat="{$pocet_nestatickych_v_kat}"/>
   }
   {
   (: statistika pre otazky bez odpovedi :)
   for $id in distinct-values($odpovede_body/@id)
      let $zaznamy := $odpovede_body[@id = $id]
      let $suma_body := sum($zaznamy/@body)
      let $suma_max := sum($zaznamy/@maxbody)
      let $kategoria_id := ($questions//otazka[@id = $id]/../@id)[1]
      let $pocet_v_kat := count($questions//kategoria[@id = $kategoria_id]/otazka)
      let $kat_el := ($questions//kategoria[@id = $kategoria_id])[1]
      let $pocet_vyber_kat := if ($kat_el/@pocet) then xs:integer($kat_el/@pocet) else 1
      let $pocet_statickych_v_kat := count($kat_el/otazka[@static])
      let $pocet_nestatickych_v_kat := count($kat_el/otazka[not(@static)])
      let $kat_vybery := count($vybery[@id = $questions//kategoria[@id = $kategoria_id]/otazka/@id])
      let $vyber_kat_percento := if ($kat_vybery > 0) then count($vybery[@id = $id]) div $kat_vybery * 100 else 0
      return <otazka id="{$id}"
               body="{$suma_body}"
               maxbody="{$suma_max}"
               percento="{if ($suma_max > 0) then $suma_body div $suma_max * 100 else 0}"
               vyber="{count($vybery[@id = $id])}"
               vyber_percento="{if ($pocet_ziakov > 0) then count($vybery[@id = $id]) div $pocet_ziakov * 100 else 0}"
               vyber_kat_percento="{$vyber_kat_percento}"
               pocet_v_kat="{$pocet_v_kat}"
               pocet_vyber_kat="{$pocet_vyber_kat}"
               pocet_statickych_v_kat="{$pocet_statickych_v_kat}"
               pocet_nestatickych_v_kat="{$pocet_nestatickych_v_kat}"/>
   }
   {
   (: otazky vyberane ale este nezodpovedane :)
   for $id in distinct-values($vybery/@id)
      where not($id = distinct-values($odpovede_pismena/@id))
         and not($id = distinct-values($odpovede_body/@id))
      let $kategoria_id := ($questions//otazka[@id = $id]/../@id)[1]
      let $pocet_v_kat := count($questions//kategoria[@id = $kategoria_id]/otazka)
      let $kat_el := ($questions//kategoria[@id = $kategoria_id])[1]
      let $pocet_vyber_kat := if ($kat_el/@pocet) then xs:integer($kat_el/@pocet) else 1
      let $pocet_statickych_v_kat := count($kat_el/otazka[@static])
      let $pocet_nestatickych_v_kat := count($kat_el/otazka[not(@static)])
      let $kat_vybery := count($vybery[@id = $questions//kategoria[@id = $kategoria_id]/otazka/@id])
      let $vyber_kat_percento := if ($kat_vybery > 0) then count($vybery[@id = $id]) div $kat_vybery * 100 else 0
      return <otazka id="{$id}"
               percento="0"
               vyber="{count($vybery[@id = $id])}"
               vyber_percento="{if ($pocet_ziakov > 0) then count($vybery[@id = $id]) div $pocet_ziakov * 100 else 0}"
               vyber_kat_percento="{$vyber_kat_percento}"
               pocet_v_kat="{$pocet_v_kat}"
               pocet_vyber_kat="{$pocet_vyber_kat}"
               pocet_statickych_v_kat="{$pocet_statickych_v_kat}"
               pocet_nestatickych_v_kat="{$pocet_nestatickych_v_kat}"/>
   }
</statistika>
