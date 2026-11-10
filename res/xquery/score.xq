declare namespace xs = "http://www.w3.org/2001/XMLSchema";

declare variable $kluc as xs:string external;
declare variable $test_cesta as xs:string external;
declare variable $answer_cesta as xs:string external;

declare variable $stupnice := doc('../xml/lists/scales.xml')/stupnice;

declare function local:spravnaodpoved($otazka as element()) as xs:string {
   string-join(
      for $i in 1 to count($otazka/odpoved)
      where $otazka/odpoved[$i]/@spravna = '1'
      return codepoints-to-string(string-to-codepoints('a') + $i - 1)
   )
};

(: Body za tabuľku: zrkadlí my:bodytabulka v res/xslt/grading.xsl :)
declare function local:bodytabulka($otazka as element(), $odpoved as xs:string) as xs:decimal {
   let $spravne := $otazka/tabulka//bunka[@odpoved]/string(@odpoved)
   let $zadane  := tokenize($odpoved, '\|')
   let $zhody   := count(
      for $i in 1 to count($spravne)
      where normalize-space(($zadane[$i], '')[1]) != '' and lower-case(normalize-space($zadane[$i])) = lower-case(normalize-space($spravne[$i]))
      return $i
   )
   return
      if (empty($spravne)) then 0
      else xs:decimal($otazka/@body) * $zhody div count($spravne)
};

let $test_doc    := if (doc-available($test_cesta))   then doc($test_cesta)   else ()
let $answer_doc  := if (doc-available($answer_cesta)) then doc($answer_cesta) else ()
let $test_node   := $test_doc//test[@id = $kluc]
let $answer_node := $answer_doc//test[@id = $kluc]

return
   if (empty($test_node) or empty($answer_node)) then
      <neohodnoteny/>
   else
      let $otazky  := $test_node/otazka[not(@rating)]
      let $maximum := xs:decimal(sum($test_node/otazka[not(@bonus)][not(@rating)]/@body))
      let $raw :=
         xs:decimal(sum(
            for $otazka in $otazky
            let $spravna := local:spravnaodpoved($otazka)
            return
               if (exists($otazka/tabulka)) then
                  local:bodytabulka($otazka, string($answer_node/otazka[@id = $otazka/@id]))
               else if ($spravna != '') then
                  if (string($answer_node/otazka[@id = $otazka/@id]) = $spravna)
                  then xs:decimal($otazka/@body) else 0
               else
                  xs:decimal(($answer_node/otazka[@id = $otazka/@id]/@body, 0)[1])
         ))
      let $neuplne :=
         exists(
            for $o in $otazky
            where local:spravnaodpoved($o) = '' and empty($o/tabulka) and empty($answer_node/otazka[@id = $o/@id]/@body)
            return $o
         )
      let $ziskane  := min(($raw, $maximum))
      let $percento := if ($maximum > 0) then $ziskane div $maximum * 100 else 0
      let $id       := (string($test_doc/testy/@stupnica)[. != ''], 'default')[1]
      let $stupnica := ($stupnice/stupnica[@id = $id], $stupnice/stupnica[@id = 'default'])[1]
      let $znamka   :=
         if ($neuplne) then ''
         else if ($percento >= xs:decimal($stupnica/@min1)) then '1'
         else if ($percento >= xs:decimal($stupnica/@min2)) then '2'
         else if ($percento >= xs:decimal($stupnica/@min3)) then '3'
         else if ($percento >= xs:decimal($stupnica/@min4)) then '4'
         else '5'
      return <skore ziskane="{$ziskane}" maximum="{$maximum}" percento="{$percento}" neuplne="{$neuplne}" znamka="{$znamka}"/>
