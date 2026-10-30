# Stände der Nutzungsbedingungen

Die Nutzungsbedingungen (`nutzungsbedingungen.component.html`) tragen unten eine Stand-Zeile mit
Tagesdatum. Dieses Datum ist der **Stand der Nutzungsbedingungen** (`GLOSSARY.md`): Es benennt
genau einen Text. Geänderte Bedingungen gelten für eine Person erst, wenn sie ihnen zugestimmt hat
(NB §10, #466); die Zustimmung holt die Keycloak-Pflichtaktion „Terms and Conditions“ beim
Anmelden ein (#429).

Keycloak speichert dabei nur den Zeitpunkt der Zustimmung, nicht den Text. Welchem Stand jemand
zugestimmt hat, ergibt sich deshalb aus diesem Verzeichnis: der Stand, der zu diesem Zeitpunkt
live war. Den Text eines Stands liefert der Release-Tag, mit dem er live ging
(`git show <tag>:mvp/frontend/gutgesagt-frontend/src/app/nutzungsbedingungen/nutzungsbedingungen.component.html`).

## Einen neuen Stand einführen

Jede Änderung am Text der Nutzungsbedingungen ist ein neuer Stand, auch eine kleine. Eine
**reine Korrektur**, die Rechte und Pflichten nicht ändert (Schreibfehler, Verweise,
Formulierungen ohne neuen Inhalt), gilt nach §10 ohne erneute Zustimmung; jede andere Änderung
ist **wesentlich** und gilt erst nach Zustimmung (Entscheidung Maintainer, 30.10.2026). Im
Zweifel wesentlich. Ein Zeitpunkt der Zustimmung gehört zum letzten wesentlichen Stand, der zu
diesem Zeitpunkt live war.

1. Stand-Zeile auf das Tagesdatum der Änderung setzen, z. B. „Stand: 1. März 2027“. Ein Datum
   nie für einen anderen Text wiederverwenden; ändert sich der Text am selben Tag noch einmal
   nach einem Release, den nächsten Tag nehmen.
2. Hier einen Ordner für den Stand anlegen, benannt nach seinem Datum (`2027-03-01/`), darin
   `stand.md` wie beim vorigen Stand, mit „Zustimmung“ ja (wesentlich) oder nein (reine
   Korrektur); „Release“ und „gültig“ bleiben offen. Jede Änderung ist eine eigene Datei im
   Ordner des Stands, benannt nach dem Ticket (`512.md`), mit Paragraf und Änderung in einem
   Absatz. So kollidieren zwei PRs nicht, die am selben Stand ändern (#500). Die alten Ordner
   bleiben. `scripts/tests/test_rechtstexte_uebersicht.py` prüft, dass der Stand der Seite
   hier steht und dass Ordner und Stand zusammenpassen.
3. Nach dem Produktiv-Deploy (Maintainer): Release-Tag und Datum in `stand.md` eintragen, beim
   vorigen Stand das „bis“-Datum. Bei einer reinen Korrektur ist der Ablauf hier zu Ende.

Bei einem wesentlichen Stand gleich nach dem Deploy (Maintainer):

4. Den Text, den Keycloak bei der Pflichtaktion zeigt, auf den neuen Stand bringen; ohne das
   stimmen die Personen dem alten Stand-Datum zu. Diesen Text (`termsText`) liefert die
   Realm-Vorlage aus #429 mit Link und Stand-Datum, ein eigenes Theme gibt es nicht; ändern in
   Vorlage und Realm wie in `docs/KEYCLOAK_REALM.md` beschrieben.
5. Die Pflichtaktion „Terms and Conditions“ für alle Konten im Realm von Gut gesagt erneut
   auslösen (siehe unten). Der Realm gehört nur zu Gut gesagt (#429); in einem geteilten Realm
   träfe das auch Konten, die Gut gesagt nie nutzen.
6. Alle abmelden, damit niemand mit einer laufenden Sitzung unter dem neuen Stand weiterarbeitet,
   ohne zugestimmt zu haben (§10; Entscheidung Maintainer, 30.10.2026). Dazu gehören zwei Dinge:
   - In Keycloak: Admin-Konsole → Realm von Gut gesagt → Sessions → „Sign out all active
     sessions“. Das beendet die Sitzungen bei Keycloak, sodass die nächste Anmeldung über die
     Pflichtaktion läuft.
   - Im BFF: Das Anmelde-Cookie lebt 14 Tage gleitend und wird nicht gegen Keycloak geprüft
     (`BFF/Program.cs`, Cookie-Lebensdauer; wie in `docs/LOESCHKONZEPT.md`, „Vorab: Sitzung
     beenden“). Das Abmelden in Keycloak allein beendet es deshalb nicht. Abgemeldet sind alle
     erst, wenn der DataProtection-Schlüsselring des BFF (`DATAPROTECTION_KEYS_PATH`, Standard
     `/keys`) geleert und das BFF neu gestartet ist: Danach lässt sich kein altes Cookie mehr
     entschlüsseln. Wer gerade mitten in einer Anmeldung ist, muss sie einmal neu beginnen.

Keycloak fragt bei der nächsten Anmeldung. Wer nicht zustimmt, kommt nicht hinein.

Das erneute Auslösen in Schritt 5 geht nicht über die Oberfläche der Admin-Konsole für alle auf
einmal, sondern über die Admin-Schnittstelle von Keycloak: für jedes Konto `requiredActions` um
den Alias der Pflichtaktion ergänzen, ohne andere offene Pflichtaktionen (etwa „E-Mail
bestätigen“) zu überschreiben. Den Alias liefert
`GET /admin/realms/<realm>/authentication/required-actions`. Die Pflichtaktion muss dort
aktiviert und für neue Konten als Standard gesetzt sein.

## Stände

Ein Ordner je Stand in diesem Verzeichnis, benannt nach seinem Datum. Als Tabelle, der neueste
zuerst: `python3 scripts/rechtstexte_uebersicht.py staende`. Hier keine Liste der Stände
pflegen: Sie wäre wieder die Stelle, an der jeder PR anhängt.

Frühere Stände hatten nur einen Monat in der Stand-Zeile und waren nie Gegenstand einer
Zustimmung beim Anmelden. Ein Monat benennt dort nicht genau einen Text: „Oktober 2026“ wurde
mehrfach geändert. Ihre Ordner nennen deshalb den Zeitraum im Repository (Commit und Datum), nicht,
wann ein Text live war; das Versprechen in §10, jeden Stand mit seinem Zeitraum aufzubewahren,
gilt ab dem Stand vom 30. Oktober 2026.
