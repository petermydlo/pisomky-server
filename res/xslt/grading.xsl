<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">

<xsl:import href="scale.xsl"/>

<xsl:key name="ttest" match="test" use="@id"/>

<xsl:function name="my:adresa" as="xs:string">
   <xsl:param name="testnode" as="element()"/>
   <xsl:sequence select="concat('../xml/answers/', $testnode/@predmet, '/', $testnode/@predmet, '_', $testnode/@trieda, $testnode/@skupina, '_', $testnode/@kapitola, '.xml')"/>
</xsl:function>

<xsl:function name="my:vybtesty" as="document-node()">
   <xsl:param name="testnode" as="element()"/>
   <xsl:variable name="adresa" select="if (local-name($testnode) = 'test') then my:adresa($testnode/..) else my:adresa($testnode)"/>
   <xsl:choose>
      <xsl:when test="doc-available($adresa)">
         <xsl:sequence select="doc($adresa)"/>
      </xsl:when>
      <xsl:otherwise>
         <xsl:document>
            <odpovede><test id="0"/></odpovede>
         </xsl:document>
      </xsl:otherwise>
   </xsl:choose>
</xsl:function>

<xsl:function name="my:riestest" as="element()?">
   <xsl:param name="testnode" as="element()"/>
   <xsl:sequence select="key('ttest', $testnode/@id, my:vybtesty($testnode))"/>
</xsl:function>

<xsl:function name="my:sucetmaxbodov" as="xs:integer">
   <xsl:param name="testnode" as="element()"/>
   <xsl:sequence select="sum(for $q in $testnode/otazka[not(@bonus)][not(@rating)] return xs:integer($q/@body))"/>
</xsl:function>

<xsl:function name="my:sucetspravnychbodov" as="xs:integer">
   <xsl:param name="testnode" as="element()"/>
   <xsl:variable name="riestest" select="my:riestest($testnode)"/>
   <xsl:variable name="polespravnychbodovs">
      <xsl:apply-templates select="$testnode/otazka[not(@rating)]" mode="ziskanebody">
         <xsl:with-param name="rtest" select="$riestest" tunnel="yes"/>
      </xsl:apply-templates>
   </xsl:variable>
   <xsl:sequence select="sum(for $i in tokenize($polespravnychbodovs) return xs:integer($i))"/>
</xsl:function>

<xsl:function name="my:ziskanepercenta" as="xs:double">
   <xsl:param name="testnode" as="element()"/>
   <xsl:sequence select="if (my:sucetmaxbodov($testnode) > 0) then my:sucetspravnychbodov($testnode) div my:sucetmaxbodov($testnode) * 100 else 0"/>
</xsl:function>

<xsl:function name="my:znamka" as="xs:string">
   <xsl:param name="percenta" as="xs:double"/>
   <xsl:choose>
      <xsl:when test="$percenta &gt;= $min1 and $percenta &lt;= $max1">1</xsl:when>
      <xsl:when test="$percenta &gt;= $min2 and $percenta &lt; $min1">2</xsl:when>
      <xsl:when test="$percenta &gt;= $min3 and $percenta &lt; $min2">3</xsl:when>
      <xsl:when test="$percenta &gt;= $min4 and $percenta &lt; $min3">4</xsl:when>
      <xsl:when test="$percenta &gt;= $min5 and $percenta &lt; $min4">5</xsl:when>
      <xsl:otherwise>-</xsl:otherwise>
   </xsl:choose>
</xsl:function>

<xsl:template match="otazka" mode="ziskanebody">
   <xsl:param name="rtest" tunnel="yes"/>
   <xsl:variable name="idotazky" select="@id"/>
   <xsl:variable name="ziakovaodpoved" select="$rtest/otazka[@id = $idotazky]/text()"/>
   <xsl:variable name="spravnaodpoved">
      <xsl:apply-templates select="odpoved" mode="spravnebody"/>
   </xsl:variable>

   <xsl:if test="$ziakovaodpoved = $spravnaodpoved">
      <xsl:sequence select="xs:integer(@body)"/>
   </xsl:if>
</xsl:template>

<xsl:template match="odpoved" mode="spravnebody">
   <xsl:if test="@spravna = 1">
      <xsl:number count="odpoved" format="a"/>
   </xsl:if>
</xsl:template>

</xsl:stylesheet>
