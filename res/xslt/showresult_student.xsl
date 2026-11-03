<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<!-- Pohľad žiaka na vyhodnotený test (po odhalení učiteľom): preberá šablóny odpovedí z učiteľského showresult.xsl, bez hodnotiaceho formulára -->
<xsl:import href="showresult.xsl"/>

<xsl:template match="test">
   <xsl:variable name="riestest" select="my:riestest(.)"/>
   <xsl:variable name="sucetmaxbodov" select="my:sucetmaxbodov(.)"/>
   <xsl:variable name="sucetspravnychbodov" select="min((my:sucetziskanychbodovpresne(., $riestest), $sucetmaxbodov))"/>
   <xsl:variable name="ziskanepercenta" select="my:ziskanepercentapresne(.)"/>
   <xsl:variable name="znamka" select="my:znamka($ziskanepercenta, my:stupnica(.))"/>
   <xsl:variable name="neuplny" select="my:testneuplny(., $riestest)"/>

   <html lang="sk">
      <head>
         <title>Vyhodnotenie testu</title>
         <meta name="description" content="Stránka písomkového servera"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <div>
               <a href="/" id="home"><i class="bi bi-house" title="Domov"/></a>
            </div>
         </div>
         <div class="flex-container-head">
            <div class="flex-container-head-part bg-info-subtle">
               <div class="bold">
                  <xsl:if test="@meno or @priezvisko">
                     <xsl:text>Meno: </xsl:text>
                     <xsl:value-of select="string-join((@meno, @priezvisko), ' ')"/>
                  </xsl:if>
                  <xsl:if test="not(@meno or @priezvisko)">
                     <xsl:text>Kód: </xsl:text>
                     <xsl:value-of select="@id"/>
                  </xsl:if>
               </div>
               <div class="bold">
                  <xsl:text>Dátum: </xsl:text>
                  <xsl:value-of select="($riestest/@dat, '-')[1]"/>
               </div>
            </div>
            <div class="flex-container-head-part znamka-{$znamka}">
               <div class="bold">Hodnotenie: <xsl:value-of select="$sucetspravnychbodov"/>/<xsl:value-of select="$sucetmaxbodov"/>
                  <xsl:text> (</xsl:text><xsl:value-of select="floor($ziskanepercenta)"/>%)
               </div>
               <div class="bold">Známka: <xsl:value-of select="$znamka"/></div>
            </div>
         </div>
         <xsl:if test="$neuplny">
            <div class="pokyny bold">Niektoré otvorené otázky ešte nie sú ohodnotené, konečné hodnotenie sa môže zmeniť.</div>
         </xsl:if>
         <div class="flex-container-table">
            <xsl:apply-templates select="otazka">
               <xsl:with-param name="rtest" select="$riestest" tunnel="yes"/>
            </xsl:apply-templates>
         </div>
      </body>
   </html>
</xsl:template>

<xsl:template match="otazka">
   <xsl:param name="rtest" tunnel="yes"/>
   <xsl:variable name="vybodpoved" select="$rtest/otazka[@id = current()/@id]"/>
   <xsl:variable name="je_rating_formular" select="exists(ancestor::testy//otazka[@rating])"/>
   <xsl:variable name="je_mcq" select="exists(odpoved) and not($je_rating_formular)"/>
   <xsl:variable name="max" select="(@body, 1)[1]"/>
   <xsl:variable name="farba" select="if (@bonus) then 'bg-warning-subtle' else 'bg-info-subtle'"/>
   <div class="flex-container-table-otazka">
      <div class="flex-container-table-znenie {$farba}">
         <div class="prvy bold vystredene">
            <xsl:choose>
               <xsl:when test="@rating or $je_rating_formular"/>
               <xsl:when test="$vybodpoved/@body"><xsl:value-of select="$vybodpoved/@body"/>/<xsl:value-of select="$max"/></xsl:when>
               <xsl:when test="$je_mcq">0/<xsl:value-of select="$max"/></xsl:when>
               <xsl:otherwise><span class="sive">nehodnotené</span></xsl:otherwise>
            </xsl:choose>
         </div>
         <div class="posledny okraj">
            <div class="bold znenie">
               <xsl:if test="@bonus"><xsl:text>Bonusová </xsl:text><xsl:number count="otazka[@bonus]" format="1: "/></xsl:if>
               <xsl:if test="not(@bonus)"><xsl:number count="otazka" format="01. "/></xsl:if>
               <xsl:apply-templates select="znenie"/>
            </div>
         </div>
      </div>
      <div class="flex-container-table-odpoved">
         <xsl:choose>
            <xsl:when test="$je_mcq">
               <xsl:apply-templates select="odpoved[position() mod 2 = 1]" mode="row">
                  <xsl:with-param name="vybodpoved" select="$vybodpoved" tunnel="yes"/>
               </xsl:apply-templates>
            </xsl:when>
            <xsl:when test="@rating">
               <div>
                  <div class="rating-wrap">
                     <xsl:for-each select="1 to 5">
                        <i class="bi bi-star-fill {if (string($vybodpoved) != '' and xs:integer(.) &lt;= xs:integer(string($vybodpoved))) then 'text-warning' else 'text-secondary opacity-25'}"/>
                     </xsl:for-each>
                  </div>
               </div>
            </xsl:when>
            <xsl:otherwise>
               <div class="odpoved-siroka">
                  <xsl:if test="normalize-space($vybodpoved) = ''"><span class="sive">(bez odpovede)</span></xsl:if>
                  <xsl:if test="normalize-space($vybodpoved) != ''"><pre class="odpoved-text"><xsl:value-of select="$vybodpoved"/></pre></xsl:if>
               </div>
            </xsl:otherwise>
         </xsl:choose>
      </div>
      <xsl:if test="normalize-space($vybodpoved/@koment) != ''">
         <div class="flex-container-table-znenie">
            <div class="prvy bold vystredene">Komentár:</div>
            <div class="posledny okraj"><xsl:value-of select="$vybodpoved/@koment"/></div>
         </div>
      </xsl:if>
   </div>
</xsl:template>

</xsl:stylesheet>
