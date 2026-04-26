<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<!-- Bootstrap CSS + Bootstrap Icons – spoločné pre všetky stránky -->
<xsl:template name="cdn-css">
   <link nonce="NGINX_CSP_NONCE" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB" crossorigin="anonymous"/>
   <link nonce="NGINX_CSP_NONCE" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.13.1/font/bootstrap-icons.min.css"/>
</xsl:template>

<!-- Popper.js – vyžadovaný pre Bootstrap dropdown (napr. selectcreate) -->
<xsl:template name="cdn-popper">
   <script nonce="NGINX_CSP_NONCE" src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.11.8/dist/umd/popper.min.js" integrity="sha384-I7E8VVD/ismYTF4hNIPjVp/Zjvgyol6VFvRkX/vR+Vc4jQkC+hVqc2pM8ODewa9r" crossorigin="anonymous"><xsl:comment>Popper</xsl:comment></script>
</xsl:template>

<!-- Bootstrap JS samostatne -->
<xsl:template name="cdn-bootstrap-js">
   <script nonce="NGINX_CSP_NONCE" src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.min.js" integrity="sha384-G/EV+4j2dNv+tEPo3++6LCgdCROaejBqfUeNjuKAiuXbjrxilcCdDz6ZAVfHWe1Y" crossorigin="anonymous"><xsl:comment>Bootstrap</xsl:comment></script>
</xsl:template>

<!-- Bootstrap JS bez Poppera -->
<xsl:template name="cdn-js">
   <xsl:call-template name="cdn-bootstrap-js"/>
</xsl:template>

<!-- Tematická ikona predmetu -->
<xsl:template name="predmet-icon">
   <xsl:param name="predmet"/>
   <xsl:variable name="icon">
      <xsl:choose>
         <xsl:when test="starts-with($predmet, 'AUT')">bi-gear</xsl:when>
         <xsl:when test="starts-with($predmet, 'CLO')">bi-cloud</xsl:when>
         <xsl:when test="starts-with($predmet, 'PIT')">bi-cpu</xsl:when>
         <xsl:when test="starts-with($predmet, 'PRO')">bi-code-slash</xsl:when>
         <xsl:when test="starts-with($predmet, 'SXT')">bi-database</xsl:when>
         <xsl:otherwise>bi-book</xsl:otherwise>
      </xsl:choose>
   </xsl:variable>
   <i class="bi {$icon} predmet-icon"/>&#160;
</xsl:template>

</xsl:stylesheet>
