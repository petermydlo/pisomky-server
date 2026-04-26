<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="head.xsl"/>
<xsl:import href="common_html.xsl"/>

<xsl:param name="admin" as="xs:boolean"/>
<xsl:param name="napovedy_zostatok" as="xs:integer" required="yes"/>

<xsl:template match="test">
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
         <div id="hlavicka" class="neviditelny" kluc="{@id}" predmet="{../@predmet}" trieda="{../@trieda}" skupina="{../@skupina}" kapitola="{../@kapitola}" fileid="{../@fileid}"/>
         <div class="flex-container-icon bg-info-subtle">
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
         <div class="flex-container-table">
            <xsl:apply-templates select="otazka"/>
         </div>
         <xsl:apply-templates select="pokyny" mode="tail"/>
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
                  <span class="ai-napoveda-btn{if ($napovedy_zostatok le 0) then ' hint-vycerpany' else ''}">
                     <xsl:attribute name="data-otazka-id">
                        <xsl:value-of select="@id"/>
                     </xsl:attribute>
                     <xsl:attribute name="data-test-id">
                        <xsl:value-of select="ancestor::test/@id"/>
                     </xsl:attribute>
                     <xsl:attribute name="title">
                        <xsl:value-of select="concat('AI help (zostatok: ', $napovedy_zostatok, ')')"/>
                     </xsl:attribute>
                     <i class="bi bi-lightbulb text-warning text-opacity-50"/>
                  </span>
               </xsl:if>
            </div>
         </div>
      </div>
      <xsl:if test="odpoved">
         <div class="flex-container-table-odpoved">
            <xsl:apply-templates select="odpoved[position() mod 2 = 1]" mode="row"/>
         </div>
      </xsl:if>
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
   <div>
      <span>
         <span class="bold"><xsl:number count="odpoved" format="a) "/></span>
         <xsl:apply-templates/>
      </span>
   </div>
</xsl:template>


</xsl:stylesheet>
