---
status: accepted
---

# Eigener Keycloak-Realm, Einladungen mit Zähler statt Zuordnung

Gut gesagt bekommt einen eigenen Keycloak-Realm „gutgesagt“ (#429, Entscheidung vom 28.10.2026). Er ist der einzige Anmeldepunkt der App: Die Netzbegrünung ist darin Identity Provider, später kommt das Grüne Netz dazu, und Personen ohne eines dieser Konten melden sich mit Mail-Adresse und Passwort an. Ein solches Konto entsteht nur über eine **Einladung**: Ein Admin legt sie im Admin-Dashboard an, wer den Link hat, gibt eine Mail-Adresse ein, und der Semantic-Service legt das Konto über die Admin-Schnittstelle von Keycloak an. Passwort, Mail-Bestätigung, „Passwort vergessen“ und der Schutz gegen Durchprobieren liegen bei Keycloak, nicht in Gut gesagt.

Gespeichert wird je Einladung nur, wie oft sie eingelöst wurde. Am Konto steht nicht, über welche Einladung es entstand, an der Einladung keine Mail-Adresse, und Keycloak erfährt den Code nicht. Eine Einladung für eine bestimmte Gruppe, etwa die Netzfeuerwehr, verriete sonst die Zugehörigkeit ihrer Mitglieder, und daraus lässt sich die politische Meinung ableiten (Art. 9 DSGVO). Gibt es zur Adresse schon ein Konto, antwortet die Seite wie bei einem neuen und zählt genauso mit; Keycloak schickt dann keine Mail. So verraten weder Antwort noch Zähler, ob eine Adresse ein Konto hat.

Gründe: Ein Realm nur für Gut gesagt lässt sich einrichten, ohne den Realm der Netzbegrünung zu ändern, und eine Pflichtaktion wie die Zustimmung zu den Nutzungsbedingungen trifft nur Konten von Gut gesagt. Weitere Identity Provider kommen ohne Änderung an der App dazu, und Keycloak verknüpft ein vorhandenes Konto mit ihnen, sodass die Kennung bleibt. Und Gut gesagt muss keine Passwörter halten.

## Considered Options

- Anmeldung direkt gegen den Realm der Netzbegrünung, Beta-Zugänge als Datei im BFF (bisheriger Stand): Personen ohne Netzbegrünung-Konto brauchen einen von Hand gepflegten Eintrag, und jede Pflichtaktion träfe alle Konten der Netzbegrünung.
- Eigene Registrierung mit Passwörtern in Gut gesagt: Mail-Bestätigung, Zurücksetzen und Schutz gegen Durchprobieren wären selbst zu bauen und zu betreiben.
- Am Konto speichern, über welche Einladung es entstand: erlaubte Auswertungen je Gruppe, legt aber die Zugehörigkeit offen (Art. 9 DSGVO).
- Nur angelegte Konten zählen, ein vorhandenes Konto nicht: Der Zähler verriete dann, ob eine Adresse schon ein Konto hat.

## Consequences

Mit dem Wechsel auf den Realm bekommt jedes Mitglied der Netzbegrünung eine neue Kennung; vorhandene Daten werden einmal umgeschrieben (#487), die Beta-Zugänge ziehen um (#488). Die Datenschutzerklärung muss Einladungen und den eigenen Realm beschreiben, bevor das Einlösen eingeschaltet wird (#490). Eine Einlösung zählt auch bei einer Adresse mit Tippfehler; bei einem persönlichen Link legt der Admin dann eine neue Einladung an. Ganz ausschließen lässt sich der Bezug nicht: Wer Keycloak-Admin ist oder das Access-Log sieht, kann bei einem persönlichen Link Zeitpunkte vergleichen (`docs/KEYCLOAK_REALM.md`, `docs/LOESCHKONZEPT.md`). Einrichtung und Reihenfolge beim Umstellen: `docs/KEYCLOAK_REALM.md`.
