declare namespace xs = "http://www.w3.org/2001/XMLSchema";
declare namespace xsl = "http://www.w3.org/1999/XSL/Transform";

declare variable $kluc as xs:string external;
declare variable $test_cesta as xs:string external;
declare variable $answer_cesta as xs:string external;

declare variable $scale := doc('../xslt/scale.xsl');
declare variable $min1  := xs:integer($scale//xsl:variable[@name='min1']/@select);
declare variable $min2  := xs:integer($scale//xsl:variable[@name='min2']/@select);
declare variable $min3  := xs:integer($scale//xsl:variable[@name='min3']/@select);
declare variable $min4  := xs:integer($scale//xsl:variable[@name='min4']/@select);

declare function local:spravnaodpoved($otazka as element()) as xs:string {
   string-join(
      for $i in 1 to count($otazka/odpoved)
      where $otazka/odpoved[$i]/@spravna = '1'
      return codepoints-to-string(string-to-codepoints('a') + $i - 1)
   )
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
      let $maximum := xs:integer(sum($test_node/otazka[not(@bonus)][not(@rating)]/@body))
      let $raw :=
         xs:integer(sum(
            for $otazka in $otazky
            let $spravna := local:spravnaodpoved($otazka)
            return
               if ($spravna != '') then
                  if (string($answer_node/otazka[@id = $otazka/@id]) = $spravna)
                  then xs:integer($otazka/@body) else 0
               else
                  xs:integer(($answer_node/otazka[@id = $otazka/@id]/@body, 0)[1])
         ))
      let $neuplne :=
         exists(
            for $o in $otazky
            where local:spravnaodpoved($o) = '' and empty($answer_node/otazka[@id = $o/@id]/@body)
            return $o
         )
      let $ziskane  := min(($raw, $maximum))
      let $percento := if ($maximum > 0) then round($ziskane div $maximum * 100) else 0
      let $znamka   :=
         if ($neuplne) then ''
         else if ($percento >= $min1) then '1'
         else if ($percento >= $min2) then '2'
         else if ($percento >= $min3) then '3'
         else if ($percento >= $min4) then '4'
         else '5'
      return <skore ziskane="{$ziskane}" maximum="{$maximum}" percento="{$percento}" neuplne="{$neuplne}" znamka="{$znamka}"/>
