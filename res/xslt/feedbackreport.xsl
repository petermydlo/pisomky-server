<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>
<xsl:import href="head.xsl"/>

<xsl:template match="feedback">
   <html lang="sk">
      <head>
         <title>Feedback: <xsl:value-of select="@predmet"/> <xsl:value-of select="@trieda"/><xsl:value-of select="@skupina"/> <xsl:value-of select="@kapitola"/></title>
         <meta name="description" content="Feedback prehľad nápovedy"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <link nonce="NGINX_CSP_NONCE" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous"/>
         <link nonce="NGINX_CSP_NONCE" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <div>
               <a href="/admin#{@predmet}"><i class="bi bi-house" title="Home"/></a>
            </div>
         </div>
         <div class="okraj bold bg-info">
            Feedback: <xsl:call-template name="predmet-icon"><xsl:with-param name="predmet" select="@predmet"/></xsl:call-template><xsl:value-of select="@predmet"/>
            <xsl:text> </xsl:text>
            <xsl:value-of select="@trieda"/>
            <xsl:value-of select="@skupina"/>
            <xsl:text> </xsl:text>
            <xsl:value-of select="@kapitola"/>
         </div>
         <xsl:choose>
            <xsl:when test="kategoria">
               <div class="nav nav-tabs flex-container-tab bg-info-subtle bold">
                  <xsl:for-each select="kategoria">
                     <div>
                        <a class="nav-link navbar-brand" data-bs-toggle="tab" href="#{@id}" title="{if (@nazov != '') then @nazov else @id}">
                           <xsl:if test="position() = 1">
                              <xsl:attribute name="class">nav-link navbar-brand active</xsl:attribute>
                           </xsl:if>
                           <span>
                              <xsl:if test="@nazov"><xsl:attribute name="title"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
                              <xsl:value-of select="if (@nazov != '') then @nazov else @id"/>
                           </span>
                           <xsl:text> (</xsl:text>
                           <xsl:value-of select="sum(otazka/@ano)"/>
                           <xsl:text>/</xsl:text>
                           <xsl:value-of select="sum(otazka/@nie)"/>
                           <xsl:text>/</xsl:text>
                           <xsl:value-of select="sum(otazka/@nezodpovedane)"/>
                           <xsl:text>)</xsl:text>
                        </a>
                     </div>
                  </xsl:for-each>
               </div>
               <div class="tab-content">
                  <xsl:apply-templates select="kategoria"/>
               </div>
            </xsl:when>
            <xsl:otherwise>
               <div class="okraj">Žiadne záznamy feedbacku.</div>
            </xsl:otherwise>
         </xsl:choose>
         <script nonce="NGINX_CSP_NONCE" src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.min.js" integrity="sha384-G/EV+4j2dNv+tEPo3++6LCgdCROaejBqfUeNjuKAiuXbjrxilcCdDz6ZAVfHWe1Y" crossorigin="anonymous"><xsl:comment>Bootstrap</xsl:comment></script>
      </body>
   </html>
</xsl:template>

<xsl:template match="kategoria">
   <div class="tab-pane" id="{@id}">
      <xsl:if test="position() = 1">
         <xsl:attribute name="class">tab-pane active</xsl:attribute>
      </xsl:if>
      <div class="flex-container-table">
         <xsl:apply-templates select="otazka"/>
      </div>
   </div>
</xsl:template>

<xsl:template match="otazka">
   <div class="flex-container-table-otazka">
      <div class="okraj flex-container-table-znenie bg-info-subtle" role="button" data-bs-toggle="collapse" data-bs-target="#{concat('o_', @id)}">
         <div class="bold znenie">
            <xsl:text>[</xsl:text>
            <span>
               <xsl:if test="@nazov"><xsl:attribute name="title"><xsl:value-of select="@id"/></xsl:attribute></xsl:if>
               <xsl:value-of select="if (@nazov != '') then @nazov else @id"/>
            </span>
            <xsl:text>] </xsl:text>
            <xsl:value-of select="znenie"/>
         </div>
         <div class="ms-auto bold">
            <span class="feedback-stat text-success me-2"><i class="bi bi-check-circle"/><xsl:value-of select="@ano"/></span>
            <span class="feedback-stat text-danger me-2"><i class="bi bi-x-circle"/><xsl:value-of select="@nie"/></span>
            <xsl:if test="@nezodpovedane > 0">
               <span class="feedback-stat text-primary"><i class="bi bi-dash-circle"/><xsl:value-of select="@nezodpovedane"/></span>
            </xsl:if>
         </div>
      </div>
      <div class="collapse" id="{concat('o_', @id)}">
         <xsl:apply-templates select="napovedy/napoveda"/>
      </div>
   </div>
</xsl:template>


<xsl:template match="napoveda">
   <div class="okraj d-flex gap-2">
      <xsl:if test="position() > 1">
         <xsl:attribute name="style">border-top: 0</xsl:attribute>
      </xsl:if>
      <xsl:choose>
         <xsl:when test="@val = '1'">
            <i class="bi bi-check-circle text-success"/>
         </xsl:when>
         <xsl:when test="@val = '0'">
            <i class="bi bi-x-circle text-danger"/>
         </xsl:when>
         <xsl:otherwise>
            <i class="bi bi-dash-circle text-primary"/>
         </xsl:otherwise>
      </xsl:choose>
      <span class="text-muted text-nowrap">
         <div><xsl:value-of select="substring-before(@datum, 'T')"/></div>
         <div><xsl:value-of select="substring-after(@datum, 'T')"/></div>
      </span>
      <span>
         <xsl:value-of select="."/>
         <xsl:if test="@keys">
            <div class="text-muted small">[<xsl:value-of select="@keys"/>]</div>
         </xsl:if>
      </span>
   </div>
</xsl:template>

<xsl:template match="text()">
   <xsl:if test="normalize-space(.)">
      <xsl:value-of select="."/>
   </xsl:if>
</xsl:template>

</xsl:stylesheet>
