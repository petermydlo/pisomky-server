<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">

<xsl:variable name="stupnice" select="doc('../xml/lists/scales.xml')/stupnice"/>

<!-- Stupnica testu (testy/@stupnica); chýbajúci alebo neznámy atribút = default -->
<xsl:function name="my:stupnica" as="element(stupnica)">
   <xsl:param name="uzol" as="node()"/>
   <xsl:variable name="id" select="($uzol/ancestor-or-self::testy/@stupnica[. != ''], 'default')[1]"/>
   <xsl:sequence select="($stupnice/stupnica[@id = $id], $stupnice/stupnica[@id = 'default'])[1]"/>
</xsl:function>

<xsl:function name="my:znamka" as="xs:string">
   <xsl:param name="percenta" as="xs:decimal"/>
   <xsl:param name="stupnica" as="element(stupnica)"/>
   <xsl:sequence select="
      if ($percenta ge xs:decimal($stupnica/@min1)) then '1'
      else if ($percenta ge xs:decimal($stupnica/@min2)) then '2'
      else if ($percenta ge xs:decimal($stupnica/@min3)) then '3'
      else if ($percenta ge xs:decimal($stupnica/@min4)) then '4'
      else if ($percenta ge xs:decimal($stupnica/@min5)) then '5'
      else '-'"/>
</xsl:function>

<!-- Text do hlavičky PDF: 100%-85%:1   84%-70%:2 ... -->
<xsl:function name="my:stupnicatext" as="xs:string">
   <xsl:param name="stupnica" as="element(stupnica)"/>
   <xsl:variable name="hranice" select="for $i in 1 to 5 return xs:decimal($stupnica/@*[local-name() = 'min' || $i])"/>
   <xsl:variable name="krok" select="if (some $h in $hranice satisfies $h ne floor($h)) then 0.01 else 1"/>
   <xsl:sequence select="string-join(
      for $i in 1 to 5 return
         concat(if ($i = 1) then 100 else $hranice[$i - 1] - $krok, '%-', $hranice[$i], '%:', $i),
      '&#xA0;&#xA0;&#xA0;')"/>
</xsl:function>

</xsl:stylesheet>
