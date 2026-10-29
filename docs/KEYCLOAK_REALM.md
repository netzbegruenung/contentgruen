# Keycloak-Realm „Gut gesagt“

Seit #429 meldet sich jede Person über einen eigenen Realm von Gut gesagt an. Darin gibt es
zwei Wege zu einem Konto:

- **Netzbegrünung-Login:** Die Netzbegrünung ist Identity Provider im Realm („Mit
  Netzbegrünung anmelden“ auf der Anmeldeseite von Keycloak). Beim ersten Anmelden legt
  Keycloak dazu ein Konto im Realm an.
- **Einladung:** Ein Admin legt im Admin-Dashboard eine Einladung an und gibt den Link weiter.
  Wer ihn öffnet, gibt eine Mail-Adresse ein; Gut gesagt legt das Konto über die
  Admin-Schnittstelle von Keycloak an, und Keycloak schickt die Mail „Passwort festlegen“.

Die **Kennung** in Gut gesagt ist in beiden Fällen der `sub` des Kontos im Realm, nicht der
im Realm der Netzbegrünung. Passwort vergessen, Mail-Bestätigung und der Schutz gegen
Durchprobieren von Passwörtern liegen bei Keycloak.

## Vorlage

`docs/keycloak/gutgesagt-realm.json` ist eine Realm-Exportdatei ohne Secrets. Sie enthält:

| Teil | Wozu |
|---|---|
| Realm `gutgesagt`, Selbstregistrierung aus | Konten entstehen nur über eine Einladung oder den Identity Provider |
| Anmelden mit Mail-Adresse, Passwort vergessen, Mail-Bestätigung, Brute-Force-Schutz | alles von Keycloak |
| Pflichtaktion „Terms and Conditions“, Standardaktion | jedes neue Konto stimmt beim ersten Anmelden den Nutzungsbedingungen zu |
| Client `gutgesagt` | Anmeldung der App (BFF, Authorization Code mit PKCE) |
| Client `gutgesagt-einladungen` mit Dienstkonto, Rolle `manage-users` | der Semantic-Service legt damit Konten aus Einladungen an; engere Rechte für „Konto anlegen“ bietet Keycloak nicht |
| Identity Provider `netzbegruenung` | Netzbegrünung-Login; Adresse und Client sind Platzhalter |
| Gültigkeit des Mail-Links, von Admins ausgelöst: 3 Tage | wie `MAIL_GUELTIG_SEKUNDEN` in `infrastructure/keycloak_konten.py` |

Platzhalter, vor dem Import ersetzen:

- `NETZBEGRUENUNG_REALM_URL`: Adresse des Realms der Netzbegrünung, also die bisherige
  `Keycloak:Authority` des BFF, ohne `/` am Ende.
- `NETZBEGRUENUNG_CLIENT_ID`: ein Client im Realm der Netzbegrünung, dessen Redirect-URI
  `<keycloak>/realms/gutgesagt/broker/netzbegruenung/endpoint` ist. Das Secret danach in der
  Oberfläche beim Identity Provider eintragen.
- Die Adressen von App und BFF in den Redirect-URIs von `gutgesagt`, falls nicht die
  Produktion gemeint ist.

Keycloak erzeugt die Client-Secrets beim Import; sie stehen danach unter *Clients →
Credentials*.

Der Text der Nutzungsbedingungen (`localizationTexts.de.termsText`) verweist nur auf die
Seite `/nutzungsbedingungen`. Den endgültigen Text samt der Einwilligung nach Art. 9 DSGVO
klärt #415. Keycloak speichert bei der Zustimmung nur einen Zeitstempel, keine Fassung;
die Fassungen deshalb archivieren.

## Konfiguration der App

BFF (`Keycloak`-Abschnitt, in Umgebungsvariablen mit `__`):

| Variable | Wert |
|---|---|
| `Keycloak__Authority` | `<keycloak>/realms/gutgesagt` |
| `Keycloak__ClientId` | `gutgesagt` |
| `Keycloak__ClientSecret` | Secret des Clients `gutgesagt` |

Semantic-Service (Einladungen einlösen; ohne die ersten drei lassen sich Einladungen nur
verwalten, das Admin-Dashboard sagt dann, dass Links ins Leere führen):

| Variable | Wert |
|---|---|
| `SEMANTIC_SEARCH_KEYCLOAK_URL` | `<keycloak>`, ohne `/realms/…` |
| `SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID` | `gutgesagt-einladungen` |
| `SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET` | Secret des Clients `gutgesagt-einladungen` |
| `SEMANTIC_SEARCH_KEYCLOAK_REALM` | `gutgesagt` (Standard) |
| `SEMANTIC_SEARCH_KEYCLOAK_APP_CLIENT_ID` | `gutgesagt`; mit der nächsten Zeile führt der Link in der Mail zurück in die App |
| `SEMANTIC_SEARCH_APP_URL` | Adresse der App, etwa `https://gutgesagt.netzbegruenung.de/` |

Der Semantic-Service muss `<keycloak>` erreichen können.

## Einladungen

- Eine Einladung hat eine Notiz, eine Zahl erlaubter Konten und einen letzten gültigen Tag
  (UTC), sie lässt sich ab- und wieder einschalten. Gruppenlink (etwa 50 Konten, vier Wochen)
  und persönlicher Link (ein Konto, zwei Wochen) sind dasselbe.
- Der Link ist `<app>/einladung#<code>`. Der Code steht hinter `#`, damit er in keinem
  Server-Log landet.
- Gezählt wird nur, wie viele Konten über eine Einladung entstanden sind. Am Konto steht
  nicht, über welche Einladung es entstand, und an der Einladung keine Mail-Adresse (Art. 9
  DSGVO: Eine Einladung für eine bestimmte Gruppe verriete sonst die Zugehörigkeit).
- Gibt es zur Adresse schon ein Konto, antwortet die Seite wie bei einem neuen und zählt
  nicht mit; die Person meldet sich an oder nutzt „Passwort vergessen“. So erfährt niemand,
  ob eine Adresse ein Konto hat.

## Grünes Netz später dazu

Das Grüne Netz kommt als weiterer Identity Provider in denselben Realm, wie
`netzbegruenung` in der Vorlage. Wer schon ein Konto hat (über eine Einladung oder die
Netzbegrünung) und sich zum ersten Mal mit dem Grünen Netz anmeldet, landet im Ablauf
*first broker login*: Keycloak findet das Konto mit derselben Mail-Adresse und verknüpft es
nach einer Bestätigung (Passwort des bestehenden Kontos oder Link per Mail). Das Konto im
Realm bleibt dasselbe, also auch seine Kennung in Gut gesagt; Beiträge gehen nicht verloren.

Schritte dann:

1. Im Grünen Netz einen Client mit der Redirect-URI
   `<keycloak>/realms/gutgesagt/broker/<alias>/endpoint` anlegen lassen.
2. Im Realm *Identity Providers → OpenID Connect v1.0* (oder *Keycloak OpenID Connect*)
   mit diesem Client anlegen, `First login flow` = `first broker login`, `Sync mode` =
   `import`. „Trust Email“ nur einschalten, wenn das Grüne Netz Mail-Adressen bestätigt.
3. In Gut gesagt ändert sich nichts.
