<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>
<xsl:import href="head.xsl"/>

<xsl:template match="statistika">
   <xsl:variable name="tests" select="doc(concat('../xml/tests/', @predmet, '/', @predmet, '_', @trieda, @skupina, '_', @kapitola, '.xml'))"/>
   <html lang="sk">
      <head>
         <title>Štatistika skupiny: <xsl:value-of select="@predmet"/> <xsl:value-of select="@trieda"/><xsl:value-of select="@skupina"/> <xsl:value-of select="@kapitola"/></title>
         <meta name="description" content="Štatistika skupiny"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <link nonce="NGINX_CSP_NONCE" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous"/>
         <link nonce="NGINX_CSP_NONCE" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
         <style nonce="NGINX_CSP_NONCE">
            <xsl:for-each select="//otazka">
               <xsl:value-of select="concat('.pb-', translate(@id, '.', '-'), ' { width: ', @percento, '%; }')"/>
            </xsl:for-each>
         </style>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <div>
               <a href="/admin#{@predmet}"><i class="bi bi-house" title="Home"/></a>
            </div>
         </div>
         <div class="okraj bold bg-info">
            <xsl:text>Štatistika: </xsl:text>
            <xsl:call-template name="predmet-icon"><xsl:with-param name="predmet" select="@predmet"/></xsl:call-template><xsl:value-of select="@predmet"/>
            <xsl:text> </xsl:text>
            <xsl:value-of select="@trieda"/>
            <xsl:value-of select="@skupina"/>
            <xsl:text> </xsl:text>
            <xsl:value-of select="@kapitola"/>
            <xsl:variable name="celk_body" select="sum(kategoria/otazka/xs:integer(@body))"/>
            <xsl:variable name="celk_max" select="sum(kategoria/otazka/xs:integer(@maxbody))"/>
            <xsl:if test="$celk_max > 0">
               <xsl:text> (</xsl:text>
               <xsl:value-of select="round($celk_body div $celk_max * 100)"/>
               <xsl:text>%)</xsl:text>
            </xsl:if>
         </div>
         <xsl:choose>
            <xsl:when test="kategoria">
               <div class="nav nav-tabs flex-container-tab bg-info-subtle bold">
                  <xsl:for-each select="kategoria">
                     <div>
                        <a class="nav-link navbar-brand" data-bs-toggle="tab" href="#{concat('kat_', @id)}" title="{if (@nazov != '') then @nazov else @id}">
                           <xsl:if test="position() = 1">
                              <xsl:attribute name="class">nav-link navbar-brand active</xsl:attribute>
                           </xsl:if>
                           <span>
                              <xsl:if test="@nazov"><xsl:attribute name="title"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
                              <xsl:value-of select="if (@nazov != '') then @nazov else @id"/>
                           </span>
                           <xsl:if test="@percento != ''">
                              <xsl:text> (</xsl:text>
                              <xsl:value-of select="@percento"/>
                              <xsl:text>%)</xsl:text>
                           </xsl:if>
                        </a>
                     </div>
                  </xsl:for-each>
               </div>
               <div class="tab-content">
                  <xsl:apply-templates select="kategoria">
                     <xsl:with-param name="tests" select="$tests" tunnel="yes"/>
                  </xsl:apply-templates>
               </div>
            </xsl:when>
            <xsl:otherwise>
               <div class="okraj">Žiadne štatistiky — žiaci ešte neodovzdali odpovede.</div>
            </xsl:otherwise>
         </xsl:choose>
         <script nonce="NGINX_CSP_NONCE" src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.min.js" integrity="sha384-G/EV+4j2dNv+tEPo3++6LCgdCROaejBqfUeNjuKAiuXbjrxilcCdDz6ZAVfHWe1Y" crossorigin="anonymous"><xsl:comment>Bootstrap</xsl:comment></script>
      </body>
   </html>
</xsl:template>

<xsl:template match="kategoria">
   <div class="tab-pane" id="{concat('kat_', @id)}">
      <xsl:if test="position() = 1">
         <xsl:attribute name="class">tab-pane active</xsl:attribute>
      </xsl:if>
      <div class="flex-container-table">
         <xsl:apply-templates select="otazka"/>
      </div>
   </div>
</xsl:template>

<xsl:template match="otazka">
   <xsl:variable name="collapse_id" select="concat('gs_', @id)"/>
   <xsl:variable name="farba">
      <xsl:choose>
         <xsl:when test="xs:integer(@percento) >= 75">bg-success-subtle</xsl:when>
         <xsl:when test="xs:integer(@percento) >= 50">bg-warning-subtle</xsl:when>
         <xsl:otherwise>bg-danger-subtle</xsl:otherwise>
      </xsl:choose>
   </xsl:variable>
   <div class="flex-container-table-otazka">
      <div class="okraj gs-riadok {$farba}" role="button" data-bs-toggle="collapse" data-bs-target="#{$collapse_id}">
         <div class="gs-id">
            <xsl:text>[</xsl:text>
            <span>
               <xsl:if test="@nazov"><xsl:attribute name="title"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
               <xsl:value-of select="if (@nazov != '') then @nazov else @id"/>
            </span>
            <xsl:text>] </xsl:text>
         </div>
         <div class="progress gs-progress">
            <div class="progress-bar pb-{@id}" role="progressbar"
                 aria-valuenow="{@percento}" aria-valuemin="0" aria-valuemax="100">
               <xsl:value-of select="@percento"/>
               <xsl:text>%</xsl:text>
            </div>
         </div>
         <xsl:if test="@spravne or @nespravne">
            <span class="tooltip-wrap gs-ikona">
               <span><i class="bi bi-bar-chart"/></span>
               <span class="tooltip-text">
                  <span class="bold"><xsl:value-of select="@spravne"/></span>
                  <xsl:text> / </xsl:text>
                  <span class="bold"><xsl:value-of select="xs:integer(@spravne) + xs:integer(@nespravne)"/></span>
                  <xsl:text> (</xsl:text>
                  <xsl:value-of select="@percento"/>
                  <xsl:text>%)</xsl:text>
               </span>
            </span>
         </xsl:if>
         <xsl:if test="not(@spravne) and not(@nespravne) and xs:integer(@maxbody) > 0">
            <span class="tooltip-wrap gs-ikona">
               <span><i class="bi bi-bar-chart"/></span>
               <span class="tooltip-text">
                  <xsl:value-of select="@body"/>
                  <xsl:text>b / </xsl:text>
                  <xsl:value-of select="@maxbody"/>
                  <xsl:text>b (</xsl:text>
                  <xsl:value-of select="@percento"/>
                  <xsl:text>%)</xsl:text>
               </span>
            </span>
         </xsl:if>
      </div>
      <xsl:if test="znenie">
         <div class="collapse okraj gs-znenie" id="{$collapse_id}">
            <xsl:apply-templates select="znenie"/>
         </div>
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

<xsl:template match="alter">
   <xsl:for-each select="choice">
      <xsl:if test="position() > 1"><xsl:text> / </xsl:text></xsl:if>
      <xsl:apply-templates/>
   </xsl:for-each>
</xsl:template>

<xsl:template match="text()">
   <xsl:if test="normalize-space(.)">
      <xsl:value-of select="."/>
   </xsl:if>
</xsl:template>

</xsl:stylesheet>
