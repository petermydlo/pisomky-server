<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="grading.xsl"/>
<xsl:import href="head.xsl"/>
<xsl:import href="common_html.xsl"/>

<xsl:template match="test">
   <xsl:variable name="testid" select="@id"/>
   <xsl:variable name="riestest" select="my:riestest(.)"/>
   <xsl:variable name="sucetmaxbodov" select="my:sucetmaxbodov(.)"/>
   <xsl:variable name="sucetspravnychbodov" select="my:sucetspravnychbodov(.)"/>
   <xsl:variable name="ziskanepercenta" select="my:ziskanepercenta(.)"/>
   <xsl:variable name="znamka" select="my:znamka($ziskanepercenta)"/>

   <html lang="sk">
      <head>
         <title>
            <xsl:if test="@meno">
               <xsl:text> </xsl:text>
               <xsl:value-of select="@meno"/>
            </xsl:if>
            <xsl:if test="@priezvisko">
               <xsl:text> </xsl:text>
               <xsl:value-of select="@priezvisko"/>
            </xsl:if>
            <xsl:if test="not(@meno or @priezvisko)">
               <xsl:text> </xsl:text>
               <xsl:value-of select="@id"/>
            </xsl:if>
         </title>
         <meta name="description" content="Stránka písomkového servera"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div id="hlavicka" class="neviditelny" kluc="{$testid}" predmet="{../@predmet}" trieda="{../@trieda}" skupina="{../@skupina}" kapitola="{../@kapitola}" fileid="{../@fileid}" dat="{$riestest/@dat}"/>
         <div class="flex-container-icon bg-info-subtle">
            <div>
               <a href="/admin/downloadresult/{$testid}"><i class="bi bi-download" title="Download result"/></a>
            </div>
            <div>
               <a href="/admin/{$testid}"><i class="bi bi-pencil-square" title="End evaluation"/></a>
            </div>
            <div>
               <a id="ai-evaluate-btn" href="#"><i class="bi bi-robot" title="AI evaluation"/></a>
            </div>
            <div>
               <a href="/admin#{../@predmet}"><i class="bi bi-house" title="Home"/></a>
            </div>
         </div>
         <div class="flex-container-head">
            <div class="flex-container-head-part bg-info-subtle">
               <div class="bold">
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
               </div>
               <div class="bold">
                  <xsl:text>Trieda:</xsl:text>
                  <xsl:if test="@trieda">
                     <xsl:text> </xsl:text>
                     <xsl:value-of select="@trieda"/>
                  </xsl:if>
                  <xsl:if test="not(@trieda) and ../@trieda">
                     <xsl:text> </xsl:text>
                     <xsl:value-of select="../@trieda"/>
                  </xsl:if>
               </div>
               <div class="bold">
                  <xsl:text>Dátum:</xsl:text>
                  <xsl:text> </xsl:text>
                  <xsl:if test="$riestest/@dat">
                     <xsl:value-of select="$riestest/@dat"/>
                  </xsl:if>
                  <xsl:if test="not($riestest/@dat)">
                     <xsl:text>-</xsl:text>
                  </xsl:if>
               </div>
            </div>
            <div id="vyhodnotenie" class="flex-container-head-part znamka-{$znamka}" data-min1="{$min1}" data-min2="{$min2}" data-min3="{$min3}" data-min4="{$min4}">
               <div class="bold">Percentá: <span id="pocetpercent"><xsl:value-of select="floor($ziskanepercenta)"/></span>%
                  <xsl:text> (</xsl:text><span id="pocetbodov"><xsl:value-of select="$sucetspravnychbodov"/></span>/<xsl:value-of select="$sucetmaxbodov"/>)
               </div>
               <div class="bold" >Známka: <span id="znamka"><xsl:value-of select="$znamka"/></span></div>
            </div>
         </div>
         <xsl:apply-templates select="pokyny" mode="head"/>
         <form id="odpovede">
            <div class="flex-container-table">
               <xsl:apply-templates select="otazka">
                  <xsl:with-param name="rtest" select="$riestest" tunnel="yes"/>
               </xsl:apply-templates>
            </div>
            <xsl:apply-templates select="pokyny" mode="tail"/>
            <div class="centrovane"><button type="submit" id="ulozit" class="btn btn-outline-primary">Uložiť</button></div>
         </form>
         <xsl:call-template name="cdn-js"/>
         <script src="/pubres/js/utils.js"><xsl:comment>MyUtils</xsl:comment></script>
         <script src="/pubres/js/showresult.js"><xsl:comment>MyJS</xsl:comment></script>
         <script src="/pubres/js/send_marks.js"><xsl:comment>MyJS</xsl:comment></script>
         <script src="/pubres/js/aievaluate.js"><xsl:comment>MyJS</xsl:comment></script>
      </body>
   </html>
</xsl:template>

<xsl:template match="pokyny" mode="head">
   <xsl:if test="head">
      <div class="pokyny bold"><xsl:apply-templates select="head"/></div>
   </xsl:if>
</xsl:template>

<xsl:template match="head | tail">
   <div><xsl:apply-templates/></div>
</xsl:template>

<xsl:template match="pokyny" mode="tail">
   <xsl:if test="tail">
      <div class="pokyny bold"><xsl:apply-templates select="tail"/></div>
   </xsl:if>
</xsl:template>

<xsl:template match="otazka">
   <xsl:param name="rtest" tunnel="yes"/>
   <xsl:variable name="idotazky" select="@id"/>
   <div class="flex-container-table-otazka">
      <xsl:variable name="hodnota">
         <xsl:value-of select="$rtest/otazka[@id = $idotazky]/@body"/>
      </xsl:variable>
      <xsl:variable name="body">
         <xsl:if test="$hodnota castable as xs:integer">
            <xsl:value-of select="$hodnota"/>
         </xsl:if>
         <xsl:if test="not($hodnota castable as xs:integer)">
            <xsl:text>0</xsl:text>
         </xsl:if>
      </xsl:variable>
      <xsl:variable name="farba" select="if (@bonus) then 'bg-warning-subtle' else 'bg-info-subtle'"/>
      <xsl:variable name="zaciatok" select="if (@bonus) then 'bh' else 'h'"/>
      <xsl:variable name="je_rating_formular" select="exists(ancestor::testy//otazka[@rating])"/>
      <div class="flex-container-table-znenie {$farba}">
         <div class="prvy">
            <xsl:if test="not(odpoved) and not($je_rating_formular)">
               <div><input type="number" id="{$zaciatok}_{@id}" name="{$zaciatok}_{@id}" min="0" max="{@body}" value="{$body}"/></div>
            </xsl:if>
            <xsl:if test="odpoved or $je_rating_formular">
               <div class="radio col-up">
                  <input type="radio" name="h{@id}" value="bg-success-subtle" form="">✓</input>
               </div>
               <div class="radio col-up">
                  <input type="radio" name="h{@id}" value="bg-danger-subtle" form="">✗</input>
               </div>
               <div class="radio col-up">
                  <input type="radio" name="h{@id}" value="{$farba}" checked="true" form="">?</input>
               </div>
            </xsl:if>
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
         <xsl:variable name="vybodpoved" select="$rtest/otazka[@id = $idotazky]"/>
         <xsl:if test="odpoved and not($je_rating_formular)">
            <xsl:apply-templates select="odpoved[position() mod 2 = 1]" mode="row">
               <xsl:with-param name="vybodpoved" select="$vybodpoved" tunnel="yes"/>
            </xsl:apply-templates>
         </xsl:if>
         <xsl:if test="@rating">
            <!-- zobraz vybranú hviezdičku read-only -->
            <div>
               <div class="rating-wrap">
                  <xsl:for-each select="1 to 5">
                     <i class="bi bi-star-fill {if (string($vybodpoved) != '' and xs:integer(.) &lt;= xs:integer(string($vybodpoved))) then 'text-warning' else 'text-secondary opacity-25'}"/>
                  </xsl:for-each>
               </div>
            </div>
         </xsl:if>
         <xsl:if test="not(odpoved) and not(@rating)">
            <div><input type="text" id="{@id}" name="{@id}" size="83" value="{$vybodpoved}" readonly="true"/></div>
         </xsl:if>
      </div>
      <div class="flex-container-table-znenie">
         <div class="prvy bold vystredene">
            Komentár:
         </div>
         <xsl:variable name="komentar" select="$rtest/otazka[@id = $idotazky]/@koment"/>
         <div class="posledny okraj">
            <input type="text" id="k_{@id}" name="k_{@id}" size="83" value="{$komentar}"/>
         </div>
      </div>
   </div>
</xsl:template>

<xsl:template match="znenie">
   <xsl:apply-templates select="node()[not(self::obrazok)]"/>
   <xsl:if test="../@body and ../@body != 0"> (<xsl:value-of select="../@body"/>b)</xsl:if>
   <xsl:if test="not(../@body)"> (1b)</xsl:if>
   <xsl:apply-templates select="obrazok"/>
</xsl:template>

<xsl:template match="odpoved" mode="row">
   <xsl:apply-templates select="self::*|following-sibling::odpoved[position() &lt; 2]"/>
</xsl:template>

<xsl:template match="odpoved">
   <xsl:param name="vybodpoved" tunnel="yes"/>
   <div>
      <xsl:variable name="pismodpoved">
         <xsl:number count="odpoved" format="a"/>
      </xsl:variable>
      <span>
         <span class="bold">
            <xsl:if test="@spravna = 1">
               <xsl:attribute name="class">bold bg-warning</xsl:attribute> <!-- spravnu podfarbit zlto -->
            </xsl:if>
            <xsl:if test="@spravna = 1 and $pismodpoved = $vybodpoved">
               <xsl:attribute name="class">bold bg-success</xsl:attribute> <!-- spravnu ziakovu podfarbit zeleno -->
            </xsl:if>
            <xsl:if test="@spravna = 0 and $pismodpoved = $vybodpoved">
               <xsl:attribute name="class">bold bg-danger</xsl:attribute> <!-- nespravnu ziakovu podfarbit cerveno -->
            </xsl:if>
            <xsl:value-of select="$pismodpoved"/><xsl:text>)</xsl:text>
         </span>
         <xsl:text> </xsl:text>
         <xsl:apply-templates/>
      </span>
   </div>
</xsl:template>

</xsl:stylesheet>
