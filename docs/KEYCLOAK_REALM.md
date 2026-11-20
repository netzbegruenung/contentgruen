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
| Client `gutgesagt-einladungen` mit Dienstkonto, Rolle `manage-users`, Client Scope `kc-admin-api` | der Semantic-Service legt damit Konten aus Einladungen an und löscht nie benutzte nach der Frist (#538, `docs/LOESCHKONZEPT.md`); engere Rechte für „Konto anlegen“ bietet Keycloak nicht; den Scope verlangt Keycloak ab 26.8.2 (unten) |
| Identity Provider `netzbegruenung` | Netzbegrünung-Login; Adresse und Client sind Platzhalter |

Die Pflichtaktionen stehen bewusst nicht in der Vorlage: Eine Liste dort ersetzt die
Standardliste von Keycloak, und was fehlt, gäbe es danach im Realm nicht.

- *Authentication → Required actions → Terms and Conditions*: seit 0.9.8 `Enabled` und
  `Set as default action` aus. Die Nutzungsbedingungen fragt die App auf `/einwilligung` mit
  eigenem Häkchen und speichert die Zustimmung mit Stand (`docs/ART9_EINWILLIGUNG.md`); neue
  Konten bekommen keine Pflichtaktion mehr (`PFLICHTAKTIONEN` in
  `infrastructure/keycloak_konten.py` ist leer). Ein bestehender Realm schaltet sie am
  Rollout-Tag ab, erst nachdem die Zeitpunkte archiviert sind und 0.9.8 live ist; danach wird
  das Attribut `terms_and_conditions` an allen Konten gelöscht (Reihenfolge:
  `docs/ART9_EINWILLIGUNG.md`, „Keycloak“; Archiv: `docs/LOESCHKONZEPT.md`; Befehle unten).
  Keycloak überspringt eine abgeschaltete Pflichtaktion auch bei Konten, die sie noch tragen
  (26.8.2, `AuthenticationManager.getApplicableRequiredAction`).

### Attribut der alten Zustimmung löschen (Rollout 0.9.8)

Keycloak 26.8.2 führt `terms_and_conditions` im Benutzerprofil als eigenes Attribut, das über die
Admin-Schnittstelle nie schreibbar und nur lesbar ist, solange die Pflichtaktion an ist
(`DeclarativeUserProfileProviderFactory.createUserResourceValidation`). Exportieren
(`mvp/scripts/manual/keycloak_nb_zeitpunkte.py`) geht deshalb nur vorher, Löschen nur in der
Datenbank von Keycloak (Tabellen `USER_ATTRIBUTE`, `USER_ENTITY`, `REALM`; die Befehle sind für
PostgreSQL, Tabellennamen klein), nach dem Archivieren und dem Abschalten, eingeschränkt auf den
Realm `gutgesagt` und das Attribut `terms_and_conditions`.

1. Vorher die betroffenen Zeilen sichern (Personendaten): als CSV über `STDOUT`, damit die Datei
   dort entsteht, wo die Shell sie hinlenkt, mit 0600, auch wenn `psql` per `docker exec` im
   Container läuft; nach erfolgreichem Abschluss löschen, das Archiv aus dem Exportskript bleibt.
   `<psql>` ist der Aufruf in die Datenbank von Keycloak (etwa `docker exec -i <container> psql -U
   <user> <db>`):

   ```bash
   S=/opt/gutgesagt-archiv/terms_and_conditions-zeilen.csv
   (umask 077; <psql> -c "\copy (SELECT ua.* FROM user_attribute ua JOIN user_entity ue ON ue.id = ua.user_id JOIN realm r ON r.id = ue.realm_id WHERE r.name = 'gutgesagt' AND ua.name = 'terms_and_conditions') TO STDOUT WITH CSV HEADER" > "$S.neu") && mv "$S.neu" "$S" && ls -l "$S"
   ```

2. In einer Transaktion zählen, löschen, nachzählen. Die erste Zahl muss gleich „mit Zeitpunkt“
   plus „ohne lesbare Zahl“ aus dem letzten Lauf des Exportskripts sein und `DELETE n` gleich ihr,
   die zweite 0; sonst `ROLLBACK;` statt `COMMIT;`. Die SQL zählt Zeilen, das Skript Konten ohne
   Dienstkonten; weicht es ab, sind das meist Konten, die zwischen dem letzten Export und dem
   Abschalten zugestimmt haben: ihre Zeilen aus der Sicherung ins Archiv übernehmen
   (`kennung,zeitpunkt`), dann erneut. Die Zeile mit `TERMS_AND_CONDITIONS` zählt nur mit, ob es
   die Schreibweise aus Keycloak 21.0.0 gibt; steht dort mehr als 0, erst klären:

   ```sql
   SELECT count(*) FROM user_attribute ua JOIN user_entity ue ON ue.id = ua.user_id JOIN realm r ON r.id = ue.realm_id WHERE r.name = 'gutgesagt' AND ua.name = 'TERMS_AND_CONDITIONS';
   BEGIN;
   SELECT count(*) FROM user_attribute ua JOIN user_entity ue ON ue.id = ua.user_id JOIN realm r ON r.id = ue.realm_id WHERE r.name = 'gutgesagt' AND ua.name = 'terms_and_conditions';
   DELETE FROM user_attribute ua USING user_entity ue, realm r WHERE ue.id = ua.user_id AND r.id = ue.realm_id AND r.name = 'gutgesagt' AND ua.name = 'terms_and_conditions';
   SELECT count(*) FROM user_attribute ua JOIN user_entity ue ON ue.id = ua.user_id JOIN realm r ON r.id = ue.realm_id WHERE r.name = 'gutgesagt' AND ua.name = 'terms_and_conditions';
   COMMIT;
   ```

Derselbe Zeitpunkt kann noch an zwei Stellen stehen, wenn der Realm Ereignisse speichert (die
Vorlage schaltet das nicht ein): Login-Ereignisse `CUSTOM_REQUIRED_ACTION` in `EVENT_ENTITY` und
Admin-Ereignisse mit Darstellung in `ADMIN_EVENT_ENTITY`. Ist *Realm settings → Events → Save
events* an, gehen sie mit der Frist der übrigen Ereignisse; sonst ist nichts zu tun.

Danach den Benutzer-Cache leeren, sonst liefert Keycloak die alten Werte aus dem Cache: in der
Admin-Konsole im Realm `master`, Benutzermenü oben rechts → *Clear Caches* → *User Cache* →
*Clear* (braucht `manage-realm`, das Dienstkonto `gutgesagt-einladungen` hat es nicht).

Platzhalter, vor dem Import ersetzen:

- `NETZBEGRUENUNG_REALM_URL`: Adresse des Realms der Netzbegrünung, also die bisherige
  `Keycloak:Authority` des BFF, ohne `/` am Ende.
- `NETZBEGRUENUNG_CLIENT_ID`: ein Client im Realm der Netzbegrünung, dessen Redirect-URI
  `<keycloak>/realms/gutgesagt/broker/netzbegruenung/endpoint` ist. Das Secret danach in der
  Oberfläche beim Identity Provider eintragen.
- Die Adressen von App und BFF in den Redirect-URIs von `gutgesagt`, falls nicht die
  Produktion gemeint ist. Die Vorlage erlaubt genau drei, jede exakt (Keycloak vergleicht
  ohne `*` die ganze Adresse): `/signin-oidc` der BFF; `<app>/einladung/anmelden`, auf die der
  Link in der Mail nach dem Passwort führt und die gleich die Anmeldung startet; und die
  App-Adresse selbst (`SEMANTIC_SEARCH_APP_URL`, genau so geschrieben, auch beim `/` am Ende).
  Fehlt die mittlere, weist Keycloak die Mail ab, und der Semantic-Service schickt sie mit der
  App-Adresse noch einmal, mit einer Warnung im Log; man meldet sich dann selbst an.

Keycloak erzeugt die Client-Secrets beim Import; sie stehen danach unter *Clients →
Credentials*.

Bis 0.9.8 zeigte Keycloak bei der Pflichtaktion den Text `localizationTexts.de.termsText`; er ist
aus der Vorlage entfernt (#731), weil die Nutzungsbedingungen seitdem nur über das Häkchen der App
angenommen werden (NB §2). Ein bestehender Realm behält seinen Override unter *Realm settings →
Localization → Realm overrides*; er wirkt nur, solange die Pflichtaktion an ist, und kann nach dem
Abschalten weg. Die Art.-9-Einwilligung fragt die App selbst (#489, `docs/ART9_EINWILLIGUNG.md`).

Wie lange der Link in der Mail „Passwort festlegen“ gilt, schickt der Semantic-Service bei
jedem Aufruf mit (`MAIL_GUELTIG_SEKUNDEN` in `infrastructure/keycloak_konten.py`, drei Tage);
die Einlöseseite nennt dieselbe Frist.

## Theme

`keycloak-theme/gutgesagt/` ist das Login- und Mail-Theme des Realms, ohne Java und ohne
Build. Es erbt von den Themes, die Keycloak mitbringt (`keycloak.v2` für die Seiten, `base`
für die Mails), und überschreibt keine Seitenvorlage:

| Datei | Inhalt |
|---|---|
| `login/resources/css/gutgesagt.css` | Farben (nur in den `--gg-`Variablen oben, hell und dunkel, Werte aus `custom-theme.scss`), Schrift PT Sans, gelbes Band mit Logo und Name |
| `login/messages/messages_de.properties` | Seitentexte in Du-Form |
| `email/html/template.ftl` | Rahmen aller HTML-Mails (Band mit Logo, Fuß); der Inhalt bleibt die Vorlage von Keycloak |
| `email/messages/messages_de.properties` | Mailtexte in Du-Form, Betreff und Text- wie HTML-Fassung |

Das Logo der Mails lädt von `https://gutgesagt.netzbegruenung.de/marke/favicon-64-v2.png`;
blockiert ein Mailprogramm Bilder, bleibt der Name als Text. Realm overrides (*Realm settings →
Localization*) gehen den Texten des Themes vor.

Auf den Keycloak kommt das Theme per Salt (State `keycloak.theme-gutgesagt`): Er lädt das
Archiv des Git-Stands aus dem Pillar `keycloak:gutgesagt_theme_ref` und verlinkt
`themes/gutgesagt` darauf. Keycloak liest Themes aus `themes/` bei jedem Aufruf; ein neues
Theme ist ohne Neustart wählbar (*Realm settings → Themes*: Login theme und Email theme
`gutgesagt`). Ändert sich ein schon geladenes Theme, gilt die Änderung erst nach einem
Neustart von Keycloak, weil Keycloak geladene Themes zwischenspeichert.

`scripts/tests/test_keycloak_theme.py` prüft Texte (kein gerades `'`, Klammern nur als
Platzhalter), Eltern-Themes und dass Farben nur in den Variablen stehen.

## Keycloak ab 26.8.2: Admin-API-Scope

Seit Keycloak 26.8.2 nimmt die Admin-Schnittstelle nur noch Tokens an, die für sie
ausgestellt sind: Scope `kc-admin-api` im Token und die Admin-Adresse des Realms
(`<keycloak>/admin/realms/gutgesagt`) als Audience. Die Rolle `manage-users` allein reicht
nicht mehr. Beides setzt der Client Scope `kc-admin-api`, den Keycloak in jedem Realm
anlegt (beim Anlegen und bei der Migration auf 26.8.2; 26.8.0 und 26.8.1 kennen ihn noch
nicht), aber nur `admin-cli` und `security-admin-console` zuweist.

Symptom, wenn er am Client `gutgesagt-einladungen` fehlt: Jeder Aufruf der Admin-Schnittstelle
endet mit 401, und Keycloak schreibt dazu auf INFO nichts ins Log. Das trifft das Einlösen
von Einladungen, das Löschen nie benutzter Konten (#538) und `kennungen_umstellen.py`.
Ob ein Token passt, zeigt sein Inhalt (`aud`, `scope`), nicht die Token-Introspection.
Die meldet `active: false`, wenn der fragende Client nicht in der Audience steht; das ist
kein Fehler.

Die Vorlage weist den Scope dem Client als *Default* zu (`defaultClientScopes`, daneben die
übrigen Standard-Scopes, die der Client sonst vom Realm bekäme); ein neuer Realm aus der
Vorlage braucht also nichts von Hand. In einem bestehenden Realm:

- *Clients → gutgesagt-einladungen → Client scopes → Add client scope → `kc-admin-api` →
  Add → Default*.
- Nur an diesem Client, nicht realmweit: In der Liste *Client scopes* bleibt der
  *Assigned type* von `kc-admin-api` auf `None`. Sonst bekäme jeder neue Client den Scope,
  und auch die Tokens der App trügen die Audience der Admin-Schnittstelle.

## Reihenfolge beim Umstellen

Die Kennung ist der `sub` des Kontos im Realm von Gut gesagt. Für jedes Mitglied der
Netzbegrünung ist das eine **neue** Kennung: Beiträge, Stimmen, Nutzung, Admin-Kennungen
(`ADMIN_USER_IDS`, `SEMANTIC_SEARCH_ADMIN_USERS`) und die Löschliste hängen an der alten.
Deshalb in dieser Reihenfolge, nicht anders:

1. Die Datenschutzerklärung beschreibt Selbstregistrierung über eine Einladung und die
   Anmeldung über den eigenen Realm (#490); diese Fassung muss ausgerollt sein. Nach dem
   Umstellen den Satz „Bis wir die Anmeldung umgestellt haben …“ unter „Anmeldung und
   Zugang“ und den Einschub „(bis zur Umstellung vom Identitätsdienst der Netzbegrünung)“
   unter „Anmeldung über die Netzbegrünung“ entfernen.
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
verknüpft mit der alten Kennung, ohne Mail (bis 0.9.8 mit der Pflichtaktion für die
Nutzungsbedingungen, seitdem fragt sie die App). Wer sich danach mit der Netzbegrünung anmeldet, landet in genau
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
Reihenfolge.

Die Root-Shell auf den Hosts ist zsh, und dort heißt `read -p` etwas anderes (Coprozess);
also zuerst `bash` starten. Dann das Secret des Clients `gutgesagt-einladungen` mit dieser Zeile
abfragen, einzeln einfügen und das Secret eintippen; nicht zusammen mit dem nächsten Block
einfügen, `read` nähme sonst dessen erste Zeile als Secret. So landet es auch nicht in der
History.

```bash
read -rs -p 'Secret gutgesagt-einladungen: ' SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET; echo
```

```bash
curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/gutgesagt/main/mvp/scripts/manual/kennungen_umstellen.py
# Zugang zum Realm, falls im Container noch nicht gesetzt:
export SEMANTIC_SEARCH_KEYCLOAK_URL=<keycloak> SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID=gutgesagt-einladungen
export SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET
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
  bleibt derselbe, „Anna B.“; aus einem einzelnen Wort wie bisher keiner), ohne Pflichtaktion (die Nutzungsbedingungen fragt seit 0.9.8 die App), Adresse als bestätigt, und Keycloak
  schickt die Mail „Passwort festlegen“ (drei Tage gültig, danach „Passwort vergessen“). Das
  alte Passwort lässt sich nicht mitnehmen, Keycloak kennt bcrypt nicht. Bestätigt, weil die
  Adresse schon die Anmeldung des Beta-Zugangs war, und damit die Löschfrist für nie
  benutzte Konten aus Einladungen (#538) das Konto nicht entfernt, wenn die Mail ungeöffnet
  bleibt; die Beiträge liegen dann schon dort.
- Konten bekommt jeder Beta-Zugang, auch ohne Beiträge; der Trockenlauf zählt, wie viele
  der Lauf anlegt. Für Kennungen auf der Löschliste legt er keins an.
- Scheitert die Mail, bleibt das Konto (die Beiträge ziehen gleich dorthin um); der Lauf
  nennt die Kennung unter „Ab hier Kennungen“. Dann „Passwort vergessen“, oder ein Admin
  setzt in der Admin-Konsole das Passwort (*Users → Credentials*). Das gilt auch für ein
  Startkonto, dessen Adresse kein echtes Postfach ist.
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
Import deshalb vor dem Umzug laufen lassen. `beitraege_importieren.py`
nimmt stattdessen die Sitzung eines Browsers (`mvp/SCRIPTS.md`) und geht auch danach.

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
