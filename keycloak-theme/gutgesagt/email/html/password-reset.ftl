<#-- Gut gesagt: eigene Fassung von base/email/html/password-reset.ftl (Keycloak 26.8.2), Knopf im gelben Band. -->
<#import "template.ftl" as layout>
<@layout.emailLayout>
<@layout.schlagzeile text=msg("gutgesagtResetTitel")/>
<p><@layout.gruss/></p>
<p>${msg("gutgesagtResetText")}</p>
<@layout.band href=link label=msg("gutgesagtResetKnopf") hinweis=msg("gutgesagtResetGueltig", linkExpirationFormatter(linkExpiration))/>
<@layout.klartextlink href=link/>
<p>${msg("gutgesagtResetIgnorieren")}</p>
</@layout.emailLayout>
