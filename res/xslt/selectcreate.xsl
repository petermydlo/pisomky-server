<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="head.xsl"/>

<xsl:param name="predmety"/>

<xsl:template name="xsl:initial-template">
   <html lang="sk">
      <head>
         <title>Písomkový server</title>
         <meta name="description" content="Vytvorenie nového testu"/>
         <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link nonce="NGINX_CSP_NONCE" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-select@1.14.0-beta3/dist/css/bootstrap-select.min.css" integrity="sha256-cwDJdubMsvIJcAYY5EXUZAuQLxSlELxFYQlxvsxdYs8=" crossorigin="anonymous"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <a href="/admin"><i class="bi bi-house" title="Home"/></a>
         </div>
         <div class="centrovane">
            <h1 class="odsadenieH">Vytvorenie nového testu</h1>
            <form id="createForm" action="/admin/createtests" method="post" class="odsadenieH">
               <div class="form-group">
                  <label for="predmet" class="form-label">Predmet</label>
                  <select id="predmet" name="predmet" class="form-select inputW" autofocus="autofocus" required="required">
                     <xsl:for-each-group select="collection('../xml/questions/?select=*.xml;recurse=yes')/kapitola" group-by="@predmet">
                        <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                        <option value="{@predmet}"><xsl:value-of select="@predmet"/></option>
                     </xsl:for-each-group>
                  </select>
                  <label for="trieda" class="form-label odsadenieHM">Trieda</label>
                  <select id="trieda" name="trieda" class="selectpicker form-control form-select inputW" title="Vyber triedu/triedy..." multiple="multiple" required="required">
                     <xsl:for-each-group select="document('../xml/lists/roster.xml')/triedy/trieda" group-by="@id">
                        <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                        <option value="{@id}"><xsl:value-of select="@id"/></option>
                     </xsl:for-each-group>
                  </select>
                  <label for="skupina" class="form-label odsadenieHM">Skupina</label>
                  <select id="skupina" name="skupina" class="form-select inputW" required="required">
                     <option value="-" class="cela">celá trieda</option>
                     <xsl:for-each-group select="document('../xml/lists/roster.xml')/triedy/trieda/student" group-by="tokenize(@skupina, ',')">
                        <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                        <xsl:variable name="classes">
                           <xsl:for-each-group select="current-group()" group-by="../@id">
                              <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                              <xsl:value-of select="translate(current-grouping-key(), '.', '_')"/>
                              <xsl:if test="position() != last()"><xsl:text> </xsl:text></xsl:if>
                           </xsl:for-each-group>
                        </xsl:variable>
                        <option value="{current-grouping-key()}" class="{$classes}" disabled="disabled"><xsl:value-of select="current-grouping-key()"/></option>
                     </xsl:for-each-group>
                  </select>
                  <label for="kapitola" class="form-label odsadenieHM">Kapitola</label>
                  <select id="kapitola" name="kapitola" class="form-select inputW" required="required">
                     <xsl:for-each-group select="collection('../xml/questions/?select=*.xml;recurse=yes')/kapitola" group-by="@id">
                        <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                        <xsl:variable name="classes">
                           <xsl:for-each-group select="current-group()" group-by="@predmet">
                              <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                              <xsl:value-of select="current-grouping-key()"/>
                              <xsl:if test="position() != last()"><xsl:text> </xsl:text></xsl:if>
                           </xsl:for-each-group>
                        </xsl:variable>
                        <option value="{@id}" class="{$classes}"><xsl:value-of select="@id"/></option>
                     </xsl:for-each-group>
                  </select>
                  <label for="start" class="form-label odsadenieHM">Start</label>
                  <input type="datetime-local" id="start" name="start" class="form-control inputW" autocomplete="off" step="60"/>
                  <label for="stop" class="form-label odsadenieHM">Stop</label>
                  <input type="datetime-local" id="stop" name="stop" class="form-control inputW" autocomplete="off" step="60"/>
                  <div class="form-check inputW dolava">
                     <input type="checkbox" id="anonymne" name="anonymne" class="form-check-input" autocomplete="off"/>
                     <label for="anonymne" class="form-check-label">Anonymné</label>
                  </div>
                  <div class="form-check inputW dolava">
                     <input type="checkbox" id="identita" name="identita" class="form-check-input" autocomplete="off"/>
                     <label for="identita" class="form-check-label">Identita</label>
                  </div>
               </div>
               <button type="submit" class="btn btn-outline-info odsadenieHM">Vytvoriť</button>
            </form>
         </div>
         <xsl:call-template name="cdn-popper"/>
         <xsl:call-template name="cdn-js"/>
         <script nonce="NGINX_CSP_NONCE" src="https://cdn.jsdelivr.net/npm/bootstrap-select@1.14.0-beta3/dist/js/bootstrap-select.min.js" integrity="sha256-obLPuLg5xxN2MC2szEaXLaN8tEKYgeCMn+TSPMxqOfE=" crossorigin="anonymous"><xsl:comment>Bootstrap-select</xsl:comment></script>
         <script src="/pubres/js/selectcreate.js"><xsl:comment>MyJS</xsl:comment></script>
      </body>
   </html>
</xsl:template>
</xsl:stylesheet>
