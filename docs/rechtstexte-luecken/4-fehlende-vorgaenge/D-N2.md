# D-N2

- **Vorgang:** **Managed Login (Gut-gesagt-Account)**
- **Fundstelle im Code:** `BFF/Controllers/AuthController.cs:45–98`, `BFF/Models/ManagedUser.cs`
- **Was in den Text muss:** E-Mail + Passwort-Hash, manuell durch Admins angelegt, keine Selbstregistrierung; Rate-Limiting bei Fehlversuchen (`ManagedUserService.cs:82–113`)
- **Eintrag / Entscheidung:** ✓ Abschnitt „Zugang, den wir selbst anlegen": E-Mail, Anzeigename, interne Kennung, Passwort-Prüfsumme; keine Selbstregistrierung; Sperre nach Fehlversuchen (15 Minuten). **Speicherdauer nach Account-Ende: keine automatische Löschung**, im Text so benannt
