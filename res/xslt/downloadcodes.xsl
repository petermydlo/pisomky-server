<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:fo="http://www.w3.org/1999/XSL/Format">
<xsl:output method="xml" version="1.1" indent="yes" encoding="UTF-8"/>

<xsl:template match="testy">
   <fo:root xml:lang="sk">
      <fo:layout-master-set>
         <fo:simple-page-master master-name="strana" page-height="29.7cm" page-width="21cm" margin-top="1cm" margin-bottom="1cm" margin-left="1.5cm" margin-right="1.5cm">
            <fo:region-body margin-top="2cm"/>
            <fo:region-before precedence="true" extent="2cm"/>
         </fo:simple-page-master>
         <fo:page-sequence-master master-name="strany">
            <fo:single-page-master-reference master-reference="strana" blank-or-not-blank="not-blank"/>
         </fo:page-sequence-master>
      </fo:layout-master-set>
      <fo:page-sequence master-reference="strany">
         <fo:static-content flow-name="xsl-region-before"> <!-- pisem do headera -->
            <fo:block font-family="DejaVu Serif" font-size="8pt" text-align="center">
               <fo:block>STREDNÁ PRIEMYSELNÁ ŠKOLA JOZEFA MURGAŠA</fo:block>
               <fo:block>Predmet:&#160; <xsl:value-of select="@predmet"/>,&#160;Trieda:&#160;<xsl:value-of select="@trieda"/>,&#160;Skupina:&#160;<xsl:value-of select="@skupina"/>,&#160;Kapitola:&#160;<xsl:value-of select="@kapitola"/></fo:block>
               <fo:block>Začiatok:&#160;<xsl:value-of select="@start"/>,&#160;Koniec:&#160;<xsl:value-of select="@stop"/></fo:block>
            </fo:block>
         </fo:static-content>
         <fo:flow flow-name="xsl-region-body" line-height="1.5"> <!-- pisem do tela -->
            <fo:block break-before="page" font-size="12pt" font-family="DejaVu Serif">
               <xsl:apply-templates select="test"/>
            </fo:block>
         </fo:flow>
      </fo:page-sequence>
   </fo:root>
</xsl:template>

<xsl:template match="test">
   <fo:block><fo:leader leader-pattern="rule" leader-length="100%" rule-style="dashed" rule-thickness="1px" color="gray"/></fo:block>
   <fo:block text-align-last="justify">
      <xsl:value-of select="@id"/><fo:leader leader-pattern="space" leader-length.minimum="3cm"/><xsl:value-of select="@meno"/>&#160;<xsl:value-of select="@priezvisko"/>
   </fo:block>
   <xsl:if test="position() = last()">
      <fo:block><fo:leader leader-pattern="rule" leader-length="100%" rule-style="dashed" rule-thickness="1px" color="gray"/></fo:block>
   </xsl:if>
</xsl:template>

</xsl:stylesheet>
