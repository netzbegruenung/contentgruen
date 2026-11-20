<#-- Gut gesagt: Hinweiszeile unter dem Formular im gelben Band (wie auf der Startseite).
     Ersetzt keycloak.v2/login/footer.ftl (dort leer und zum Überschreiben gedacht). -->
<#macro content>
<p class="gg-hinweis">${msg("gutgesagtHinweis")} <a href="${msg("gutgesagtStartseiteUrl")}">${msg("gutgesagtHinweisLink")}</a></p>
</#macro>
