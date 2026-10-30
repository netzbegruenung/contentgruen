# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities in Gut gesagt by e-mail to
**gutgesagt@netzbegruenung.de**, not in a public issue, pull request or chat.

<!-- ANNAHME (#430): Sicherheitsluecken gehen an die allgemeine Kontaktadresse, bis es eine
eigene Adresse gibt (#290 sieht eine vor). Kommt sie, nur hier eintragen: README.md,
CONTRIBUTING.md und ORGANISATION.gutgesagtMail (shared/organisation.ts) nennen die allgemeine
Adresse fuer Fragen und Fehler und bleiben. -->

Please include:

- what is affected (URL, endpoint or file),
- the steps to reproduce it,
- what an attacker could do with it.

We answer in German or English. We confirm receipt and tell you how we proceed. Please give
us a reasonable time to fix the problem before you publish anything about it.

<!-- ANNAHME (#430): Antwort auf Deutsch oder Englisch und Eingangsbestaetigung sind zugesagt,
aber noch nicht bestaetigt; faellt die Zusage weg, diesen Absatz kuerzen. -->

## Scope

This policy covers the code in this repository and the instances it runs as:

- https://gutgesagt.netzbegruenung.de (production)
- https://gutgesagt-test.netzbegruenung.de (test)

Login (Keycloak) and the hosting infrastructure are run by [verdigado](https://verdigado.com/).
A finding that concerns them rather than Gut gesagt goes to verdigado directly.

<!-- ANNAHME (#430): verdigado will Hinweise zu Login und Hosting selbst bekommen (deshalb kein
zentrales security.txt). Nennt verdigado eine eigene Adresse dafuer, hier eintragen. -->
