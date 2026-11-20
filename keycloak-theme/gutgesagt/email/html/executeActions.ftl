<#-- Gut gesagt: eigene Fassung von base/email/html/executeActions.ftl (Keycloak 26.8.2), Knopf im gelben Band. -->
<#outputformat "plainText">
<#assign requiredActionsText><#if requiredActions??><#list requiredActions><#items as reqActionItem>${msg("requiredAction.${reqActionItem}")}<#sep>, </#sep></#items></#list></#if></#assign>
</#outputformat>
<#import "template.ftl" as layout>
<@layout.emailLayout>
<@layout.schlagzeile text=msg("gutgesagtExecTitel")/>
<p><@layout.gruss/></p>
<p>${msg("gutgesagtExecText")}</p>
<@layout.band href=link label=msg("gutgesagtExecKnopf") hinweis=msg("gutgesagtExecGueltig", linkExpirationFormatter(linkExpiration))/>
<#if requiredActions?? && requiredActions?has_content && (requiredActions?size gt 1 || requiredActions[0] != "UPDATE_PASSWORD")><p>${msg("gutgesagtExecSchritte", requiredActionsText)}</p></#if>
<@layout.klartextlink href=link/>
<p>${msg("gutgesagtExecIgnorieren")}</p>
</@layout.emailLayout>
