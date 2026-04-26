declare namespace xs = "http://www.w3.org/2001/XMLSchema";

declare variable $predmet as xs:string external;
declare variable $trieda as xs:string external;
declare variable $skupina as xs:string external;
declare variable $kapitola as xs:string external;
declare variable $fileid as xs:string external;

let $feedback := if (doc-available(concat('../xml/feedback/', $predmet, '/', $predmet, '_', $trieda, $skupina, '_', $kapitola, '_', $fileid, '.xml')))
                 then doc(concat('../xml/feedback/', $predmet, '/', $predmet, '_', $trieda, $skupina, '_', $kapitola, '_', $fileid, '.xml'))
                 else ()
let $qsubor := doc(concat('../xml/questions/', $predmet, '/', $predmet, '_', $kapitola, '.xml'))

let $otazky :=
   for $otazka_id in distinct-values($feedback//zapis/@otazka_id)
      let $q_otazka := $qsubor//otazka[@id = $otazka_id]
      let $q_kategoria := $q_otazka/..
      let $kategoria_id := $q_kategoria/@id
      let $kat_poradie := count($q_kategoria/preceding-sibling::kategoria) + 1
      let $otazka_poradie := count($q_otazka/preceding-sibling::otazka) + 1
      let $zaznamy := $feedback//zapis[@otazka_id = $otazka_id]
      let $ano := count($zaznamy[@val = '1'])
      let $nie := count($zaznamy[@val = '0'])
      let $nezodpovedane := count($zaznamy[@val = ''])
      order by $kat_poradie ascending, $otazka_poradie ascending
      return <otazka id="{$otazka_id}" nazov="{$q_otazka/@nazov}" ano="{$ano}" nie="{$nie}" nezodpovedane="{$nezodpovedane}" kategoria="{$kategoria_id}">
         <znenie>{$q_otazka/znenie[1]/string()}</znenie>
         <napovedy>
            {for $z in $zaznamy
             return <napoveda val="{$z/@val}" datum="{$z/@datum}" keys="{$z/keys}">
                       {if ($z/hint) then $z/hint/string() else $z/string()}
                    </napoveda>}
         </napovedy>
      </otazka>

return <feedback predmet="{$predmet}" trieda="{$trieda}" skupina="{$skupina}" kapitola="{$kapitola}" fileid="{$fileid}">
   {
   for $kat_id in distinct-values($otazky/@kategoria)
      let $q_kat := $qsubor//kategoria[@id = $kat_id]
      let $kat_poradie := count($q_kat/preceding-sibling::kategoria) + 1
      order by $kat_poradie ascending
      return <kategoria id="{$kat_id}" nazov="{$q_kat/@nazov}">
         {$otazky[@kategoria = $kat_id]}
      </kategoria>
   }
</feedback>
