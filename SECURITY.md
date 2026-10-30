# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities in Gut gesagt by e-mail to
**gutgesagt@netzbegruenung.de**, not in a public issue, pull request or chat.

<!-- Entschieden 30.10.2026 (#430): Sicherheitsluecken gehen an dieselbe Adresse wie Fragen und
Fehler. Aendert sie sich, auch security.txt (Contact), README.md, CONTRIBUTING.md und
ORGANISATION.gutgesagtMail (shared/organisation.ts) nachziehen. -->

Please include:

- what is affected (URL, endpoint or file),
- the steps to reproduce it,
- what an attacker could do with it.

Please give us a reasonable time to fix the problem before you publish anything about it.

## Scope

This policy covers the code in this repository and the instances it runs as:

- https://gutgesagt.netzbegruenung.de (production)
- https://gutgesagt-test.netzbegruenung.de (test)

Login (Keycloak) and the hosting infrastructure are run by [verdigado](https://verdigado.com/).
A finding that concerns them rather than Gut gesagt goes to verdigado directly.

<!-- Entschieden 30.10.2026 (#430): Hinweise zu Login und Hosting gehen direkt an verdigado. -->

## security.txt

The app publishes [`/.well-known/security.txt`](https://gutgesagt.netzbegruenung.de/.well-known/security.txt)
(RFC 9116) with the same address. The file lives in
`mvp/frontend/gutgesagt-frontend/public/.well-known/security.txt`; the frontend nginx serves it
(`nginx.conf`, `nginx.docker.conf`).

### Renewing security.txt

`Expires` may be at most one year ahead. `scripts/tests/test_security_txt.py` fails 30 days
before it runs out, so `scripts/check.sh` and CI turn red in time. To renew:

1. Set `Expires` to a date no more than a year from now, in UTC, e.g. `2028-10-29T23:00:00.000Z`.
2. Check that `Contact` and `Policy` are still right.
3. Open a pull request; the file goes live with the next frontend image that is deployed.
