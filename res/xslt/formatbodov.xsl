<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">

<xsl:decimal-format name="sk" decimal-separator="." grouping-separator="&#160;"/>

<!-- Body na výpis: zaokrúhlené na 2 desatinné miesta (.5 hore), bez zbytočných núl, desatinná bodka.
     Výpočty ostávajú nezaokrúhlené, zaokrúhľuje sa len tu. -->
<xsl:function name="my:body-text" as="xs:string">
   <xsl:param name="x" as="xs:anyAtomicType?"/>
   <xsl:sequence select="if (empty($x)) then '' else format-number(round(xs:decimal($x) * 100) div 100, '0.##', 'sk')"/>
</xsl:function>

<!-- Percentá na výpis: orezané (nie zaokrúhlené) na 2 desatinné miesta, aby zobrazená hodnota nikdy nebola
     nad hranicou známky, ktorú výsledok nedosiahol (hranice stupnice majú najviac 2 desatinné miesta). -->
<xsl:function name="my:percent-text" as="xs:string">
   <xsl:param name="x" as="xs:anyAtomicType?"/>
   <xsl:sequence select="if (empty($x)) then '' else format-number(floor(xs:decimal($x) * 100) div 100, '0.##', 'sk')"/>
</xsl:function>

</xsl:stylesheet>
