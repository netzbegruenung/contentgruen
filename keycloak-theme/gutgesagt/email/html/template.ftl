<#-- Gut gesagt: Rahmen aller HTML-Mails (ersetzt base/email/html/template.ftl, Keycloak 26.8.2).
     Weißer Kopf mit Wortmarke als Text (kein Bild: lädt nichts nach, keine Spam-Punkte, bleibt im Dunkelmodus lesbar),
     große kursive Schlagzeile, gelbes Band mit breitem Knopf. Farben inline. -->
<#macro emailLayout>
<!DOCTYPE html>
<html lang="${locale.language}" dir="${(ltr)?then('ltr','rtl')}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>Gut gesagt</title>
<style>
  .gg-inhalt a { color: #007830; text-decoration: underline; }
  .gg-inhalt p { margin: 0 0 14px 0; }
</style>
</head>
<body style="margin:0;padding:0;background:#ffffff;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;">
<tr><td align="center" style="padding:16px 12px 24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#ffffff;">
<tr><td style="padding:8px 24px 0 24px;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:24px;line-height:1.2;font-weight:bold;font-style:italic;color:#005437;"><span aria-hidden="true">&#128077;&nbsp;</span>Gut gesagt</td></tr>
<tr><td class="gg-inhalt" style="padding:24px 24px 8px 24px;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;color:#212121;">
<#nested>
</td></tr>
<tr><td style="padding:16px 24px 8px 24px;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:13px;line-height:1.5;color:#666666;border-top:1px solid #e0e0e0;">${msg("gutgesagtMailFuss")}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
</#macro>
<#macro schlagzeile text>
<h1 style="margin:0 0 12px 0;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:32px;line-height:1.1;font-weight:bold;font-style:italic;color:#005437;">${text}</h1>
</#macro>
<#-- Gelbes Band über die Inhaltsbreite: breiter Knopf, darunter kleine Hinweiszeile (wie das Suchband der Startseite) -->
<#macro band href label hinweis>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:20px 0;background:#f6ff7c;">
<tr><td bgcolor="#f6ff7c" style="padding:20px 20px 14px 20px;background:#f6ff7c;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
<tr><td align="center" bgcolor="#005437" style="border-radius:6px;background:#005437;">
<a href="${href}" target="_blank" style="display:block;padding:14px 20px;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:17px;font-weight:bold;line-height:1.2;color:#ffffff;text-decoration:none;border-radius:6px;border:1px solid #005437;">${label}</a>
</td></tr>
</table>
<p style="margin:10px 0 0 0;text-align:center;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:14px;line-height:1.45;color:#666666;">${hinweis}</p>
</td></tr>
</table>
</#macro>
<#macro gruss><#if user.firstName?has_content>${msg("gutgesagtHallo", user.firstName)}<#else>${msg("gutgesagtHalloOhneName")}</#if></#macro>
<#macro klartextlink href>
<p style="margin:0 0 14px 0;font-size:14px;color:#666666;">${msg("gutgesagtLinkKlartext")}<br><a href="${href}" style="color:#007830;word-break:break-all;">${href}</a></p>
</#macro>
