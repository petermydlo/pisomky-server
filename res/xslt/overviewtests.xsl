<?xml version="1.1" encoding="UTF-8"?>
<xsl:stylesheet version="3.0" xml:lang="sk"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:my="http://www.spsjm.sk">
<xsl:output method="html" version="5" indent="yes" encoding="UTF-8"/>

<xsl:import href="grading.xsl"/>
<xsl:import href="head.xsl"/>

<xsl:param name="autor"/>

<xsl:template name="xsl:initial-template">
   <xsl:variable name="vsetky" select="
      collection('../xml/tests?select=*.xml;recurse=yes;on-error=ignore')/testy[@autor=$autor or @autor='' or not(@autor)] |
      collection('../xml/answers?select=*.xml;recurse=yes;on-error=ignore')/odpovede[@fileid != ''][@autor=$autor or @autor='' or not(@autor)] |
      collection('../xml/feedback?select=*.xml;recurse=yes;on-error=ignore')/feedback[@fileid != ''][@autor=$autor or @autor='' or not(@autor)]
   "/>
   <html lang="sk">
      <head>
         <title>Prehľad testov</title>
         <meta name="description" content="Prehľad testov"/>
         <meta http-equiv="Content-Type" content="application/xhtml+xml; charset=UTF-8"/>
         <meta name="viewport" content="width=device-width, initial-scale=1"/>
         <link rel="icon" type="image/svg+xml" href="/pubres/img/faviconP.svg"/>
         <xsl:call-template name="cdn-css"/>
         <link rel="stylesheet" type="text/css" href="/pubres/css/testy.css"/>
      </head>
      <body>
         <div class="flex-container-icon bg-info-subtle">
            <div>
               <a href="/admin/selectquestions"><i class="bi bi-pencil" title="Edit questions"/></a>
            </div>
            <div>
               <a href="/admin/selectcreate"><i class="bi bi-plus-circle" title="Add test"/></a>
            </div>
            <div>
               <a href="/admin/ai/importanswers"><i class="bi bi-qr-code-scan" title="Upload scanned answers"/></a>
            </div>
         </div>
         <div class="nav nav-tabs flex-container-tab bg-info-subtle bold">
            <xsl:for-each-group select="$vsetky" group-by="@predmet">
               <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
               <div>
                  <a class="nav-link navbar-brand" data-bs-toggle="tab" href="#{@predmet}">
                     <xsl:if test="position() = 1">
                        <xsl:attribute name="class">nav-link navbar-brand active</xsl:attribute>
                     </xsl:if>
                     <xsl:call-template name="predmet-icon"><xsl:with-param name="predmet" select="@predmet"/></xsl:call-template><xsl:value-of select="@predmet"/>
                  </a>
               </div>
            </xsl:for-each-group>
         </div>
         <div class="tab-content">
            <xsl:for-each-group select="$vsetky" group-by="@predmet">
               <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
               <div class="tab-pane" id="{@predmet}">
                  <xsl:if test="position() = 1">
                     <xsl:attribute name="class">tab-pane active</xsl:attribute>
                  </xsl:if>
                  <div class="grid bold bg-info">
                     <div class="grid-span span7"><xsl:call-template name="predmet-icon"><xsl:with-param name="predmet" select="@predmet"/></xsl:call-template><xsl:value-of select="@predmet"/> (<span class="autor"><xsl:value-of select="$autor"/></span>)</div>
                  </div>
                  <div class="grid bold bg-info bg-opacity-50 grid-header">
                     <div><i class="bi bi-people header-icon"/>&#160;Trieda</div>
                     <div><i class="bi bi-journal-bookmark header-icon"/>&#160;Kapitola</div>
                     <div><i class="bi bi-calendar-plus header-icon"/>&#160;Vytvorené</div>
                     <div><i class="bi bi-play-fill header-icon"/>&#160;Start</div>
                     <div><i class="bi bi-stop-fill header-icon"/>&#160;Stop</div>
                     <div><i class="bi bi-check2 header-icon"/>&#160;Odovzdané</div>
                     <div><i class="bi bi-lightning header-icon"/>&#160;Akcie</div>
                  </div>
                  <xsl:for-each-group select="current-group()" group-by="@trieda">
                     <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                     <xsl:for-each-group select="current-group()" group-by="@skupina">
                        <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                        <xsl:variable name="skupina_id" select="generate-id()"/>
                        <div class="grid skupinaToggle bg-info bg-opacity-25" role="button"
                             data-bs-toggle="collapse" data-bs-target="#{$skupina_id}">
                           <div class="zalomenie grid-span span7">
                              <span id="trieda"><xsl:value-of select="@trieda"/></span><span id="skupina"><xsl:value-of select="@skupina"/></span>
                           </div>
                        </div>
                        <div id="{$skupina_id}" class="collapse"
                             data-trieda="{@trieda}" data-skupina="{@skupina}">
                        <xsl:for-each-group select="current-group()" group-by="@kapitola">
                           <xsl:sort select="current-grouping-key()" data-type="text" order="ascending"/>
                           <xsl:for-each-group select="current-group()" group-by="string(@fileid)">
                           <xsl:sort select="(@gendat, '')[1]" data-type="text" order="ascending"/>
                           <xsl:variable name="testy-el"    select="current-group()[local-name() = 'testy']"/>
                           <xsl:variable name="ma-test"     select="exists($testy-el)"/>
                           <xsl:variable name="ma-answers"  select="exists(current-group()[local-name() = 'odpovede'])"/>
                           <xsl:variable name="ma-feedback" select="exists(current-group()[local-name() = 'feedback'])"/>
                           <xsl:variable name="vybtesty"    select="my:vybtesty(current-group()[1])"/>
                           <div class="skupina" data-fileid="{@fileid}">
                              <div class="grid" role="button" data-bs-toggle="collapse" data-bs-target=".{generate-id()}">
                                 <div class="subory-ikony">
                                    <xsl:if test="$ma-feedback"><i class="bi bi-chat-right-text text-purple" title="Feedback"/></xsl:if>
                                    <xsl:if test="$ma-answers"><i class="bi bi-pencil text-warning" title="Odpovede"/></xsl:if>
                                    <xsl:if test="$ma-test"><i class="bi bi-journal-text text-blue" title="Test"/></xsl:if>
                                 </div>
                                 <div id="kapitola">
                                    <xsl:value-of select="@kapitola"/>
                                    <xsl:if test="@fileid">
                                       <span class="sive"> (<xsl:value-of select="@fileid"/>)</span>
                                    </xsl:if>
                                 </div>
                                 <div class="sive"><xsl:value-of select="$testy-el/@gendat"/></div>
                                 <div>
                                    <span><xsl:value-of select="$testy-el/@start"/></span>
                                    <xsl:if test="$ma-test"><span class="startS penIcon" title="Start time" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-pencil"/></span></xsl:if>
                                 </div>
                                 <div>
                                    <span><xsl:value-of select="$testy-el/@stop"/></span>
                                    <xsl:if test="$ma-test"><span class="stopS penIcon" title="Stop time" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-pencil"/></span></xsl:if>
                                 </div>
                                 <div><xsl:value-of select="sort($vybtesty/odpovede/test, (), function($t) { xs:dateTime($t/@dat) })[last()]/@dat"/></div>
                                 <div>
                                    <xsl:if test="$ma-test">
                                       <span class="codes" title="Download codes" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-file-earmark"/></span>
                                       <span class="tests" title="Download tests" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-printer"/></span>
                                       <span class="results" title="Download results" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-download"/></span>
                                       <span class="groupstatistics" title="Show statistics" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-bar-chart"/></span>
                                    </xsl:if>
                                    <span class="feedback{if ($ma-feedback) then '' else ' disabled'}" title="Show feedback" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-chat-left-text"/></span>
                                    <span class="del" title="Delete tests" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-dash-square"/></span>
                                    <xsl:if test="$ma-test">
                                       <span class="regenerate{if (exists($vybtesty/odpovede/test[@dat])) then ' disabled' else ''}" title="Regenerovať otázky" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-arrow-repeat"/></span>
                                    </xsl:if>
                                 </div>
                              </div>
                              <xsl:if test="$ma-test">
                                 <div class="collapse {generate-id()}">
                                    <div class="grid">
                                       <div class="neviditelny grid-span span2"/>
                                       <div class="bold bg-info bg-opacity-25">Kód</div>
                                       <div class="bold bg-info bg-opacity-25">Start</div>
                                       <div class="bold bg-info bg-opacity-25">Stop</div>
                                       <div class="bold bg-info bg-opacity-25">Odovzdané</div>
                                       <div class="neviditelny"/>
                                    <xsl:apply-templates select="$testy-el/test">
                                       <xsl:with-param name="vybtesty" select="$vybtesty"/>
                                       <xsl:with-param name="id" select="generate-id()"/>
                                       <xsl:sort select="@priezvisko" lang="sk" data-type="text"/>
                                    </xsl:apply-templates>
                                    </div>
                                 </div>
                              </xsl:if>
                           </div>
                           </xsl:for-each-group>
                        </xsl:for-each-group>
                        </div>
                     </xsl:for-each-group>
                  </xsl:for-each-group>
               </div>
            </xsl:for-each-group>
         </div>
         <div class="modal fade" id="deleteModal" tabindex="-1" aria-labelledby="deleteModalLabel" aria-hidden="true">
            <div class="modal-dialog">
               <div class="modal-content">
                  <div class="modal-header">
                     <h5 class="modal-title" id="deleteModalLabel">Vymazať súbory</h5>
                     <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Zavrieť"/>
                  </div>
                  <div class="modal-body">
                     <p id="deleteModalDesc"/>
                     <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="delTest" checked="true"/>
                        <label class="form-check-label" for="delTest">Test</label>
                     </div>
                     <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="delAnswers" checked="true"/>
                        <label class="form-check-label" for="delAnswers">Odpovede</label>
                     </div>
                     <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="delFeedback" checked="true"/>
                        <label class="form-check-label" for="delFeedback">Feedback</label>
                     </div>
                  </div>
                  <div class="modal-footer">
                     <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Zrušiť</button>
                     <button type="button" class="btn btn-danger" id="deleteModalConfirm">Vymazať</button>
                  </div>
               </div>
            </div>
         </div>
         <xsl:call-template name="cdn-js"/>
         <script src="/pubres/js/utils.js"><xsl:comment>MyUtils</xsl:comment></script>
         <script src="/pubres/js/overviewtests.js"><xsl:comment>MyJS</xsl:comment></script>
      </body>
   </html>
</xsl:template>

<xsl:template match="test">
   <xsl:param name="id"/>
   <xsl:param name="vybtesty"/>
   <xsl:variable name="rid" select="@id"/>
   <div class="neviditelny grid-span span2"></div>
   <div class="truncate" title="{@id}"><a class="kluc" href="/admin/{@id}"><xsl:value-of select="@id"/></a></div>
   <div><span><xsl:value-of select="@start"/></span><span id="{@id}" class="startT penIcon" title="Start time" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-pencil"/></span></div>
   <div><span><xsl:value-of select="@stop"/></span><span id="{@id}" class="stopT penIcon" title="Stop time" data-bs-toggle="collapse" data-bs-target=""><i class="bi bi-pencil"/></span></div>
   <div><xsl:value-of select="$vybtesty/odpovede/test[@id = $rid]/@dat"/></div>
   <div class="neviditelny"></div>
</xsl:template>
</xsl:stylesheet>
