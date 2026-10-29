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

Jede Änderung am Text der Nutzungsbedingungen ist ein neuer Stand, auch eine kleine.

1. Stand-Zeile auf das Tagesdatum der Änderung setzen, z. B. „Stand: 1. März 2027“. Ein Datum
   nie für einen anderen Text wiederverwenden; ändert sich der Text am selben Tag noch einmal
   nach einem Release, den nächsten Tag nehmen.
2. Hier eine Zeile ergänzen, „Release“ und „gültig“ bleiben offen. Die alten Zeilen bleiben.
   `scripts/tests/test_nutzungsbedingungen_staende.py` prüft, dass der Stand der Seite hier
   steht.
3. Nach dem Produktiv-Deploy (Maintainer): Release-Tag und Datum eintragen, beim vorigen Stand
   das „bis“-Datum.
4. Gleich danach (Maintainer): die Pflichtaktion „Terms and Conditions“ für alle Konten im Realm
   erneut auslösen. Keycloak zeigt den neuen Stand dann bei der nächsten Anmeldung. Wer nicht
   zustimmt, kommt nicht hinein; wer noch angemeldet ist, bleibt bis zum Ablauf der Sitzung
   beim alten Stand, so wie es §10 sagt.

Das erneute Auslösen geht nicht über die Oberfläche der Admin-Konsole für alle auf einmal,
sondern über die Admin-Schnittstelle von Keycloak: für jedes Konto `requiredActions` um den
Alias der Pflichtaktion ergänzen, ohne andere offene Pflichtaktionen (etwa „E-Mail bestätigen“)
zu überschreiben. Den Alias liefert `GET /admin/realms/<realm>/authentication/required-actions`.
Die Pflichtaktion muss dort aktiviert und für neue Konten als Standard gesetzt sein.

## Stände

| Stand | Was sich geändert hat | Release | gültig |
|-------|-----------------------|---------|--------|
| 30. Oktober 2026 | §10: Änderungen gelten erst nach ausdrücklicher Zustimmung beim Anmelden statt durch Schweigen (#466). §4: Ersatzlizenz, wo der CC0-Verzicht nicht wirkt (#466) | offen | offen; frühestens nach der Freigabe in #296 und mit der Pflichtaktion aus #429 |

Frühere Stände hatten nur einen Monat in der Stand-Zeile und waren nie Gegenstand einer
Zustimmung beim Anmelden; sie stehen hier, damit die Reihe vollständig ist.

| Stand (alt) | Was sich geändert hat | bis |
|-------------|-----------------------|-----|
| Oktober 2026 | Glossarbegriffe, Moderation nach dem Funktionsumfang, Sperrgrund und Widerspruch (#222, #448; ab bb0235b5, mehrfach geändert bis 6b7f9cdf) | 30. Oktober 2026 |
| September 2026 | Neufassung (20c1b06b) | bb0235b5 |
