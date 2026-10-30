# Keycloak-Realm „Gut gesagt“

Mit #429 bekommt Gut gesagt einen eigenen Realm. Sobald die App darauf umgestellt ist
(Reihenfolge unten), meldet sich jede Person darüber an; bis dahin läuft die Anmeldung wie
bisher direkt gegen den Realm der Netzbegrünung. Im eigenen Realm gibt es zwei Wege zu einem
Konto:

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
| Client `gutgesagt` | Anmeldung der App (BFF, Authorization Code mit PKCE) |
| Client `gutgesagt-einladungen` mit Dienstkonto, Rolle `manage-users` | der Semantic-Service legt damit Konten aus Einladungen an; engere Rechte für „Konto anlegen“ bietet Keycloak nicht |
| Identity Provider `netzbegruenung` | Netzbegrünung-Login; Adresse und Client sind Platzhalter |

Die Pflichtaktionen stehen bewusst nicht in der Vorlage: Eine Liste dort ersetzt die
Standardliste von Keycloak, und was fehlt, gäbe es danach im Realm nicht. Nach dem Import
deshalb von Hand:

- *Authentication → Required actions → Terms and Conditions*: `Enabled` und
  `Set as default action` an. Dann stimmt jedes neue Konto beim ersten Anmelden den
  Nutzungsbedingungen zu, auch über den Identity Provider. Ohne diesen Schritt weist
  Keycloak jedes Konto aus einer Einladung ab (`PFLICHTAKTIONEN` in
  `infrastructure/keycloak_konten.py`).

Platzhalter, vor dem Import ersetzen:

- `NETZBEGRUENUNG_REALM_URL`: Adresse des Realms der Netzbegrünung, also die bisherige
  `Keycloak:Authority` des BFF, ohne `/` am Ende.
- `NETZBEGRUENUNG_CLIENT_ID`: ein Client im Realm der Netzbegrünung, dessen Redirect-URI
  `<keycloak>/realms/gutgesagt/broker/netzbegruenung/endpoint` ist. Das Secret danach in der
  Oberfläche beim Identity Provider eintragen.
- Die Adressen von App und BFF in den Redirect-URIs von `gutgesagt`, falls nicht die
  Produktion gemeint ist. Die Vorlage erlaubt genau zwei: `/signin-oidc` der BFF und die
  App-Adresse, auf die der Link in der Mail zurückführt (`SEMANTIC_SEARCH_APP_URL`, mit `/`
  am Ende).

Keycloak erzeugt die Client-Secrets beim Import; sie stehen danach unter *Clients →
Credentials*.

Bei der Pflichtaktion zeigt Keycloak den Text `localizationTexts.de.termsText` aus der Vorlage.
Ein eigenes Theme gibt es nicht: Keycloak gibt diesen Text als HTML aus (`terms.ftl`,
`kcSanitize`), Link und Stand-Datum stehen also direkt darin. Er verlinkt die Seite
`/nutzungsbedingungen` und nennt ihren Stand, etwa „(Stand: Oktober 2026)“;
`scripts/tests/test_keycloak_nutzungsbedingungen.py` prüft, dass der Stand mit der Stand-Zeile
der Seite übereinstimmt. Keycloak speichert bei der Zustimmung nur den Zeitpunkt; welchem Text
jemand zugestimmt hat, sagt nur dieses Datum.

Bei einem neuen Stand der Nutzungsbedingungen deshalb Vorlage und Realm nachziehen: in der
Vorlage `termsText` (der Test schlägt sonst fehl), im laufenden Realm *Realm settings →
Localization → Realm overrides → de → termsText*; ein erneuter Import ändert einen bestehenden
Realm nicht. Den Zustimmungssatz „Mit „Annehmen“ stimmst du ihnen zu.“ prüft die Juristin mit
#296. Die ausdrückliche Einwilligung nach Art. 9 DSGVO als eigenes Häkchen ist in der Vorlage
noch nicht enthalten (Folgeticket).

Wie lange der Link in der Mail „Passwort festlegen“ gilt, schickt der Semantic-Service bei
jedem Aufruf mit (`MAIL_GUELTIG_SEKUNDEN` in `infrastructure/keycloak_konten.py`, drei Tage);
die Einlöseseite nennt dieselbe Frist.

## Reihenfolge beim Umstellen

Die Kennung ist der `sub` des Kontos im Realm von Gut gesagt. Für jedes Mitglied der
Netzbegrünung ist das eine **neue** Kennung: Beiträge, Stimmen, Nutzung, Admin-Kennungen
(`ADMIN_USER_IDS`, `SEMANTIC_SEARCH_ADMIN_USERS`) und die Löschliste hängen an der alten.
Deshalb in dieser Reihenfolge, nicht anders:

1. Die Datenschutzerklärung beschreibt Selbstregistrierung über eine Einladung und die
   Anmeldung über den eigenen Realm (eigenes Rechtstext-Ticket). Heute sagt sie, eine
   Selbstregistrierung gebe es nicht.
2. Die vorhandenen Kennungen sind auf die des neuen Realms umgeschrieben (Skript mit
   Trockenlauf, Teil von #429, noch offen).
3. Erst dann, gemeinsam: BFF auf den neuen Realm (`Keycloak__*`) und Einlösen im
   Semantic-Service einschalten (`SEMANTIC_SEARCH_KEYCLOAK_*`). Wer nur Einlösen einschaltet,
   verteilt Links für Konten, mit denen sich niemand in der App anmelden kann; das Dashboard
   warnt dann nicht mehr.

## Konfiguration der App

BFF (`Keycloak`-Abschnitt, in Umgebungsvariablen mit `__`):

| Variable | Wert |
|---|---|
| `Keycloak__Authority` | `<keycloak>/realms/gutgesagt` |
| `Keycloak__ClientId` | `gutgesagt` |
| `Keycloak__ClientSecret` | Secret des Clients `gutgesagt` |

Semantic-Service (Einladungen einlösen; ohne die ersten drei lassen sich Einladungen nur
verwalten, das Admin-Dashboard sagt dann, dass Links ins Leere führen). Erst zusammen mit
der BFF setzen, siehe „Reihenfolge beim Umstellen“:

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

- Eine Einladung hat eine Notiz, eine Zahl erlaubter Einlösungen und einen letzten gültigen Tag
  (UTC), sie lässt sich ab- und wieder einschalten. Gruppenlink (etwa 50 Einlösungen, vier Wochen)
  und persönlicher Link (ein Konto, zwei Wochen) sind dasselbe.
- Der Link ist `<app>/einladung#<code>`. Der Code steht hinter `#`, damit er in keinem
  Server-Log landet.
- Gezählt wird nur, wie oft eine Einladung eingelöst wurde. Am Konto steht nicht, über
  welche Einladung es entstand, und an der Einladung keine Mail-Adresse (Art. 9 DSGVO: Eine
  Einladung für eine bestimmte Gruppe verriete sonst die Zugehörigkeit). Ganz ausschließen
  lässt sich der Bezug nicht: Wer Keycloak-Admin ist, sieht, wann ein Konto entstand, und
  kann das bei einem persönlichen Link mit dem Zähler vergleichen; ebenso, wer den Zeitpunkt
  der Anfrage an `/api/v1/einladungen/einloesen` im Access-Log sieht.
- Gibt es zur Adresse schon ein Konto, antwortet die Seite wie bei einem neuen und zählt
  genauso mit; Keycloak schickt dann keine Mail, die Person meldet sich an oder nutzt
  „Passwort vergessen“. So erfährt niemand, ob eine Adresse ein Konto hat, auch nicht über
  den Zähler. Messbar bleibt nur, dass die Antwort ohne Mail etwas schneller kommt.

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
