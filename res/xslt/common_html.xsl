<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:template match="ref">
   <xsl:variable name="ref_id" select="@id"/>
   <xsl:value-of select="count(ancestor::test/otazka[@id = $ref_id]/preceding-sibling::otazka) + 1"/>
</xsl:template>

<xsl:template match="obrazok">
   <div class="centrovane">
      <img src="/pubres/img/{@src}">
         <xsl:if test="@vyska">
            <xsl:attribute name="height"><xsl:value-of select="@vyska"/>px</xsl:attribute>
         </xsl:if>
         <xsl:if test="@sirka">
            <xsl:attribute name="width"><xsl:value-of select="@sirka"/>px</xsl:attribute>
         </xsl:if>
         <xsl:if test="@nazov">
            <xsl:attribute name="title"><xsl:value-of select="@nazov"/></xsl:attribute>
         </xsl:if>
      </img>
   </div>
</xsl:template>

<xsl:template match="file">
   <a href="/pubres/subory/{@src}">
      <xsl:if test="@meno">
         <xsl:attribute name="download"><xsl:value-of select="@meno"/></xsl:attribute>
      </xsl:if>
      <xsl:if test="not(@meno)">
         <xsl:attribute name="download"/>
      </xsl:if>
      <xsl:if test="@nazov">
         <xsl:value-of select="@nazov"/>
      </xsl:if>
   </a>
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="text()">
   <xsl:if test="normalize-space(.)">
      <xsl:value-of select="."/>
   </xsl:if>
</xsl:template>

<xsl:template match="br">
   <br/>
   <xsl:apply-templates/>
</xsl:template>

<xsl:template match="bold | italic | underline | upp | low | sup | sub">
   <span class="{local-name()}">
      <xsl:apply-templates/>
   </span>
</xsl:template>

</xsl:stylesheet>
