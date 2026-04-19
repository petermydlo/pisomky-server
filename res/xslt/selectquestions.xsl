<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="head.xsl"/>

<xsl:param name="predmety"/>

<xsl:template name="xsl:initial-template">
   <html lang="sk">
      <head>
         <title>Výber otázok na zobrazenie</title>
         <meta name="description" content="Výber otázok na zobrazenie"/>
         <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <a href="/admin"><i class="bi bi-house" title="Home"/></a>
         </div>
         <div class="centrovane">
            <h1 class="odsadenieH">Výber otázok na zobrazenie</h1>
            <form id="showForm" action="/admin/showquestions" method="post" class="odsadenieH">
               <div class="form-group">
                  <label for="predmet" class="form-label">Predmet</label>
                  <select id="predmet" name="predmet" class="form-select inputW" autofocus="on" required="required">
                     <xsl:for-each select="tokenize($predmety)">
                        <xsl:sort select="." data-type="text" order="ascending"/>
                        <option value="{.}"><xsl:value-of select="."/></option>
                     </xsl:for-each>
                  </select>
               </div>
               <button type="submit" class="btn btn-outline-info odsadenieHM">Zobraziť</button>
            </form>
         </div>
      </body>
   </html>
</xsl:template>
</xsl:stylesheet>
