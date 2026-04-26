<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:fo="http://www.w3.org/1999/XSL/Format">

<xsl:template match="ref">
   <xsl:variable name="ref_id" select="@id"/>
   <fo:inline>
      <xsl:value-of select="count(ancestor::test/otazka[@id = $ref_id]/preceding-sibling::otazka) + 1"/>
   </fo:inline>
</xsl:template>

<xsl:template match="obrazok">
   <fo:block text-align="center">
      <xsl:choose>
         <xsl:when test="@vyska and @sirka">
            <fo:external-graphic src="url('../pubres/img/{@src}')" width="100%" content-width="{@sirka * 0.75}pt" scaling="uniform" content-height="{@vyska * 0.75}pt"/>
         </xsl:when>
         <xsl:when test="@vyska and not(@sirka)">
            <fo:external-graphic src="url('../pubres/img/{@src}')" width="100%" content-width="scale-down-to-fit" scaling="uniform" content-height="{@vyska * 0.75}pt"/>
         </xsl:when>
         <xsl:when test="@sirka and not(@vyska)">
            <fo:external-graphic src="url('../pubres/img/{@src}')" width="100%" content-width="{@sirka * 0.75}pt" scaling="uniform" content-height="scale-down-to-fit"/>
         </xsl:when>
         <xsl:otherwise>
            <fo:external-graphic src="url('../pubres/img/{@src}')" width="100%" content-width="scale-down-to-fit" scaling="uniform" content-height="scale-down-to-fit"/>
         </xsl:otherwise>
      </xsl:choose>
   </fo:block>
</xsl:template>

<xsl:template match="file">
   <xsl:value-of select="@nazov"/> &lt;<xsl:value-of select="@src"/>&gt;
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="text()">
   <xsl:if test="normalize-space(.)">
      <xsl:value-of select="."/>
   </xsl:if>
</xsl:template>

<xsl:template match="br">
   <fo:block/>
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="bold">
   <fo:inline font-weight="bold">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

<xsl:template match="italic">
   <fo:inline font-style="italic">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

<xsl:template match="underline">
   <fo:inline text-decoration="underline">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

<xsl:template match="upp">
   <fo:inline text-transform="uppercase">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

<xsl:template match="low">
   <fo:inline text-transform="lowercase">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

<xsl:template match="sup">
   <fo:inline baseline-shift="super" font-size="70%">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

<xsl:template match="sub">
   <fo:inline baseline-shift="sub" font-size="70%">
      <xsl:apply-templates/>
   </fo:inline>
</xsl:template>

</xsl:stylesheet>
