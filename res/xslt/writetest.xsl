<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="grading.xsl"/>
<xsl:import href="head.xsl"/>

<xsl:param name="admin" as="xs:boolean"/>

<xsl:template match="test">
   <xsl:variable name="riestest" select="my:riestest(.)"/>

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
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div id="hlavicka" class="neviditelny" kluc="{@id}" predmet="{../@predmet}" trieda="{../@trieda}" skupina="{../@skupina}" kapitola="{../@kapitola}"/>
         <div class="flex-container-icon bg-info-subtle">
            <div id="save-status" title="Uložiť odpovede">
               <i class="bi bi-cloud-check text-success" id="save-icon"/>
            </div>
            <xsl:if test="../@filesave = '1'">
               <div id="file-upload">
                  <label for="files">
                     <i class="bi bi-upload" title="Vybrať súbor"/>
                  </label>
                  <input id="files" type="file" name="files" multiple="true"/>
               </div>
            </xsl:if>
            <xsl:if test="$admin = true()">
               <div>
                  <a href="/admin/showresult/{@id}"><i class="bi bi-pencil-square" title="Start evaluation"/></a>
               </div>
            </xsl:if>
            <div>
               <xsl:if test="$admin = true()">
                  <a href="/admin#{../@predmet}"><i class="bi bi-house" title="Home"/></a>
               </xsl:if>
               <xsl:if test="$admin = false()">
                  <a href="/" id="home"><i class="bi bi-house" title="Ukončiť test"/></a>
               </xsl:if>
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
                  <xsl:value-of select="format-dateTime(current-dateTime(), '[Y0001]-[M01]-[D01]T[H01]:[m01]:[s01]')"/>
               </div>
            </div>
            <xsl:if test="../@start or ../@stop or @start or @stop">
               <div class="flex-container-head-part bg-danger-subtle">
                  <xsl:choose>
                     <xsl:when test="@start != ''">
                        <div>Začiatok: <xsl:value-of select="@start"/></div>
                     </xsl:when>
                     <xsl:when test="../@start != ''">
                        <div>Začiatok: <xsl:value-of select="../@start"/></div>
                     </xsl:when>
                  </xsl:choose>
                  <xsl:choose>
                     <xsl:when test="@stop != ''">
                        <div>Koniec: <xsl:value-of select="@stop"/></div>
                     </xsl:when>
                     <xsl:when test="../@stop != ''">
                        <div>Koniec: <xsl:value-of select="../@stop"/></div>
                     </xsl:when>
                  </xsl:choose>
               </div>
            </xsl:if>
         </div>
         <xsl:apply-templates select="pokyny" mode="head"/>
         <form id="odpovede">
            <div class="flex-container-table">
               <xsl:apply-templates select="otazka">
                  <xsl:with-param name="rtest" select="$riestest" tunnel="yes"/>
               </xsl:apply-templates>
            </div>
            <xsl:apply-templates select="pokyny" mode="tail"/>
         </form>
         <xsl:call-template name="cdn-js"/>
         <script src="/pubres/js/utils.js"><xsl:comment>MyUtils</xsl:comment></script>
         <script src="/pubres/js/test.js"><xsl:comment>MyJS</xsl:comment></script>
         <script src="/pubres/js/send_answers.js"><xsl:comment>MyJS</xsl:comment></script>
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
      <xsl:variable name="farba" select="if (@bonus) then 'bg-warning-subtle' else 'bg-info-subtle'"/>
      <div class="flex-container-table-znenie {$farba}">
         <div class="prvy">
            <div class="radio col-up">
               <input type="radio" name="h{@id}" value="bg-success-subtle" form="">✓</input>
            </div>
            <div class="radio col-up">
               <input type="radio" name="h{@id}" value="bg-danger-subtle" form="">✗</input>
            </div>
            <div class="radio col-up">
               <input type="radio" name="h{@id}" value="{$farba}" checked="true" form="">?</input>
            </div>
         </div>
         <xsl:variable name="je_rating_formular" select="exists(ancestor::testy//otazka[@rating])"/>
         <div class="posledny okraj">
            <div class="bold znenie otazka-header">
               <span>
                  <xsl:if test="@bonus"><xsl:text>Bonusová </xsl:text><xsl:number count="otazka[@bonus]" format="1: "/></xsl:if>
                  <xsl:if test="not(@bonus)"><xsl:number count="otazka" format="01. "/></xsl:if>
                  <xsl:apply-templates select="znenie"/>
               </span>
               <xsl:if test="not($je_rating_formular)">
                  <span class="ai-napoveda-btn" title="Požiadať AI o nápovedu">
                     <xsl:attribute name="data-otazka-id">
                        <xsl:value-of select="@id"/>
                     </xsl:attribute>
                     <xsl:attribute name="data-test-id">
                        <xsl:value-of select="ancestor::test/@id"/>
                     </xsl:attribute>
                     <i class="bi bi-lightbulb"/>
                  </span>
               </xsl:if>
            </div>
         </div>
      </div>
      <div class="flex-container-table-odpoved">
         <xsl:if test="odpoved">
            <div class="skryte"><input type="radio" name="{@id}" class="skryte" value="-" checked="true"/></div>
            <xsl:apply-templates select="odpoved[position() mod 2 = 1]" mode="row">
               <xsl:with-param name="idotazky" select="@id" tunnel="yes"/>
            </xsl:apply-templates>
         </xsl:if>
         <xsl:if test="@rating and not(odpoved)">
            <xsl:variable name="vybodpoved" select="$rtest/otazka[@id = @id]"/>
            <xsl:variable name="otazka_id" select="@id"/>
            <div>
               <div class="rating-wrap">
                  <div class="skryte"><input type="radio" name="{@id}" class="skryte" value="-" checked="true"/></div>
                  <xsl:for-each select="1 to 5">
                     <xsl:variable name="val" select="string(.)"/>
                     <label class="rating-label">
                        <input type="radio" name="{$otazka_id}" value="{$val}" class="odpoved skryte">
                           <xsl:if test="$val = $vybodpoved">
                              <xsl:attribute name="checked">true</xsl:attribute>
                           </xsl:if>
                        </input>
                        <i class="bi bi-star-fill rating-star"/>
                     </label>
                  </xsl:for-each>
               </div>
            </div>
         </xsl:if>
         <xsl:if test="not(odpoved) and not(@rating)">
            <xsl:variable name="vybodpoved" select="$rtest/otazka[@id = $idotazky]"/>
            <div><input type="text" class="odpoved" id="{@id}" name="{@id}" value="{$vybodpoved}"/></div>
         </xsl:if>
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
   <xsl:param name="rtest" tunnel="yes"/>
   <xsl:param name="idotazky" tunnel="yes"/>
   <xsl:variable name="vybodpoved" select="$rtest/otazka[@id = $idotazky]"/>
   <div>
      <span>
         <xsl:variable name="pismodpoved">
            <xsl:number count="odpoved" format="a"/>
         </xsl:variable>
         <input type="radio" class="odpoved" name="{../@id}" value="{$pismodpoved}">
            <xsl:if test="$pismodpoved = $vybodpoved">
               <xsl:attribute name="checked">true</xsl:attribute>
            </xsl:if>
         </input>
         <xsl:apply-templates/>
      </span>
   </div>
</xsl:template>

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
