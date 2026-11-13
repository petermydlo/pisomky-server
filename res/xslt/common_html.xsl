<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema">

<!-- vyber suborov na odovzdanie (test/@filesave); odosiela ich test.js klikom na #save-status -->
<xsl:template name="file-upload">
   <div id="file-upload">
      <label for="files">
         <i class="bi bi-upload" title="Vybrať súbor"/>
      </label>
      <input id="files" type="file" name="files" multiple="true"/>
      <ul id="files-zoznam" class="files-zoznam" hidden="hidden"/>
   </div>
</xsl:template>

<!-- Tabuľka na vyplnenie. $rezim: zadanie (prázdne polia), vstup (polia na písanie), vysledok (odpoveď žiaka voči správnej),
      riesenie (správne hodnoty). $hodnoty: odpoveď žiaka rozdelená po poliach v poradí v dokumente -->
<xsl:template match="tabulka">
   <xsl:param name="rezim" select="'zadanie'"/>
   <xsl:param name="hodnoty" as="xs:string*" select="()"/>
   <table class="tabulka">
      <xsl:apply-templates select="hlavicka | riadok">
         <xsl:with-param name="rezim" select="$rezim" tunnel="yes"/>
         <xsl:with-param name="hodnoty" select="$hodnoty" tunnel="yes"/>
      </xsl:apply-templates>
   </table>
</xsl:template>

<xsl:template match="hlavicka | riadok">
   <tr><xsl:apply-templates select="bunka"/></tr>
</xsl:template>

<xsl:template match="bunka">
   <xsl:param name="rezim" tunnel="yes"/>
   <xsl:param name="hodnoty" as="xs:string*" tunnel="yes"/>
   <xsl:variable name="prvok" select="if (parent::hlavicka) then 'th' else 'td'"/>
   <xsl:variable name="poradie" select="count(preceding::bunka[@odpoved][ancestor::tabulka is current()/ancestor::tabulka]) + 1"/>
   <xsl:variable name="zadane" select="($hodnoty[$poradie], '')[1]"/>
   <xsl:variable name="dobre" select="normalize-space($zadane) != '' and lower-case(normalize-space($zadane)) = lower-case(normalize-space(@odpoved))"/>
   <xsl:element name="{$prvok}">
      <xsl:choose>
         <xsl:when test="not(@odpoved)"><xsl:apply-templates/></xsl:when>
         <xsl:when test="$rezim = 'vstup'">
            <input type="text" class="bunka-vstup form-control{if (../../@povolene) then '' else ' bunka-siroka'}" autocomplete="off" value="{$zadane}">
               <xsl:if test="../../@povolene">
                  <xsl:attribute name="data-povolene" select="../../@povolene"/>
               </xsl:if>
            </input>
         </xsl:when>
         <xsl:when test="$rezim = 'vysledok'">
            <xsl:attribute name="class" select="if ($dobre) then 'bg-success' else 'bg-danger'"/>
            <xsl:value-of select="if ($zadane = '') then '–' else $zadane"/>
            <xsl:if test="not($dobre)">
               <xsl:text> </xsl:text><span class="bunka-spravna bg-warning"><xsl:value-of select="@odpoved"/></span>
            </xsl:if>
         </xsl:when>
         <xsl:when test="$rezim = 'riesenie'">
            <xsl:attribute name="class" select="'bg-success'"/>
            <xsl:value-of select="@odpoved"/>
         </xsl:when>
         <xsl:otherwise><xsl:text>&#160;</xsl:text></xsl:otherwise>
      </xsl:choose>
   </xsl:element>
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

<xsl:template match="okno">
   <div>
      <a class="okno-odkaz" href="/pubres/{@src}" target="_blank" rel="noopener"><xsl:value-of select="@nazov"/></a>
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
