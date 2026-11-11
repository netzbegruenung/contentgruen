# Fragen an die Datenschutzbeauftragte

Nur die Punkte mit echtem Risiko; alles Übrige zu den Rechtstexten entscheiden wir selbst.
Stand: 2. November 2026. Hintergrund in `docs/rechtstexte-luecken/` und den genannten Tickets.

## 1. Art. 9 DSGVO bei Punkten und Ranglisten (#374)

**Frage:** Braucht eine Rangliste, aus der hervorgeht, wer wie viel zu politischen Argumenten
beiträgt, eine ausdrückliche Einwilligung (Art. 9 Abs. 2 lit. a)? Ranglisten sind für alle
Mitwirkenden gedacht, nicht nur für Mitglieder des Vereins. Trägt lit. d für einen Teil von
ihnen, und ist die Netzbegrünung überhaupt eine Organisation im Sinne von lit. d?

**Empfehlung:** Ranglisten nur mit ausdrücklicher Einwilligung, die man jederzeit zurückziehen
kann, und die Folgenabschätzung dazu vor dem Start (Entwurf in #374).

**Ergebnis:** …

## 2. Tagespseudonym der Besucher und § 25 TDDDG (#495, P1)

**Sachverhalt:** Der Server bildet aus IP-Adresse (IPv6: /64) und Tag mit einem täglich neuen
Schlüssel ein Pseudonym. Schlüssel und Adresse liegen dafür nur im Arbeitsspeicher; im Browser
wird für das Pseudonym nichts gespeichert oder ausgelesen. Den User-Agent nimmt der Server seit
der Vorprüfung zu #495 nicht mehr auf (Entscheidung Maintainer, 11.11.2026). Das Pseudonym selbst
wird gespeichert: an Suchereignissen nur bis zum Ende ihres Tages (danach bleiben Tageszähler ohne
Pseudonym; vorher 90 Tage) und an anonymen Meldungen, bis sie abgeschlossen sind. Unabhängig
davon halten die Zugriffsprotokolle des vorgelagerten Webservers Adresse, User-Agent und Uhrzeit
jeder Anfrage außer der Suche fest (Datenschutzerklärung, „Protokolldateien“).

**Frage:** Darf der Server das Pseudonym ohne Einwilligung bilden? Strittig war vor allem, ob
schon das Auswerten des User-Agents unter § 25 TDDDG fällt (EDSA-Leitlinien 2/2023 Rn. 43, 54–55
dafür, DSK-OH Digitale Dienste Rn. 23–25 dagegen); für das Pseudonym entfällt das. Für die
Geräteklasse der Nutzungsereignisse liest der Server den User-Agent weiter und verdichtet ihn sofort
zu einer von vier Klassen (Datenschutzerklärung, „Verwendung von Beiträgen“); das ist nicht Teil
des Pseudonyms. Zu klären bleibt, ob das Bilden des Pseudonyms aus der IP-Adresse allein § 25
TDDDG berührt.

**Empfehlung:** Ja: § 25 TDDDG ist nach der DSK-Auslegung nicht berührt, und Art. 6 Abs. 1
lit. f trägt, weil sich Pseudonyme verschiedener Tage auch mit Datenbank und Konfiguration nicht
verknüpfen lassen.

**Ergebnis:** …

## 3. AV-Vertrag mit verdigado und Hetzner nach dem Umzug (#506, #206)

**Frage:** verdigado hat am 04.09.2026 bestätigt, dass AV-Verträge vorliegen (Lückenliste
D-M3, D-N7). Deckt der Vertrag zwischen dem Verein und verdigado auch Gut gesagt ab? Und bleibt
Hetzner Unterauftragsverarbeiterin, wenn sie nach dem Umzug nur Rack, Strom und Netz stellt?

**Empfehlung:** Vertrag auf Gut gesagt prüfen und sonst ergänzen; Hetzner erst nach dem Umzug
und nur ohne Zugriff auf Daten aus der Datenschutzerklärung streichen.

**Ergebnis:** …
