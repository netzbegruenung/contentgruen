<#-- Gut gesagt: Rahmen aller HTML-Mails (ersetzt base/email/html/template.ftl, Keycloak 26.8.2).
     Der Inhalt kommt unverändert aus den base-Vorlagen (<#nested>, Texte *BodyHtml).
     Farben inline, weil Mailprogramme <style> oft verwerfen; der <style>-Block ist nur Zugabe
     für Links. Das Logo lädt von der App (ohne Bild bleibt der Name als Text), alt="" weil der
     Name daneben steht. -->
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
<body style="margin:0;padding:0;background:#f5f1e9;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f1e9;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;">
<tr><td style="background:#f6ff7c;padding:16px 32px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td style="padding:0 12px 0 0;vertical-align:middle;"><img src="https://gutgesagt.netzbegruenung.de/marke/favicon-64-v2.png" width="40" height="40" alt="" style="display:block;border:0;width:40px;height:40px;"></td>
<td style="vertical-align:middle;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:24px;line-height:1.2;font-weight:bold;color:#005437;">Gut gesagt</td>
</tr></table>
</td></tr>
<tr><td class="gg-inhalt" style="padding:28px 32px 14px 32px;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:16px;line-height:1.5;color:#212121;">
<#nested>
</td></tr>
<tr><td style="padding:16px 32px 24px 32px;font-family:'PT Sans',Arial,Helvetica,sans-serif;font-size:13px;line-height:1.5;color:#666666;border-top:1px solid #e0e0e0;">${msg("gutgesagtMailFuss")}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
</#macro>
