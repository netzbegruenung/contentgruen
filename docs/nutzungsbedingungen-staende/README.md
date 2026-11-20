# Stände der Nutzungsbedingungen

Die Nutzungsbedingungen (`nutzungsbedingungen.component.html`) tragen unten eine Stand-Zeile mit
Tagesdatum. Dieses Datum ist der **Stand der Nutzungsbedingungen** (`GLOSSARY.md`): Es benennt
genau einen Text. Geänderte Bedingungen gelten für eine Person erst, wenn sie ihnen zugestimmt hat
(NB §10, #466). Seit dem Stand vom 20. November 2026 kommt die Zustimmung mit einem eigenen
Häkchen auf `/einwilligung`, bei der ersten Anmeldung und nach jedem wesentlichen Stand neu
(NB §2 und §10, #731); die App speichert sie mit dem Stand (Schritt 3). Bis dahin kam sie über
den CC0-Hinweis beim Absenden (NB §2, #415, #521); der Hinweis verlinkt die Bedingungen weiter,
das Absenden gibt aber nur noch den Text nach §4 frei. Bis 0.9.8 fragte daneben die
Keycloak-Pflichtaktion „Terms and Conditions“ beim Anmelden (#429); sie wird mit 0.9.8
abgeschaltet, nachdem die Zeitpunkte archiviert sind (Entscheidung Maintainer, 20.11.2026;
Folgeschritte in #731). Damit entfallen die Schritte 5 und 6 unten
(`docs/rechtstexte-luecken/README.md`, Abschnitt 5).

Bei der Pflichtaktion speichert Keycloak nur den Zeitpunkt der Zustimmung, nicht den Text. Welchem Stand jemand
zugestimmt hat, ergibt sich deshalb aus diesem Verzeichnis: der Stand, der zu diesem Zeitpunkt
live war. Wer über den CC0-Hinweis zugestimmt hat (NB §2, #415), dem gehört der Stand, der beim
Absenden live war; den Zeitpunkt liefert der Beitrag, der Satz oder der Einwurf (Erstellungszeit),
die Kennung des Hinweises steht daneben (`docs/CC0_HINWEIS_WORTLAUTE.md`). Den Text eines Stands liefert der Release-Tag, mit dem er live ging
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
   Korrektur); „Release“ und „gültig“ bleiben offen. Jedes Ticket, das am Text ändert, legt
   im Ordner des Stands eine eigene Datei an, benannt nach dem Ticket (`512.md`), mit
   Paragraf und Änderung in einem Absatz (bei mehreren Änderungen je ein Satz). So
   kollidieren zwei PRs nicht, die am selben Stand ändern (#500). Die alten Ordner bleiben.
   `scripts/tests/test_nutzungsbedingungen_staende.py` prüft, dass der Stand der Seite hier
   steht und dass Ordner und Stand zusammenpassen.
3. In der App (`mvp/backend/semantic-search-service/app/domain/nutzungsbedingungen.py`): den
   Stand in `STAENDE` eintragen und `AKTUELLER_STAND` setzen; bei einer reinen Korrektur den
   Stand zu `GELTENDE_STAENDE` hinzufügen (niemand wird gefragt), bei einem wesentlichen
   `GELTENDE_STAENDE` nur mit ihm (alle stimmen beim nächsten Besuch auf `/einwilligung` neu zu;
   bis dahin sind Beitragen und Bewerten gesperrt, Lesen nicht, `docs/ART9_EINWILLIGUNG.md`).
4. Nach dem Produktiv-Deploy (Maintainer): Release-Tag und Datum in `stand.md` eintragen, beim
   vorigen Stand das „bis“-Datum. Bei einer reinen Korrektur ist der Ablauf hier zu Ende.

Bei einem wesentlichen Stand gleich nach dem Deploy (Maintainer), solange die Pflichtaktion
läuft:

5. Den Text, den Keycloak bei der Pflichtaktion zeigt, auf den neuen Stand bringen; ohne das
   stimmen die Personen dem alten Stand-Datum zu. Diesen Text (`termsText`) liefert die
   Realm-Vorlage aus #429 mit Link und Stand-Datum, ein eigenes Theme gibt es nicht; ändern in
   Vorlage und Realm wie in `docs/KEYCLOAK_REALM.md` beschrieben.
6. Die Pflichtaktion „Terms and Conditions“ für alle Konten im Realm von Gut gesagt erneut
   auslösen (siehe unten). Der Realm gehört nur zu Gut gesagt (#429); in einem geteilten Realm
   träfe das auch Konten, die Gut gesagt nie nutzen.

Bis 0.9.8 fragte Keycloak bei der nächsten Anmeldung; wer nicht zustimmte, kam nicht hinein. Seit dem
Stand vom 20. November 2026 kommt die Zustimmung nach §2 und §10 nur über das Häkchen der App
(Schritt 3); das Absenden unter dem CC0-Hinweis gibt nur noch den Text nach §4 frei. Wer nicht
zustimmt, kann mit dem Konto nichts einstellen und nichts bewerten, Lesen bleibt (§10). Die
Pflichtaktion wird mit 0.9.8 abgeschaltet; Schritt 6 entfällt für den Stand vom 20. November 2026,
weil die App selbst neu fragt (Entscheidung Maintainer, 20.11.2026).

Das erneute Auslösen in Schritt 6 geht nicht über die Oberfläche der Admin-Konsole für alle auf
einmal, sondern über die Admin-Schnittstelle von Keycloak: für jedes Konto `requiredActions` um
den Alias der Pflichtaktion ergänzen, ohne andere offene Pflichtaktionen (etwa „E-Mail
bestätigen“) zu überschreiben. Den Alias liefert
`GET /admin/realms/<realm>/authentication/required-actions`. Die Pflichtaktion muss dort
aktiviert und für neue Konten als Standard gesetzt sein.

## Stände

Ein Ordner je Stand in diesem Verzeichnis, benannt nach seinem Datum. Als Tabelle, der neueste
zuerst: im Wiki des Repositorys auf Forgejo, Seite „Rechtstexte Übersicht“ (#503), lokal
`python3 scripts/rechtstexte_uebersicht.py staende`. Hier keine Liste der Stände
pflegen: Sie wäre wieder die Stelle, an der jeder PR anhängt. Bis #500 stand das Verzeichnis
in einer Datei, `docs/NUTZUNGSBEDINGUNGEN_STAENDE.md`; Verweise in `docs/archiv/` nennen noch
diesen Namen.

Frühere Stände hatten nur einen Monat in der Stand-Zeile und waren nie Gegenstand einer
Zustimmung beim Anmelden. Ein Monat benennt dort nicht genau einen Text: „Oktober 2026“ wurde
mehrfach geändert. Ihre Ordner nennen deshalb den Zeitraum im Repository (Commit und Datum), nicht,
wann ein Text live war; das Versprechen in §10, jeden Stand mit seinem Zeitraum aufzubewahren,
gilt ab dem Stand vom 30. Oktober 2026. Ihre Änderungen sind nicht nach einem Ticket benannt:
`2026-09/neufassung.md` hatte keins, `2026-10/222.md` deckt auch #448 ab.
