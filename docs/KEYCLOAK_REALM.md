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
Durchprobieren von Passwörtern liegen bei Keycloak. Warum so: ADR 0006
(`docs/adr/0006-eigener-realm-zaehler-statt-zuordnung.md`).

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
`/nutzungsbedingungen` und nennt ihren Stand, etwa „(Stand: 30. Oktober 2026)“;
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
2. Die vorhandenen Kennungen sind auf die des neuen Realms umgeschrieben (unten,
   „Kennungen umstellen“).
3. Erst dann, gemeinsam: BFF auf den neuen Realm (`Keycloak__*`) und Einlösen im
   Semantic-Service einschalten (`SEMANTIC_SEARCH_KEYCLOAK_*`). Wer nur Einlösen einschaltet,
   verteilt Links für Konten, mit denen sich niemand in der App anmelden kann; das Dashboard
   warnt dann nicht mehr.

## Kennungen umstellen

`mvp/scripts/manual/kennungen_umstellen.py` (#487) schreibt jede Kennung eines Mitglieds
der Netzbegrünung auf die seines Kontos im Realm um: in PostgreSQL dieselben Spalten wie
das Löschkommando (`person_loeschen.sql`), in Qdrant die vier Felder an Beiträgen. Für die
Admin-Listen gibt es die neuen Werte aus. Die Löschliste ergänzt es nur: Ein Cookie mit der
alten Kennung gilt bis zu 14 Tage weiter (Löschkonzept), die alte Zeile muss also bleiben.
Die Zuordnung kommt aus dem Realm: Ein Konto, das mit dem Identity Provider
`netzbegruenung` verknüpft ist, trägt dort die alte Kennung. Ohne `--ausfuehren` zählt es
nur, je Tabelle und Spalte und je Collection. Ein zweiter Lauf zählt null; nur einen Satz,
der stehen bleibt, weil die neue Kennung am selben Einwurf schon einen hat, nennt er
wieder.

Ein Konto im Realm entsteht für ein Mitglied sonst erst bei der ersten Anmeldung über den
Realm. Vor dem Umstellen der BFF legt das Skript es deshalb an (`--konten-anlegen`):
verknüpft mit der alten Kennung, ohne Mail, mit der Pflichtaktion für die
Nutzungsbedingungen. Wer sich danach mit der Netzbegrünung anmeldet, landet in genau
diesem Konto. Dafür braucht es die Mail-Adresse, denn im Realm ist sie der
Benutzername. Ist eine Adresse im Realm schon vergeben, etwa über eine Einladung,
verknüpft das Skript nichts und nennt die Kennung. Ob diese Person ihr Konto aus der
Einladung behält oder das verknüpfte bekommt, entscheidet ein Admin; ein zweiter Lauf
stellt sie dann um. Für Kennungen aus der Löschliste legt das Skript nie ein Konto an.

Beta-Zugänge ziehen im selben Lauf um (`--beta-zugaenge`, unten „Beta-Zugänge umziehen“).
Was ohne Konto bleibt, behält seine Kennung: Konten aus Einladungen (die haben schon die
Kennung im Realm), Autor-Werte, die keine Person bezeichnen (`system:suchanfrage`, „Gut
gesagt Team“), und Mitglieder, für die keine Adresse angegeben ist.

Die Ausgabe nennt zuerst nur Zahlen; nur die gehören in einen PR oder ein Issue. Nach der
Zeile „Ab hier Kennungen“ folgen Kennungen (Personendaten, bleiben auf dem Host) und die
neuen Werte der Listen; im Trockenlauf sind die nur eine Vorschau, weil die erst
anzulegenden Konten fehlen.

Das Image des Semantic-Service muss diesen Stand schon enthalten; ein älteres bricht mit
`ModuleNotFoundError` ab, bevor es etwas schreibt. Auf dem Host, in einer ruhigen Zeit
(eine Änderung an einem Beitrag während des Laufs kann verloren gehen), in dieser
Reihenfolge:

```bash
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/kennungen_umstellen.py
# Zugang zum Realm, falls im Container noch nicht gesetzt (Secret nicht in die History):
export SEMANTIC_SEARCH_KEYCLOAK_URL=<keycloak> SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID=gutgesagt-einladungen
read -rs SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET; export SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET
KC=(-e SEMANTIC_SEARCH_KEYCLOAK_URL -e SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID
    -e SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET)
# ADMIN_USER_IDS der BFF, die Löschliste und die Beta-Zugänge der BFF (managed-users.json)
docker cp <pfad>/managed-users.json gutgesagt-semantic-search:/tmp/managed-users.json
LISTEN=(--liste "ADMIN_USER_IDS=<Wert aus der BFF>"
        --loeschliste "$(grep -v '^#' <pfad>/geloeschte-konten.txt | paste -sd, -)"
        --beta-zugaenge /tmp/managed-users.json)

# 1. Trockenlauf: welche Kennungen haben kein Konto?
docker exec -i "${KC[@]}" gutgesagt-semantic-search python - "${LISTEN[@]}" \
  --ohne-konto-zeigen < kennungen_umstellen.py
```

2. Zu jeder Kennung eines Mitglieds aus dieser Liste die Mail-Adresse aus dem Realm der
   Netzbegrünung holen (Admin-Konsole, *Users*, Suche nach der ID) und in eine Datei
   `konten.csv` schreiben, je Zeile `kennung,mail-adresse`. Die Datei enthält
   Personendaten: nur auf dem Host, nach dem Lauf löschen.

```bash
docker cp konten.csv gutgesagt-semantic-search:/tmp/konten.csv
# 3. Trockenlauf mit den anzulegenden Konten. Deren Zeilen und Beiträge zählt er noch
#    nicht mit, er nennt nur, wie viele Konten der Lauf anlegt.
docker exec -i "${KC[@]}" gutgesagt-semantic-search python - "${LISTEN[@]}" \
  --konten-anlegen /tmp/konten.csv < kennungen_umstellen.py
# 4. Backup (mvp/scripts/backup/backup.sh), dann umstellen; Ausgabe protokollieren
docker exec -i "${KC[@]}" gutgesagt-semantic-search python - "${LISTEN[@]}" \
  --konten-anlegen /tmp/konten.csv --ausfuehren < kennungen_umstellen.py
docker exec gutgesagt-semantic-search rm /tmp/konten.csv; rm konten.csv
```

5. Die neuen Werte aus dem Lauf (Schritt 4, nicht aus einem Trockenlauf) setzen:
   `SEMANTIC_SEARCH_ADMIN_USERS`, `ADMIN_USER_IDS` und `geloeschte-konten.txt`, dazu die
   neuen Kennungen der Admins unter den Beta-Zugängen in beiden Admin-Listen.
6. Gleich danach, am selben Tag: Schritt 3 der Reihenfolge oben (BFF auf den Realm) und die
   Datei der Beta-Zugänge aus der BFF entfernen (unten). Bis dahin melden sich Mitglieder
   und Beta-Zugänge noch mit der alten Kennung an, und was sie dann anlegen, trägt sie.
   Die Mails „Passwort festlegen“ aus Schritt 4 führen zwar schon in den Realm, anmelden
   kann man sich damit in der App aber erst nach diesem Schritt.
7. Nachholen, was zwischen 4 und 6 entstand: derselbe Aufruf wie in Schritt 4, ohne
   `--konten-anlegen` (die Zuordnung steht jetzt im Realm). Erst danach die Kopie der
   Beta-Zugänge löschen, sie enthält Personendaten:

```bash
docker exec -i "${KC[@]}" gutgesagt-semantic-search python - "${LISTEN[@]}" \
  --ausfuehren < kennungen_umstellen.py
docker exec gutgesagt-semantic-search rm /tmp/managed-users.json
```

## Beta-Zugänge umziehen

Bis zum Umstellen stehen Beta-Zugänge (auch die Startkonten) in `managed-users.json` der
BFF, mit eigener Kennung (`userId`) und Passwort. Mit `--beta-zugaenge` (#488) zieht jeder
in das Konto im Realm mit seiner Mail-Adresse um:

- Gibt es zur Adresse schon ein Konto, etwa aus einer Einladung oder über die
  Netzbegrünung, gehen die Beiträge des Beta-Zugangs dorthin. Die Adresse ist im Realm
  der Benutzername; wer sie hat, ist dieselbe Person.
- Sonst legt der Lauf ein Konto an: Vor- und Nachname aus `displayName` (der Anzeigename
  bleibt derselbe, „Anna B.“; aus einem einzelnen Wort wie bisher keiner), Pflichtaktion Nutzungsbedingungen, und Keycloak schickt die
  Mail „Passwort festlegen“ (drei Tage gültig, danach „Passwort vergessen“). Das alte
  Passwort lässt sich nicht mitnehmen, Keycloak kennt bcrypt nicht.
- Konten bekommt jeder Beta-Zugang, auch ohne Beiträge; der Trockenlauf zählt, wie viele
  der Lauf anlegt. Für Kennungen auf der Löschliste legt er keins an.
- Scheitert die Mail, bleibt das Konto (die Beiträge ziehen gleich dorthin um); der Lauf
  nennt die Kennung unter „Ab hier Kennungen“. Dann „Passwort vergessen“, oder ein Admin
  setzt in der Admin-Konsole das Passwort (*Users → Credentials*) und schaltet beim Konto
  *Email verified* ein; sonst verlangt Keycloak beim Anmelden die Bestätigung per Mail
  (`verifyEmail` in der Vorlage). Das gilt auch für ein Startkonto, dessen Adresse kein
  echtes Postfach ist.
- Gehört die Adresse im Realm schon zu einer anderen alten Kennung (ein Mitglied, ein
  zweiter Beta-Zugang mit derselben Adresse), zieht der Beta-Zugang nicht um; der Lauf
  nennt ihn. Ob die beiden zusammengehören, entscheidet ein Admin.
- Der Lauf prüft die Zuordnung, bevor er ein Konto anlegt; ist sie nicht eindeutig, bricht
  er ab, ohne dass ein Konto entsteht oder eine Mail hinausgeht. Bricht er später ab (etwa
  beim Schreiben in PostgreSQL), denselben Aufruf wiederholen: Er findet die schon
  angelegten Konten über die Adresse und schickt keine zweite Mail. Welche Mails beim
  abgebrochenen Lauf scheiterten, nennt er dann nicht mehr; in der Admin-Konsole haben diese
  Konten dann noch kein Passwort (*Users → Credentials* leer), für sie „Passwort vergessen“.
- Zurück auf die Datei: Bis Schritt 6 meldet sich jeder Beta-Zugang weiter mit der Datei an.
  Vor dem Lauf (Schritt 4) ändert nichts die Daten, angelegte Konten kann ein Admin löschen.
  Nach dem Lauf tragen die Beiträge die neuen Kennungen; zurück geht es dann nur mit dem
  Backup aus Schritt 4 (`mvp/scripts/backup/restore.sh`), und was seitdem entstand, geht
  verloren.
- `isAdmin` aus der Datei gibt es im Realm nicht: Der Lauf nennt die neuen Kennungen dieser
  Admins, sie gehören in `ADMIN_USER_IDS` und `SEMANTIC_SEARCH_ADMIN_USERS`.

Danach, zusammen mit dem Umstellen der BFF, die Datei entfernen: `managed-users.json` und
ihren Mount aus Test und Produktion löschen und `ENABLE_MANAGED_AUTH=false` setzen. Eine
Direktanmeldung mit der Datei liefe sonst weiter unter der alten Kennung, deren Beiträge
schon umgezogen sind. Die Direktanmeldung bleibt im Code für die Entwicklung: Der Dev-Stack
und die E2E-Tests haben kein Keycloak und melden sich mit
`mvp/config/managed-users.example.json` an.

Was ohne Direktanmeldung nicht mehr geht: `mvp/scripts/manual/einwuerfe_importieren.py`
meldet sich mit Mail und Passwort an der BFF an, also nur über die Direktanmeldung. Einen
Import unter einem Startkonto deshalb vor dem Umzug laufen lassen.

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
