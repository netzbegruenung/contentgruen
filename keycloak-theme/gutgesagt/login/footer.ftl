<#-- Gut gesagt: Hinweiszeile unter dem Formular im gelben Band (wie auf der Startseite).
     Ersetzt keycloak.v2/login/footer.ftl (dort leer und zum Überschreiben gedacht).
     Nicht auf Info-, Fehler- und Abmeldeseiten: dort führt schon „Weiter zu Gut gesagt“ zurück.
     pageId ist der Name der Vorlage ohne .ftl (FreeMarkerLoginFormsProvider, Keycloak 26.8.2). -->
<#macro content>
<#if !["info", "error", "logout-confirm"]?seq_contains(pageId!"")>
<p class="gg-hinweis">${msg("gutgesagtHinweis")} <a href="${msg("gutgesagtStartseiteUrl")}">${msg("gutgesagtHinweisLink")}</a></p>
</#if>
</#macro>
