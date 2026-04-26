<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:fn="http://www.w3.org/2005/xpath-functions"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk"
   exclude-result-prefixes="#all">
<xsl:output method="xml" version="1.1" indent="yes" encoding="UTF-8"/>

<xsl:param name="seed_ext"/>
<xsl:param name="fileid"/>
<xsl:param name="predmet"/>
<xsl:param name="trieda"/>
<xsl:param name="skupina"/>
<xsl:param name="kapitola"/>
<xsl:param name="start"/>
<xsl:param name="stop"/>
<xsl:param name="anonymne"/>
<xsl:param name="identita"/>
<xsl:param name="autor"/>

<!-- Náhodné miešanie: fn:random-number-generator($seed)?permute(sekvencia)
     Vytvorí deterministický generátor seedovaný hodnotami žiaka + pozíciou + generate-id(),
     takže každý žiak dostane iné, ale reprodukovateľné poradie otázok/odpovedí.
     Seed sa skladá z mena, priezviska, externého seedu a pozície — zaručuje unikátnosť
     aj pri rovnomenných žiakoch v rovnakej triede. -->
<xsl:strip-space elements="*"/>

<xsl:variable name="vkapitola" select="document('../xml/questions/' || $predmet || '/' || $predmet || '_' || $kapitola || '.xml')/kapitola"/>

<xsl:variable name="vsetkycesty">
   <xsl:apply-templates select="$vkapitola//otazka" mode="cesta"/>
</xsl:variable>

<xsl:variable name="cesty">
   <xsl:value-of select="distinct-values(tokenize($vsetkycesty))"/>
</xsl:variable>

<xsl:template match="otazka" mode="cesta">
   <xsl:sequence select="tokenize(@cesta, ',')"/>
</xsl:template>

<xsl:template match="/triedy">
   <testy xml:lang="sk" predmet="{$predmet}" trieda="{$trieda}" skupina="{$skupina}" kapitola="{$kapitola}" fileid="{$fileid}" gendat="{format-dateTime(current-dateTime(), '[Y0001]-[M01]-[D01]T[H01]:[m01]:[s01]')}" start="{$start}" stop="{$stop}" autor="{$autor}">
      <xsl:if test="$vkapitola/@filesave = '1'">
         <xsl:attribute name="filesave">1</xsl:attribute>
      </xsl:if>
      <xsl:apply-templates select="trieda[@id = tokenize($trieda, ',')]"/>
   </testy>
</xsl:template>

<!-- Vstupný template pre regenerovanie: zdrojom su existujúce testy XML (root <testy>, nie <triedy>) -->
<xsl:template match="/testy">
   <testy xml:lang="sk" predmet="{@predmet}" trieda="{@trieda}" skupina="{@skupina}" kapitola="{@kapitola}" fileid="{@fileid}" gendat="{format-dateTime(current-dateTime(), '[Y0001]-[M01]-[D01]T[H01]:[m01]:[s01]')}" start="{@start}" stop="{@stop}" autor="{@autor}">
      <xsl:if test="$vkapitola/@filesave = '1'">
         <xsl:attribute name="filesave">1</xsl:attribute>
      </xsl:if>
      <xsl:apply-templates select="test" mode="regenerate"/>
   </testy>
</xsl:template>

<xsl:template match="test" mode="regenerate">
   <xsl:variable name="seed" select="@meno || @priezvisko || $seed_ext || position() || generate-id()"/>
   <xsl:variable name="cesta">
      <xsl:if test="$cesty != ''">
         <xsl:sequence select="fn:random-number-generator($seed)?permute(tokenize($cesty))[position() = 1]"/>
      </xsl:if>
   </xsl:variable>
   <test>
      <xsl:copy-of select="@*"/>
      <xsl:copy-of copy-namespaces="no" select="pokyny"/>
      <xsl:variable name="otazky">
         <xsl:apply-templates select="$vkapitola/kategoria[not(@deprecated) and not(@paused='1')]">
            <xsl:with-param name="seed" select="$seed"/>
            <xsl:with-param name="meno" select="@meno" tunnel="yes"/>
            <xsl:with-param name="priezvisko" select="@priezvisko" tunnel="yes"/>
            <xsl:with-param name="kod" select="@id" tunnel="yes"/>
            <xsl:with-param name="vc" select="$cesta" tunnel="yes"/>
         </xsl:apply-templates>
      </xsl:variable>
      <xsl:variable name="seed0" select="'0' || $seed || position() || generate-id()"/>
      <xsl:variable name="seed1" select="'1' || $seed || position() || generate-id()"/>
      <xsl:sequence select="$otazky/otazka[@static and not(@bonus)]"/>
      <xsl:sequence select="fn:random-number-generator($seed0)?permute($otazky/otazka[not(@static) and not(@bonus)])"/>
      <xsl:sequence select="$otazky/otazka[@bonus and @static]"/>
      <xsl:sequence select="fn:random-number-generator($seed1)?permute($otazky/otazka[@bonus and not(@static)])"/>
   </test>
</xsl:template>

<xsl:template match="trieda">
   <xsl:if test="not($skupina)">
      <xsl:apply-templates select="student"/>
   </xsl:if>
   <xsl:if test="$skupina">
      <xsl:apply-templates select="student[tokenize(@skupina, ',') = $skupina]"/>
   </xsl:if>
</xsl:template>

<xsl:template match="student">
   <xsl:variable name="seed" select="@meno || @priezvisko || $seed_ext || position() || generate-id()"/>
   <xsl:variable name="cesta">
      <xsl:if test="$cesty != ''">
         <xsl:sequence select="fn:random-number-generator($seed)?permute(tokenize($cesty))[position() = 1]"/>
      </xsl:if>
   </xsl:variable>
   <test>
      <xsl:variable name="id">
         <xsl:if test="$identita = false() and $anonymne = false()">
            <xsl:value-of select="lower-case($predmet) || lower-case($kapitola) || $fileid || generate-id()"/>
         </xsl:if>
         <xsl:if test="$identita = false() and $anonymne = true()">
            <xsl:value-of select="format-date(current-date(), '[Y01][M01][D01]') || $fileid || generate-id()"/>
         </xsl:if>
         <xsl:if test="$identita = true() and $anonymne = false()">
            <xsl:value-of select="lower-case($predmet) || lower-case($kapitola) || $fileid || my:normalizuj(lower-case(@priezvisko)) || my:normalizuj(lower-case(substring(@meno,1,1)))"/>
         </xsl:if>
         <xsl:if test="$identita = true() and $anonymne = true()">
            <xsl:value-of select="format-date(current-date(), '[Y01][M01][D01]') || $fileid || my:normalizuj(lower-case(@priezvisko)) || my:normalizuj(lower-case(substring(@meno,1,1)))"/>
         </xsl:if>
      </xsl:variable>
      <xsl:attribute name="id"><xsl:value-of select="$id"/></xsl:attribute>
      <xsl:if test="@meno and $identita = true()">
         <xsl:attribute name="meno"><xsl:value-of select="@meno"/></xsl:attribute>
      </xsl:if>
      <xsl:if test="@priezvisko and $identita = true()">
         <xsl:attribute name="priezvisko"><xsl:value-of select="@priezvisko"/></xsl:attribute>
      </xsl:if>
      <xsl:if test="../@id and $identita = true()">
         <xsl:attribute name="trieda"><xsl:value-of select="../@id"/></xsl:attribute>
      </xsl:if>
      <xsl:apply-templates select="$vkapitola/pokyny">
         <xsl:with-param name="seed" select="$seed"/>
         <xsl:with-param name="meno" select="@meno" tunnel="yes"/>
         <xsl:with-param name="priezvisko" select="@priezvisko" tunnel="yes"/>
         <xsl:with-param name="kod" select="$id" tunnel="yes"/>
      </xsl:apply-templates>
      <xsl:variable name="otazky">
         <xsl:apply-templates select="$vkapitola/kategoria[not(@deprecated) and not(@paused='1')]">
            <xsl:with-param name="seed" select="$seed"/>
            <xsl:with-param name="meno" select="@meno" tunnel="yes"/>
            <xsl:with-param name="priezvisko" select="@priezvisko" tunnel="yes"/>
            <xsl:with-param name="kod" select="$id" tunnel="yes"/>
            <xsl:with-param name="vc" select="$cesta" tunnel="yes"/>
         </xsl:apply-templates>
      </xsl:variable>
      <xsl:variable name="seed0" select="'0' || $seed || position() || generate-id()"/>
      <xsl:variable name="seed1" select="'1' || $seed || position() || generate-id()"/>
      <xsl:sequence select="$otazky/otazka[@static and not(@bonus)]"/>
      <xsl:sequence select="fn:random-number-generator($seed0)?permute($otazky/otazka[not(@static) and not(@bonus)])"/>
      <xsl:sequence select="$otazky/otazka[@bonus and @static]"/>
      <xsl:sequence select="fn:random-number-generator($seed1)?permute($otazky/otazka[@bonus and not(@static)])"/>
   </test>
</xsl:template>

<xsl:template match="pokyny">
   <xsl:param name="seed"/>
   <pokyny>
      <xsl:apply-templates select="$vkapitola/pokyny/head[@static]"/>
      <xsl:variable name="seed2" select="'2' || $seed || position() || generate-id()"/>
      <xsl:apply-templates select="fn:random-number-generator($seed2)?permute($vkapitola/pokyny/head[not(@static)])[position() = 1]"/>
      <xsl:apply-templates select="$vkapitola/pokyny/tail[@static]"/>
      <xsl:variable name="seed3" select="'3' || $seed || position() || generate-id()"/>
      <xsl:apply-templates select="fn:random-number-generator($seed3)?permute($vkapitola/pokyny/tail[not(@static)])[position() = 1]"/>
   </pokyny>
</xsl:template>

<xsl:template match="head|tail">
   <xsl:copy copy-namespaces="no">
      <xsl:apply-templates/>
   </xsl:copy>
</xsl:template>

<xsl:template match="kategoria">
   <xsl:param name="seed"/>
   <xsl:param name="vc" tunnel="yes"/>
   <xsl:variable name="pocetotazok" select="if (@pocet) then xs:integer(@pocet) else 1"/>
   <!-- vyberiem spravny pocet otazok -->
   <xsl:variable name="otazkystaticke">
      <xsl:if test="$vc != ''">
         <xsl:apply-templates select="otazka[not(@deprecated)][not(@paused='1')][@static = '1'][tokenize(@cesta, ',') = $vc or not(@cesta)][position() = 1 to $pocetotazok]">
            <xsl:with-param name="seed" select="$seed"/>
         </xsl:apply-templates>
      </xsl:if>
      <xsl:if test="$vc = ''">
         <xsl:apply-templates select="otazka[not(@deprecated)][not(@paused='1')][@static = '1'][position() = 1 to $pocetotazok]">
            <xsl:with-param name="seed" select="$seed"/>
         </xsl:apply-templates>
      </xsl:if>
   </xsl:variable>
   <xsl:variable name="zostatok" select="$pocetotazok - count($otazkystaticke/otazka)"/>
   <xsl:variable name="seed4" select="'4' || $seed || position() || generate-id()"/>
   <xsl:variable name="otazkydynamicke">
      <xsl:if test="$vc != ''">
         <xsl:apply-templates select="fn:random-number-generator($seed4)?permute(otazka[not(@deprecated)][not(@paused='1')][not(@static)][tokenize(@cesta, ',') = $vc or not(@cesta)])[position() = 1 to $zostatok]">
            <xsl:with-param name="seed" select="$seed"/>
         </xsl:apply-templates>
      </xsl:if>
      <xsl:if test="$vc = ''">
         <xsl:apply-templates select="fn:random-number-generator($seed4)?permute(otazka[not(@deprecated)][not(@paused='1')][not(@static)])[position() = 1 to $zostatok]">
            <xsl:with-param name="seed" select="$seed"/>
         </xsl:apply-templates>
      </xsl:if>
   </xsl:variable>
   <xsl:sequence select="$otazkystaticke"/>
   <xsl:sequence select="$otazkydynamicke"/>
</xsl:template>

<xsl:template match="otazka">
   <xsl:param name="seed"/>
   <otazka id="{@id}">
      <xsl:if test="../@static or @static">
         <xsl:attribute name="static">1</xsl:attribute>
      </xsl:if>
      <xsl:if test="../@bonus or @bonus">
         <xsl:attribute name="bonus">1</xsl:attribute>
      </xsl:if>
      <xsl:if test="../@rating or @rating">
         <xsl:attribute name="rating">1</xsl:attribute>
         </xsl:if>
      <xsl:if test="@body">
         <xsl:attribute name="body"><xsl:value-of select="@body"/></xsl:attribute>
      </xsl:if>
      <xsl:if test="../@body and not (@body)">
         <xsl:attribute name="body"><xsl:value-of select="../@body"/></xsl:attribute>
      </xsl:if>
      <xsl:if test="not(../@body or @body)">
         <xsl:attribute name="body">1</xsl:attribute>
      </xsl:if>
      <xsl:copy copy-namespaces="no" select="znenie">
         <xsl:apply-templates>
            <xsl:with-param name="seed" select="$seed" tunnel="yes"/>
         </xsl:apply-templates>
      </xsl:copy>
      <xsl:variable name="seed5" select="'5' || $seed || position() || generate-id()"/>
      <xsl:variable name="pomer" select="if (@pomer) then @pomer else '1:3'"/>
      <xsl:for-each select="fn:random-number-generator($seed5)?permute(my:nahodne-odpovede(odpoved, $seed5, $pomer))">
         <xsl:copy-of copy-namespaces="no" select="."/>
      </xsl:for-each>
      <xsl:apply-templates select="miesto"/>
   </otazka>
</xsl:template>

<xsl:template match="ref">
   <xsl:param name="vc" tunnel="yes"/>
   <xsl:variable name="ref_id" select="@id"/>
   <xsl:variable name="otazka" select="$vkapitola//otazka[@id = $ref_id]"/>
   <xsl:choose>
      <xsl:when test="$otazka">
         <!-- id otazky - zistime poradie neskor cez test -->
         <ref id="{$ref_id}"/>
      </xsl:when>
      <xsl:otherwise>
         <!-- id kategorie - najdi prvu otazku z tej kategorie s respektovanim cesty ziaka -->
         <xsl:variable name="kat_otazky" select="
            if ($vc != '') then
               $vkapitola//kategoria[@id = $ref_id]/otazka[not(@deprecated)][tokenize(@cesta, ',') = $vc or not(@cesta)]/@id
            else
               $vkapitola//kategoria[@id = $ref_id]/otazka[not(@deprecated)]/@id"/>
         <ref id="{$kat_otazky[1]}"/>
      </xsl:otherwise>
   </xsl:choose>
</xsl:template>

<xsl:template match="placeholder">
   <xsl:param name="meno" tunnel="yes"/>
   <xsl:param name="priezvisko" tunnel="yes"/>
   <xsl:param name="kod" tunnel="yes"/>
   <xsl:variable name="text">
      <xsl:if test="$identita = false()">
         <xsl:value-of select="$kod"/>
      </xsl:if>
      <xsl:if test="$identita = true()">
         <xsl:choose>
            <xsl:when test="@typ = 'meno'">
               <xsl:value-of select="$meno"/>
            </xsl:when>
            <xsl:when test="@typ = 'priezvisko'">
               <xsl:value-of select="$priezvisko"/>
            </xsl:when>
            <xsl:when test="@typ = 'kod'">
               <xsl:value-of select="$kod"/>
            </xsl:when>
            <xsl:when test="@typ = 'trieda'">
               <xsl:value-of select="$trieda"/>
            </xsl:when>
            <xsl:otherwise>
               <xsl:text>ERROR! Unknown value </xsl:text><xsl:value-of select="@typ"/><xsl:text>.</xsl:text>
            </xsl:otherwise>
         </xsl:choose>
      </xsl:if>
   </xsl:variable>
   <xsl:variable name="transformacia">
      <xsl:variable name="tokens" select="tokenize(@transform)"/>
      <xsl:variable name="text1">
         <xsl:choose>
            <xsl:when test="'low' = $tokens">
               <xsl:value-of select="lower-case($text)"/>
            </xsl:when>
            <xsl:when test="'upp' = $tokens">
               <xsl:value-of select="upper-case($text)"/>
            </xsl:when>
            <xsl:otherwise>
               <xsl:value-of select="$text"/>
            </xsl:otherwise>
         </xsl:choose>
      </xsl:variable>
      <xsl:variable name="text2">
         <xsl:choose>
            <xsl:when test="'rep' = $tokens">
               <xsl:value-of select="my:normalizuj($text1)"/>
            </xsl:when>
            <xsl:otherwise>
               <xsl:value-of select="$text1"/>
            </xsl:otherwise>
         </xsl:choose>
      </xsl:variable>
      <xsl:value-of select="$text2"/>
   </xsl:variable>
   <xsl:value-of select="$transformacia"/>
</xsl:template>

<xsl:template match="alter">
   <xsl:param name="seed" tunnel="yes"/>
   <xsl:variable name="seed8" select="'8' || $seed || position() || generate-id()"/>
   <xsl:apply-templates select="fn:random-number-generator($seed8)?permute(choice)[position() = 1]"/> <!-- vyberie nahodne jedno vnutro choice a aplikuje transformacie -->
</xsl:template>

<xsl:template match="br | bold | italic | underline | upp | low | sup | sub">
   <xsl:copy copy-namespaces="no"> <!-- skopiruje cely tag ... -->
      <xsl:apply-templates/> <!-- ... a na vnutro aplikuje transformacie -->
   </xsl:copy>
</xsl:template>

<xsl:template match="miesto|obrazok|table|file">
   <xsl:copy-of copy-namespaces="no" select="."/>
</xsl:template>

<xsl:template match="text()">
   <xsl:if test="normalize-space(.)">
      <xsl:value-of select="."/>
   </xsl:if>
</xsl:template>

<xsl:function name="my:hash4" as="xs:string">
   <xsl:param name="s" as="xs:string"/>
   <xsl:variable name="h" select="fold-left(string-to-codepoints($s), 5381, function($a, $c) { ($a * 33 + $c) mod 1679616 })"/>
   <xsl:variable name="chars" select="'0123456789abcdefghijklmnopqrstuvwxyz'"/>
   <xsl:variable name="d0" select="$h mod 36"/>
   <xsl:variable name="d1" select="($h idiv 36) mod 36"/>
   <xsl:variable name="d2" select="($h idiv 1296) mod 36"/>
   <xsl:variable name="d3" select="($h idiv 46656) mod 36"/>
   <xsl:value-of select="substring($chars, $d3 + 1, 1) || substring($chars, $d2 + 1, 1) || substring($chars, $d1 + 1, 1) || substring($chars, $d0 + 1, 1)"/>
</xsl:function>

<xsl:function name="my:normalizuj">
   <xsl:param name="text"/>
   <xsl:sequence select="replace(replace(normalize-unicode($text,'NFKD'),'\P{IsBasicLatin}',''), '\s', '')"/>
</xsl:function>

<xsl:function name="my:nahodne-odpovede">
   <xsl:param name="odpovede"/>
   <xsl:param name="seed"/>
   <xsl:param name="pomer"/>
   <xsl:variable name="pocet" select="tokenize($pomer, ':')"/>
   <xsl:variable name="spravnych" select="xs:integer($pocet[1])" as="xs:integer"/>
   <xsl:variable name="nespravnych" select="xs:integer($pocet[2])" as="xs:integer"/>
   <xsl:variable name="seed6" select="'6' || $seed"/>
   <xsl:variable name="seed7" select="'7' || $seed"/>
   <xsl:sequence select="fn:random-number-generator($seed6)?permute($odpovede[@spravna = '1'])[position() = 1 to $spravnych]"/>
   <xsl:sequence select="fn:random-number-generator($seed7)?permute($odpovede[@spravna = '0'])[position() = 1 to $nespravnych]"/>
</xsl:function>
</xsl:stylesheet>
