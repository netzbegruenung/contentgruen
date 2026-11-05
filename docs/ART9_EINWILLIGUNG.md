# Art.-9-Einwilligung

Mitwirkung bei Gut gesagt kann auf eine politische Meinung schließen lassen (Art. 9 DSGVO,
Lückenliste D-N15). Rechtsgrundlage ist eine ausdrückliche Einwilligung (Art. 9 Abs. 2 lit. a),
die die App selbst einholt, nicht Keycloak (Entscheidung Maintainer, 05.11.2026,
#489). Begriff: `GLOSSARY.md`, „Art.-9-Einwilligung“.

## Ablauf

- **Fragen:** Nach dem Anmelden fragt die App einmal je Person und App-Start nach dem Stand
  (`GET /api/v1/art9-einwilligung`) und führt ohne Einwilligung auf `/einwilligung`. Das gilt
  für jede Kontoart (Netzbegrünung-Login, Konto aus einer Einladung, Beta-Zugang). Dort steht
  der Wortlaut an einem eigenen Häkchen, getrennt von den Nutzungsbedingungen und nicht
  angehakt. „Ohne Einwilligung weiter“ führt zurück; die Person kann suchen und lesen.
- **Speichern:** Tabelle `art9_einwilligungen`, je Einwilligung eine Zeile mit Kennung der
  Person, Zeitpunkt und Kennung des gezeigten Wortlauts. Es gilt die jüngste Zeile.
- **Sperren:** Ohne geltende Einwilligung antworten die Endpunkte, die mit Personenbezug etwas
  speichern, aus dem sich auf die politische Meinung schließen lässt, mit 403
  (`art9_einwilligung_fehlt`); die App zeigt dann einen Hinweis mit Knopf, der auf
  `/einwilligung` und danach zurück führt, und bleibt sonst auf der Seite, damit kein Text im
  Formular verloren geht.
  Gesperrt: Beiträge anlegen und ändern, Herkunft anlegen, Einwurf und Satz, einen Einwurf
  ausformulieren, Stimmen abgeben. Offen bleiben Lesen, Suchen, Löschen, einen Einwurf
  verwerfen, Melden, Feedback, Gegenlesen, Sprachhinweis, Kürzungsvorschlag und Widerspruch
  gegen eine Sperre. Die Liste prüft `tests/unit/api/test_art9_einwilligung_api.py`
  (`GESPERRT`, `OFFEN`): Ein neuer schreibender Endpunkt fällt dort auf, bis er in einer der
  beiden steht; gesperrte tragen `require_art9_einwilligung` (`dependencies.py`).
- **Kopieren:** bleibt offen und zählt am Zähler der Karte (Kopieren ist Lesen). Ohne geltende
  Einwilligung entsteht dabei aber kein Prüfwert und kein Paar-Prüfwert: keine entdoppelte
  Nutzung, also keine Wirkung-Punkte für die Autorin und kein Eintrag in „Diese Woche oft
  genutzt“, und keine Muster-Hinweise. Einen Paar-Prüfwert gibt es auch nicht, wenn die
  Autorin des Beitrags nicht eingewilligt hat (#559, `track_content_usage` in
  `api/v1/usage.py`, Tests `TestArt9Einwilligung` in
  `tests/unit/api/test_usage_eigene_kopie.py`). Gefragt wird je Kopie; ist die Einwilligung
  nicht lesbar, gilt sie als nicht erteilt und die Kopie zählt trotzdem. Paar-Prüfwerte und
  Hinweise von vor einem Widerruf gehen mit ihren Fristen (`docs/LOESCHKONZEPT.md`).
- **Punkte:** Ein Konto ohne geltende Einwilligung (nie erteilt oder widerrufen) hat keine
  Punkte; `GET /api/v1/usage/users/me/punkte` liefert dann 0 in jeder Stufe, wie bei einem
  Startkonto (#559, F559-1, `PunkteService.punkte`). Gefragt wird je Abruf.
- **Widerrufen:** jederzeit unter `/einwilligung` (Profilmenü „Einwilligung“). Die Zeile bekommt
  den Zeitpunkt des Widerrufs und bleibt stehen, als Nachweis, dass die Verarbeitung bis dahin
  auf der Einwilligung beruhte (Art. 7 Abs. 1); danach ist wieder gesperrt. Schon Gespeichertes
  bleibt, bis die Person es löscht oder ihr Konto löschen lässt (Löschkonzept). Eine neue
  Einwilligung ist eine neue Zeile; die früheren bleiben. Jede Prüfung fragt die Datenbank,
  damit ein Widerruf und das Löschkommando sofort wirken.
- **Startkonten und Import:** Auch ein Startkonto willigt einmal in der App ein, bevor es
  schreibt oder `mvp/scripts/manual/einwuerfe_importieren.py` unter ihm läuft (`mvp/SCRIPTS.md`).
  Verwerfen eines Einwurfs bleibt ohne Einwilligung offen, wie Löschen.
- **Löschen und Umstellen:** Die Zeile geht mit dem Konto (`docs/LOESCHKONZEPT.md`, Schritt 2)
  und zieht beim Umstellen der Kennungen mit (`services/wartung/kennungen_umstellen.py`).

## Wortlaut ändern

Der Wortlaut steht an einer Stelle: `WORTLAUTE` in
`mvp/backend/semantic-search-service/app/domain/art9_einwilligung.py`. Das Frontend zeigt,
was das Backend liefert, und hat keinen eigenen Text. Die Kennung eines Wortlauts ist sein
Stand-Datum; ein zweiter Wortlaut vom selben Tag bekommt ein Suffix (`-b`, `-c` …).

1. Neuen Eintrag in `WORTLAUTE` mit dem Tagesdatum als Kennung anlegen; den alten stehen lassen,
   sonst ist eine gespeicherte Kennung keinem Text mehr zuzuordnen. Ein Datum nie für einen
   anderen Text wiederverwenden; gibt es das Tagesdatum schon, mit Suffix (`2026-11-05-b`).
2. `AKTUELLER_WORTLAUT` auf die neue Kennung setzen.
3. Unten in der Tabelle eine Zeile ergänzen, beim vorigen Wortlaut das „bis“-Datum nach dem
   Produktiv-Deploy.

Eine Einwilligung zu einem älteren Wortlaut gilt weiter. Ob ein geänderter Wortlaut eine neue
Einwilligung verlangt, ist beim Ändern zu entscheiden; heute fragt die App nicht erneut.
Die Prüfung der Einwilligung (`Art9EinwilligungService.eingewilligt`) unterscheidet heute nicht
nach Wortlaut: Eine Einwilligung zu `2026-11-05` zählt also auch für Punkte, obwohl erst
`2026-11-05-b` sie nennt. Das ist vertretbar, weil `2026-11-05` nie produktiv war (#559). Nennt
ein künftiger Wortlaut neue Zwecke, muss die Prüfung für diese Zwecke die Kennung
berücksichtigen oder die App neu fragen.

## Wortlaute

| Kennung | Stand | gültig |
|---------|-------|--------|
| `2026-11-05` | vorläufig, Prüfung mit #296 (Lückenliste P11) | nie produktiv: von `2026-11-05-b` abgelöst, bevor #489 in einem Release war |
| `2026-11-05-b` | vorläufig, Prüfung mit #296; nennt zusätzlich Punkte, Quests und Meilenstein-Abzeichen und die Muster-Hinweise (#559, Zwecke aus `docs/DSFA_PUNKTE.md` Abschnitt 4) | seit dem Produktiv-Deploy von #489 und #559 (Datum nach dem Ausrollen eintragen) |
