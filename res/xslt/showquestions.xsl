<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="head.xsl"/>
<xsl:import href="common_html.xsl"/>

<xsl:param name="predmet"/>
<xsl:param name="statistika"/>

<xsl:template name="xsl:initial-template">
   <xsl:variable name="stat" select="if ($statistika != '') then doc($statistika) else ()"/>
   <html lang="sk">
      <head>
         <title>Prehľad otazok</title>
         <meta name="description" content="Prehľad otázok"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <div>
               <a href="/admin#{$predmet}"><i class="bi bi-house" title="Home"/></a>
            </div>
         </div>
         <div class="nav nav-tabs flex-container-tab bg-info-subtle bold">
            <xsl:for-each-group select="collection(concat('../xml/questions/', $predmet, '?select=*.xml;on-error=ignore'))" group-by="/kapitola/@id">
               <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
               <xsl:variable name="id_kap" select="/kapitola/@id"/>
               <xsl:variable name="body_kap" select="sum($stat/statistika/otazka[@id = /kapitola//otazka/@id]/@body)"/>
               <xsl:variable name="maxbody_kap" select="sum($stat/statistika/otazka[@id = /kapitola//otazka/@id]/@maxbody)"/>
               <div>
                  <a class="nav-link navbar-brand" data-bs-toggle="tab" href="#{$id_kap}">
                  <xsl:if test="position() = 1">
                     <xsl:attribute name="class">nav-link navbar-brand active</xsl:attribute>
                  </xsl:if>
                  Kapitola: <xsl:value-of select="$id_kap"/>
                  <xsl:if test="$maxbody_kap > 0">
                     <xsl:text> (</xsl:text>
                     <xsl:value-of select="round($body_kap div $maxbody_kap * 100)"/>
                     <xsl:text>%)</xsl:text>
                  </xsl:if>
                  </a>
               </div>
            </xsl:for-each-group>
         </div>
         <div class="okraj bold bg-info">Predmet: <xsl:call-template name="predmet-icon"><xsl:with-param name="predmet" select="$predmet"/></xsl:call-template><xsl:value-of select="$predmet"/></div>
         <div class="tab-content">
            <xsl:for-each-group select="collection(concat('../xml/questions/', $predmet, '?select=*.xml;on-error=ignore'))" group-by="/kapitola/@id">
               <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
               <div class="tab-pane" id="{/kapitola/@id}">
                  <xsl:if test="position() = 1">
                     <xsl:attribute name="class">tab-pane active</xsl:attribute>
                  </xsl:if>
                  <div class="flex-container-table">
                     <!-- pokyny heads -->
                     <xsl:if test="current-group()/kapitola/pokyny/head">
                        <div class="okraj bold bg-info bg-opacity-50" role="button" data-bs-toggle="collapse" data-bs-target=".h{generate-id()}">Heads</div>
                           <xsl:apply-templates select="current-group()/kapitola/pokyny" mode="head">
                              <xsl:with-param name="id" select="concat('h', generate-id())"/>
                           </xsl:apply-templates>
                     </xsl:if>
                     <!-- pokyny tails -->
                     <xsl:if test="current-group()/kapitola/pokyny/tail">
                        <div class="okraj bold bg-info bg-opacity-50" role="button" data-bs-toggle="collapse" data-bs-target=".t{generate-id()}">Tails</div>
                           <xsl:apply-templates select="current-group()/kapitola/pokyny" mode="tail">
                              <xsl:with-param name="id" select="concat('t', generate-id())"/>
                           </xsl:apply-templates>
                     </xsl:if>
                     <!-- kategorie -->
                     <xsl:for-each select="current-group()/kapitola/kategoria">
                        <div class="pause-row">
                           <xsl:choose>
                              <xsl:when test="@deprecated='1'">
                                 <input type="checkbox" class="pause-check form-check-input flex-shrink-0" data-id="{@id}" data-typ="kategoria" disabled="disabled"/>
                              </xsl:when>
                              <xsl:otherwise>
                                 <input type="checkbox" class="pause-check form-check-input flex-shrink-0" data-id="{@id}" data-typ="kategoria">
                                    <xsl:if test="not(@paused='1')">
                                       <xsl:attribute name="checked">checked</xsl:attribute>
                                    </xsl:if>
                                 </input>
                              </xsl:otherwise>
                           </xsl:choose>
                           <div class="okraj bold bg-info bg-opacity-50 flex-grow-1" role="button" data-bs-toggle="collapse" data-bs-target=".{generate-id()}">
                           <xsl:if test="@deprecated='1'">
                                 <i class="bi bi-x" title="archivovaná"/>
                           </xsl:if>
                           <xsl:if test="@bonus">
                              <i class="bi bi-star-fill" title="bonusová"/>
                           </xsl:if>
                           <xsl:if test="@static">
                              <i class="bi bi-pin-fill" title="statická"/>
                           </xsl:if>
                           <xsl:if test="@bonus or @static">
                              <xsl:text>&#160;</xsl:text>
                           </xsl:if>
                           Kategória: <span>
                              <xsl:if test="@nazov"><xsl:attribute name="title"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
                              <xsl:value-of select="if (@nazov != '') then @nazov else @id"/>
                           </span>
                           <xsl:if test="@pocet">
                              (<xsl:value-of select="@pocet"/>)
                           </xsl:if>
                        </div>
                        </div>
                        <xsl:apply-templates select="otazka">
                           <xsl:with-param name="id" select="generate-id()"/>
                           <xsl:with-param name="stat" select="$stat"/>
                        </xsl:apply-templates>
                     </xsl:for-each>
                  </div>
               </div>
            </xsl:for-each-group>
         </div>
         <xsl:call-template name="cdn-js"/>
         <script src="/pubres/js/showquestions.js"><xsl:comment>MyJS</xsl:comment></script>
      </body>
   </html>
</xsl:template>

<xsl:template match="pokyny" mode="head">
   <xsl:param name="id"/>
   <xsl:if test="head">
      <div class="okraj bold collapse {$id}"><xsl:apply-templates select="head"/></div>
   </xsl:if>
</xsl:template>

<xsl:template match="head | tail">
   <div><xsl:apply-templates/></div>
</xsl:template>

<xsl:template match="pokyny" mode="tail">
   <xsl:param name="id"/>
   <xsl:if test="tail">
      <div class="okraj bold collapse {$id}"><xsl:apply-templates select="tail"/></div>
   </xsl:if>
</xsl:template>

<xsl:template match="otazka">
   <xsl:param name="id"/>
   <xsl:param name="stat"/>
   <!-- vypocet otazka id -->
   <xsl:variable name="otazka_id" select="@id"/>
   <xsl:variable name="stat_otazka" select="$stat/statistika/otazka[@id = $otazka_id]"/>
   <div class="collapse flex-container-table-otazka {$id}">
      <xsl:if test="position() = last()">
         <xsl:attribute name="class">collapse flex-container-table-otazka <xsl:value-of select="$id"/> mb-2</xsl:attribute>
      </xsl:if>
      <div class="pause-row-otazka">
         <xsl:choose>
            <xsl:when test="@deprecated='1' or ../@deprecated='1'">
               <input type="checkbox" class="pause-check form-check-input flex-shrink-0" data-id="{@id}" data-typ="otazka" disabled="disabled"/>
            </xsl:when>
            <xsl:otherwise>
               <input type="checkbox" class="pause-check form-check-input flex-shrink-0" data-id="{@id}" data-typ="otazka">
                  <xsl:if test="not(@paused='1')">
                     <xsl:attribute name="checked">checked</xsl:attribute>
                  </xsl:if>
               </input>
            </xsl:otherwise>
         </xsl:choose>
         <div class="okraj flex-container-table-znenie flex-wrap bg-info-subtle flex-grow-1">
         <div class="kval-hviezdicky">
            <!-- h1/h2: MCQ alebo otvorena -->
            <xsl:if test="odpoved">
               <i class="bi {if (count(odpoved[@spravna='1']) > 1) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Správne odpovede"/>
               <i class="bi {if (count(odpoved[not(@spravna='1')]) > 3) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Nesprávne odpovede"/>
            </xsl:if>
            <xsl:if test="not(odpoved)">
               <i class="bi {if (vzor) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Vzor"/>
               <i class="bi {if (klucove_slova/slovo) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Kľúčové slová"/>
            </xsl:if>
            <!-- h3: napoveda -->
            <i class="bi {if (napoveda[not(@pre)]) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Nápoveda"/>
            <span class="kval-separator"/>
            <!-- h4: uspesnost >= 90% -->
            <i class="bi {if ($stat_otazka and round($stat_otazka/@percento) >= 90) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Úspešnosť ≥ 90%"/>
            <!-- h5: rovnomernost vyberu -->
            <xsl:variable name="idealny_vyber">
               <xsl:choose>
                  <xsl:when test="@static and $stat_otazka/@pocet_vyber_kat">
                     <xsl:value-of select="round(1 div $stat_otazka/@pocet_vyber_kat * 100)"/>
                  </xsl:when>
                  <xsl:when test="not(@static) and $stat_otazka/@pocet_nestatickych_v_kat and $stat_otazka/@pocet_nestatickych_v_kat > 0">
                     <xsl:value-of select="round(($stat_otazka/@pocet_vyber_kat - $stat_otazka/@pocet_statickych_v_kat) div $stat_otazka/@pocet_nestatickych_v_kat div $stat_otazka/@pocet_vyber_kat * 100)"/>
                  </xsl:when>
                  <xsl:otherwise>0</xsl:otherwise>
               </xsl:choose>
            </xsl:variable>
            <i class="bi {if ($idealny_vyber > 0 and $stat_otazka and abs($stat_otazka/@vyber_kat_percento - $idealny_vyber) le max((round($idealny_vyber * 0.1), 10))) then 'bi-star-fill text-warning' else 'bi-star-fill opacity-25 text-secondary'}" title="Rovnomernosť výberu"/>
         </div>
         <xsl:if test="@deprecated='1' or ../@deprecated='1'">
            <i class="bi bi-x" title="archivovaná"/>
         </xsl:if>
         <xsl:if test="@bonus">
            <i class="bi bi-star-fill" title="bonusová"/>
         </xsl:if>
         <xsl:if test="@static">
            <i class="bi bi-pin-fill" title="statická"/>
         </xsl:if>
         <xsl:if test="@cesta">
            <xsl:value-of select="@cesta"/>
         </xsl:if>
         <xsl:if test="@bonus or @static or @cesta">
            <xsl:text>&#160;</xsl:text>
         </xsl:if>
         <div class="bold znenie">
            <xsl:text>[</xsl:text>
            <span>
               <xsl:if test="@nazov"><xsl:attribute name="title"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
               <xsl:value-of select="if (@nazov != '') then @nazov else @id"/>
            </span>
            <xsl:text>] </xsl:text>
            <xsl:apply-templates select="znenie">
               <xsl:with-param name="stat_otazka" select="$stat_otazka"/>
            </xsl:apply-templates>
         </div>
         <xsl:if test="not(odpoved) and (vzor or klucove_slova/slovo)">
            <span class="tooltip-wrap">
               <span><i class="bi bi-mortarboard"></i></span>
               <span class="tooltip-text">
                  <xsl:if test="vzor">
                     <span class="bold">Vzor: </span>
                     <xsl:value-of select="vzor"/>
                  </xsl:if>
                  <xsl:if test="vzor and klucove_slova/slovo"><br/></xsl:if>
                  <xsl:if test="klucove_slova/slovo">
                     <span class="bold">Kľúčové slová: </span>
                     <xsl:value-of select="string-join(klucove_slova/slovo, ', ')"/>
                  </xsl:if>
               </span>
            </span>
         </xsl:if>
         <xsl:if test="not(odpoved) and napoveda[not(@pre)]">
            <span class="tooltip-wrap">
               <span><i class="bi bi-lightbulb"/></span>
               <span class="tooltip-text">
                  <span class="bold">Nápoveda: </span>
                  <xsl:value-of select="napoveda[not(@pre)]"/>
               </span>
            </span>
         </xsl:if>
         <xsl:if test="$stat_otazka">
            <span class="tooltip-wrap">
               <span><i class="bi bi-bar-chart"/></span>
               <span class="tooltip-text">
                  <xsl:if test="$stat_otazka/@spravne">
                     <span class="bold"><xsl:value-of select="round($stat_otazka/@spravne)"/></span>
                     <xsl:text> / </xsl:text>
                     <span class="bold"><xsl:value-of select="round($stat_otazka/@spravne) + round($stat_otazka/@nespravne)"/></span>
                     <xsl:text> (</xsl:text>
                     <xsl:value-of select="round($stat_otazka/@percento)"/>
                     <xsl:text>%)</xsl:text>
                  </xsl:if>
                  <xsl:if test="not($stat_otazka/@spravne)">
                     <xsl:value-of select="round($stat_otazka/@percento)"/>
                     <xsl:text>%</xsl:text>
                  </xsl:if>
               </span>
            </span>
         </xsl:if>
         <xsl:if test="$stat_otazka/@vyber">
            <span class="tooltip-wrap">
               <span><i class="bi bi-bullseye"/></span>
               <span class="tooltip-text">
                  <xsl:value-of select="round($stat_otazka/@vyber)"/>
                  <xsl:text> (</xsl:text>
                  <xsl:value-of select="round($stat_otazka/@vyber_kat_percento)"/>
                  <xsl:text>%)</xsl:text>
               </span>
            </span>
         </xsl:if>
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
   <span>
      <xsl:apply-templates select="node()[not(self::obrazok)]"/>
      <xsl:if test="../@body and ../@body != 0"> (<xsl:value-of select="../@body"/>b)</xsl:if>
      <xsl:if test="not(../@body) and ../../@body and ../../@body != 0"> (<xsl:value-of select="../../@body"/>b)</xsl:if>
      <xsl:if test="not(../@body) and not(../../@body)"> (1b)</xsl:if>
      <xsl:apply-templates select="obrazok"/>
   </span>
</xsl:template>

<xsl:template match="odpoved" mode="row">
   <xsl:apply-templates select="self::*|following-sibling::odpoved[position() &lt; 2]"/>
</xsl:template>

<xsl:template match="odpoved">
   <div>
      <span>
         <span class="bold">
            <xsl:if test="@spravna = 1">
               <xsl:attribute name="class">bold bg-success</xsl:attribute>
            </xsl:if>
            <xsl:number count="odpoved" format="a)"/>
         </span>
         <xsl:text> </xsl:text>
         <xsl:apply-templates/>
      </span>
      <xsl:if test="@spravna = 1">
         <xsl:variable name="klic" select="@napoveda"/>
         <xsl:if test="(@napoveda and ../napoveda[@pre = $klic]) or ../napoveda[not(@pre)]">
            <span class="tooltip-wrap">
               <span><i class="bi bi-lightbulb"/></span>
               <span class="tooltip-text">
                  <xsl:if test="@napoveda and ../napoveda[@pre = $klic]">
                     <xsl:value-of select="../napoveda[@pre = $klic]"/>
                  </xsl:if>
                  <xsl:if test="../napoveda[not(@pre)]">
                     <xsl:if test="@napoveda and ../napoveda[@pre = $klic]"><br/></xsl:if>
                     <xsl:value-of select="../napoveda[not(@pre)]"/>
                  </xsl:if>
               </span>
            </span>
         </xsl:if>
      </xsl:if>
   </div>
</xsl:template>

<xsl:template match="ref">
   <xsl:variable name="ref_id" select="@id"/>
   <xsl:variable name="otazka" select="//otazka[@id = $ref_id]"/>
   <xsl:choose>
      <xsl:when test="$otazka">
         <span class="text-muted">[(<xsl:value-of select="$otazka/../@id"/>) <xsl:value-of select="$ref_id"/>]</span>
      </xsl:when>
      <xsl:otherwise>
         <span class="text-muted">[(<xsl:value-of select="$ref_id"/>)]</span>
      </xsl:otherwise>
   </xsl:choose>
</xsl:template>

<xsl:template match="placeholder | alter | table">
   <xsl:variable name="prefor"><xsl:copy-of copy-namespaces="no" select="."/></xsl:variable>
   <xsl:value-of select="serialize($prefor)"/>
</xsl:template>


</xsl:stylesheet>
