# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities in Gut gesagt by e-mail to
**gutgesagt@netzbegruenung.de**, not in a public issue, pull request or chat.

<!-- ANNAHME (#430): Sicherheitsmeldungen gehen an die allgemeine Kontaktadresse, bis es eine
eigene Adresse gibt (#290 sieht eine vor). Kommt sie, nur hier eintragen: README.md,
CONTRIBUTING.md und ORGANISATION.gutgesagtMail (shared/organisation.ts) nennen die allgemeine
Adresse fuer Fragen und Fehler und bleiben. -->

Please include:

- what is affected (URL, endpoint or file),
- the steps to reproduce it,
- what an attacker could do with it.

We answer in German or English. We confirm receipt and tell you how we proceed. Please give
us a reasonable time to fix the problem before you publish anything about it.

## Scope

This policy covers the code in this repository and the instances it runs as:

- https://gutgesagt.netzbegruenung.de (production)
- https://gutgesagt-test.netzbegruenung.de (test)

Login (Keycloak) and the hosting infrastructure are run by the hosting provider. If a finding
concerns them rather than Gut gesagt, report it the same way; we forward it.
