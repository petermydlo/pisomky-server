<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:fo="http://www.w3.org/1999/XSL/Format"
   xmlns:my="http://www.spsjm.sk">
<xsl:output method="xml" version="1.1" indent="yes" encoding="UTF-8"/>

<xsl:import href="grading.xsl"/>

<xsl:param name="kluc"/>

<xsl:template match="/testy">
   <fo:root xml:lang="sk">
      <fo:layout-master-set>
         <fo:simple-page-master master-name="strana" page-height="29.7cm" page-width="21cm" margin-top="0.5cm" margin-bottom="0.5cm" margin-left="1.5cm" margin-right="1.5cm">
            <fo:region-body margin-top="1.5cm" margin-bottom="0.5cm"/>
            <fo:region-before precedence="true" extent="1cm"/>
         </fo:simple-page-master>
         <fo:simple-page-master master-name="prazdna" page-height="29.7cm" page-width="21cm">
            <fo:region-body/>
         </fo:simple-page-master>
         <fo:page-sequence-master master-name="strany">
            <fo:repeatable-page-master-alternatives>
               <fo:conditional-page-master-reference master-reference="strana" blank-or-not-blank="not-blank"/>
               <fo:conditional-page-master-reference master-reference="prazdna" page-position="last" blank-or-not-blank="blank"/>
            </fo:repeatable-page-master-alternatives>
         </fo:page-sequence-master>
      </fo:layout-master-set>
      <xsl:if test="$kluc">
         <xsl:apply-templates select="test[@id = $kluc]"/>
      </xsl:if>
      <xsl:if test="not($kluc)">
         <xsl:apply-templates select="test"/>
      </xsl:if>
   </fo:root>
</xsl:template>

<xsl:template match="test">
   <xsl:variable name="testid" select="@id"/>
   <xsl:variable name="riestest" select="my:riestest(.)"/>
   <fo:page-sequence master-reference="strany">
      <fo:static-content flow-name="xsl-region-before"> <!-- pisem do headera -->
         <fo:block font-family="DejaVu Serif">
            <fo:block>
               <fo:block font-size="8pt" text-align="center" space-after="-10pt">STREDNÁ PRIEMYSELNÁ ŠKOLA JOZEFA MURGAŠA</fo:block>
               <fo:block font-size="8pt" text-align="right"><xsl:value-of select="@id"/></fo:block>
            </fo:block>
            <fo:block font-size="6pt" text-align="center">Hodnotenie:
<xsl:value-of select="$max1"/>%-<xsl:value-of select="$min1"/>%:1&#xA0;&#xA0;&#xA0;<xsl:value-of select="$max2"/>%-<xsl:value-of select="$min2"/>%:2&#xA0;&#xA0;&#xA0;<xsl:value-of select="$max3"/>%-<xsl:value-of select="$min3"/>%:3&#xA0;&#xA0;&#xA0;<xsl:value-of select="$max4"/>%-<xsl:value-of select="$min4"/>%:4&#xA0;&#xA0;&#xA0;<xsl:value-of select="$max5"/>%-<xsl:value-of select="$min5"/>%:5</fo:block>
         </fo:block>
      </fo:static-content>
      <fo:flow flow-name="xsl-region-body" line-height="1.5"> <!-- pisem do tela -->
         <fo:block break-before="page" font-size="10pt" font-family="DejaVu Serif">
            <fo:table table-layout="fixed" width="100%" border-collapse="collapse">
               <fo:table-column column-width="40%"/>
               <fo:table-column column-width="20%"/>
               <fo:table-column column-width="40%"/>
               <fo:table-body>
                  <fo:table-row>
                     <fo:table-cell>
                        <fo:block font-weight="bold">
                           <xsl:if test="@meno or @priezvisko">
                              <xsl:text>Meno:</xsl:text>
                              <xsl:if test="@meno">
                                 <xsl:text> </xsl:text>
                                 <xsl:value-of select="@meno"/>
                              </xsl:if>
                              <xsl:if test="@priezvisko">
                                 <xsl:text> </xsl:text>
                                 <xsl:value-of select="@priezvisko"/>
                              </xsl:if>
                           </xsl:if>
                           <xsl:if test="not(@meno or @priezvisko)">
                              <xsl:text>Kód: </xsl:text>
                              <xsl:value-of select="@id"/>
                           </xsl:if>
                        </fo:block>
                     </fo:table-cell>
                     <fo:table-cell>
                        <fo:block font-weight="bold">
                           <xsl:text>Trieda:</xsl:text>
                           <xsl:if test="@trieda">
                              <xsl:text> </xsl:text>
                              <xsl:value-of select="@trieda"/>
                           </xsl:if>
                           <xsl:if test="not(@trieda) and ../@trieda">
                              <xsl:text> </xsl:text>
                              <xsl:value-of select="../@trieda"/>
                           </xsl:if>
                        </fo:block>
                     </fo:table-cell>
                     <fo:table-cell>
                        <fo:block font-weight="bold">
                           <xsl:text>Dátum:</xsl:text>
                           <xsl:text> </xsl:text>
                           <xsl:value-of select="$riestest/@dat"/>
                        </fo:block>
                     </fo:table-cell>
                  </fo:table-row>
               </fo:table-body>
            </fo:table>
            <xsl:if test="pokyny/head"><xsl:apply-templates select="pokyny" mode="pdfhead"/></xsl:if>
            <fo:table table-layout="fixed" width="100%" border-collapse="collapse">
               <fo:table-column column-width="50%"/>
               <fo:table-column column-width="50%"/>
               <fo:table-body>
                  <xsl:apply-templates select="otazka">
                     <xsl:with-param name="rtest" select="$riestest" tunnel="yes"/>
                  </xsl:apply-templates>
               </fo:table-body>
            </fo:table>
            <xsl:if test="pokyny/tail"><xsl:apply-templates select="pokyny" mode="pdftail"/></xsl:if>
         </fo:block>
      </fo:flow>
   </fo:page-sequence>
</xsl:template>

<xsl:template match="pokyny" mode="pdfhead">
   <fo:block font-weight="bold"><xsl:apply-templates select="head" mode="pdfhead"/></fo:block>
</xsl:template>

<xsl:template match="head" mode="pdfhead">
   <xsl:if test="position() = last()">
      <fo:block margin-bottom="0.3cm"><xsl:apply-templates/></fo:block>
   </xsl:if>
   <xsl:if test="not(position() = last())">
      <fo:block><xsl:apply-templates/></fo:block>
   </xsl:if>
</xsl:template>

<xsl:template match="pokyny" mode="pdftail">
   <fo:block font-weight="bold"><xsl:apply-templates select="tail" mode="pdftail"/></fo:block>
</xsl:template>

<xsl:template match="tail" mode="pdftail">
   <xsl:if test="position() = 1">
      <fo:block margin-top="0.3cm"><xsl:apply-templates/></fo:block>
   </xsl:if>
   <xsl:if test="not(position() = 1)">
      <fo:block><xsl:apply-templates/></fo:block>
   </xsl:if>
</xsl:template>

<xsl:template match="otazka">
   <xsl:param name="rtest" tunnel="yes"/>
   <xsl:variable name="idotazky" select="@id"/>
   <fo:table-row keep-with-next.within-page="always" border-top="solid 1px black">
      <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
         <fo:block start-indent="0.75cm" text-indent="-0.75cm">
            <xsl:if test="@bonus">
               <fo:inline font-weight="bold"><xsl:text>Bonusová </xsl:text><xsl:number count="otazka[@bonus]" format="1: "/></fo:inline>
               <xsl:apply-templates select="znenie"/>
            </xsl:if>
            <xsl:if test="not(@bonus)">
               <fo:inline font-weight="bold"><xsl:number count="otazka" format="01. "/></fo:inline>
               <xsl:apply-templates select="znenie"/>
            </xsl:if>
         </fo:block>
      </fo:table-cell>
   </fo:table-row>
   <xsl:variable name="vybodpoved" select="$rtest/otazka[@id = $idotazky]"/>
   <xsl:if test="odpoved">
      <xsl:apply-templates select="odpoved[position() mod 2 = 1]" mode="row">
         <xsl:with-param name="vybodpoved" select="$vybodpoved" tunnel="yes"/>
      </xsl:apply-templates>
   </xsl:if>
   <xsl:if test="not(odpoved)">
      <xsl:if test="$vybodpoved">
         <fo:table-row keep-with-previous.within-page="always" border="solid 1px black">
            <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
               <fo:block>
                  <xsl:value-of select="$vybodpoved"/>
               </fo:block>
            </fo:table-cell>
         </fo:table-row>
         <xsl:if test="$vybodpoved/@body">
            <fo:table-row keep-with-previous.within-page="always">
               <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
                  <fo:block>
                     body: <xsl:value-of select="$vybodpoved/@body"/>
                  </fo:block>
               </fo:table-cell>
            </fo:table-row>
         </xsl:if>
         <xsl:if test="$vybodpoved/@koment">
            <fo:table-row keep-with-previous.within-page="always">
               <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
                  <fo:block>
                     komentár: <xsl:value-of select="$vybodpoved/@koment"/>
                  </fo:block>
               </fo:table-cell>
            </fo:table-row>
         </xsl:if>
         <fo:table-row keep-with-previous.within-page="always">
            <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
               <fo:block margin-bottom="0.5cm"/>
            </fo:table-cell>
         </fo:table-row>
      </xsl:if>
   </xsl:if>
</xsl:template>

<xsl:template match="znenie">
   <xsl:apply-templates/>
   <xsl:if test="../@body"> (<xsl:value-of select="../@body"/>b)</xsl:if>
   <xsl:if test="not(../@body)"> (1b)</xsl:if>
</xsl:template>

<xsl:template match="odpoved" mode="row">
   <fo:table-row keep-with-previous.within-page="always">
      <xsl:apply-templates select="self::*|following-sibling::odpoved[position() &lt; 2]"/>
   </fo:table-row>
</xsl:template>

<xsl:template match="odpoved">
   <xsl:param name="rtest" tunnel="yes"/>
   <xsl:param name="vybodpoved" tunnel="yes"/>
   <fo:table-cell padding-left="0.2cm"> <!-- padding kvoli druhemu stlpcu -->
      <fo:block start-indent="0.55cm" text-indent="-0.55cm">
         <xsl:variable name="pismodp"><xsl:number count="odpoved" format="a"/></xsl:variable>
         <fo:inline font-weight="bold">
            <xsl:if test="@spravna = 1">
               <xsl:attribute name="background-color">yellow</xsl:attribute> <!-- spravnu podfarbit zlto -->
            </xsl:if>
            <xsl:if test="@spravna = 1 and $pismodp = $vybodpoved">
               <xsl:attribute name="background-color">green</xsl:attribute> <!-- spravnu ziakovu podfarbit zeleno -->
            </xsl:if>
            <xsl:if test="@spravna = 0 and $pismodp = $vybodpoved">
               <xsl:attribute name="background-color">red</xsl:attribute> <!-- nespravnu ziakovu podfarbit cerveno -->
            </xsl:if>
            <xsl:value-of select="$pismodp"/><xsl:text>)</xsl:text>
         </fo:inline>
         <xsl:text> </xsl:text>
         <xsl:apply-templates/>
      </fo:block>
   </fo:table-cell>
</xsl:template>

<xsl:template match="miesto">
   <fo:table-row keep-with-previous.within-page="always" height="30pt">
      <fo:table-cell keep-together.within-page="always" number-columns-spanned="2">
         <fo:block/>
      </fo:table-cell>
   </fo:table-row>
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
