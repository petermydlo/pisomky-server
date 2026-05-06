declare namespace xs = "http://www.w3.org/2001/XMLSchema";

declare variable $kluc as xs:string external;
declare variable $test_cesta as xs:string external;
declare variable $answer_cesta as xs:string external;
declare variable $questions_cesta as xs:string external;

let $test_doc      := if (doc-available($test_cesta))      then doc($test_cesta)      else ()
let $answer_doc    := if (doc-available($answer_cesta))    then doc($answer_cesta)    else ()
let $questions_doc := if (doc-available($questions_cesta)) then doc($questions_cesta) else ()

let $test_node   := $test_doc//test[@id = $kluc]
let $answer_node := $answer_doc//test[@id = $kluc]

return
   if (empty($test_node) or empty($answer_node)) then
      <otazky/>
   else
      <otazky>
      {
         for $otazka in $test_node/otazka[not(odpoved)]
         let $oid     := string($otazka/@id)
         let $odpoved := string($answer_node/otazka[@id = $oid])
         let $q       := $questions_doc//otazka[@id = $oid]
         let $vzor    := string($q/vzor)
         where $odpoved != '' and $vzor != ''
         return
            <otazka id="{$oid}" body="{$otazka/@body}">
               <znenie>{string($q/znenie)}</znenie>
               <vzor>{$vzor}</vzor>
               {for $s in $q/klucove_slova/slovo[normalize-space()] return <klucove>{normalize-space($s)}</klucove>}
               <odpoved>{$odpoved}</odpoved>
            </otazka>
      }
      </otazky>
