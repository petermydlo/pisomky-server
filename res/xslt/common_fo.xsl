<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:fo="http://www.w3.org/1999/XSL/Format">

<!-- Tabuľka na vyplnenie, vystredená (prázdny stĺpec po bokoch). $rezim: zadanie (prázdne polia) alebo vysledok
      (odpoveď žiaka farebne voči správnej); $hodnoty: odpoveď žiaka po poliach -->
<xsl:template match="tabulka">
   <xsl:param name="rezim" select="'zadanie'"/>
   <xsl:param name="hodnoty" as="xs:string*" select="()"/>
   <xsl:variable name="stlpce" select="count((hlavicka, riadok)[1]/bunka)"/>
   <fo:table-row keep-with-previous.within-page="always">
      <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
         <fo:table table-layout="fixed" width="100%" margin-top="0.2cm" margin-bottom="0.3cm">
            <fo:table-column column-width="proportional-column-width(1)"/>
            <fo:table-column column-width="{$stlpce * 1.4}cm"/>
            <fo:table-column column-width="proportional-column-width(1)"/>
            <fo:table-body>
               <fo:table-row>
                  <fo:table-cell><fo:block/></fo:table-cell>
                  <fo:table-cell>
                     <fo:table table-layout="fixed" width="100%" border="solid 0.5pt black">
                        <xsl:for-each select="1 to $stlpce">
                           <fo:table-column column-width="proportional-column-width(1)"/>
                        </xsl:for-each>
                        <fo:table-body>
                           <xsl:apply-templates select="hlavicka | riadok">
                              <xsl:with-param name="rezim" select="$rezim" tunnel="yes"/>
                              <xsl:with-param name="hodnoty" select="$hodnoty" tunnel="yes"/>
                           </xsl:apply-templates>
                        </fo:table-body>
                     </fo:table>
                  </fo:table-cell>
                  <fo:table-cell><fo:block/></fo:table-cell>
               </fo:table-row>
            </fo:table-body>
         </fo:table>
      </fo:table-cell>
   </fo:table-row>
</xsl:template>

<xsl:template match="tabulka/hlavicka | tabulka/riadok">
   <fo:table-row><xsl:apply-templates select="bunka"/></fo:table-row>
</xsl:template>

<xsl:template match="tabulka//bunka">
   <xsl:param name="rezim" tunnel="yes"/>
   <xsl:param name="hodnoty" as="xs:string*" tunnel="yes"/>
   <xsl:variable name="poradie" select="count(preceding::bunka[@odpoved][ancestor::tabulka is current()/ancestor::tabulka]) + 1"/>
   <xsl:variable name="zadane" select="($hodnoty[$poradie], '')[1]"/>
   <xsl:variable name="dobre" select="normalize-space($zadane) != '' and lower-case(normalize-space($zadane)) = lower-case(normalize-space(@odpoved))"/>
   <fo:table-cell border="solid 0.5pt black" padding="2pt" text-align="center">
      <xsl:if test="parent::hlavicka">
         <xsl:attribute name="font-weight">bold</xsl:attribute>
      </xsl:if>
      <xsl:if test="@odpoved and $rezim = 'vysledok'">
         <xsl:attribute name="background-color" select="if ($dobre) then 'green' else 'red'"/>
      </xsl:if>
      <fo:block>
         <xsl:choose>
            <xsl:when test="not(@odpoved)"><xsl:apply-templates/></xsl:when>
            <xsl:when test="$rezim = 'vysledok'">
               <xsl:value-of select="if ($zadane = '') then '-' else $zadane"/>
               <xsl:if test="not($dobre)"> (<xsl:value-of select="@odpoved"/>)</xsl:if>
            </xsl:when>
            <xsl:otherwise><xsl:text>&#160;</xsl:text></xsl:otherwise>
         </xsl:choose>
      </fo:block>
   </fo:table-cell>
</xsl:template>

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
