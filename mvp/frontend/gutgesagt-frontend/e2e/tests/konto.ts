/**
 * Testkonto und Ablage der Sitzung. Ohne Playwright-Import, damit auch
 * playwright.config.ts es laden kann.
 */

/** Testkonto aus mvp/config/managed-users.example.json, ueberschreibbar per Umgebung. */
export const KONTO = {
  email: process.env['E2E_EMAIL'] ?? 'test.user@example.com',
  passwort: process.env['E2E_PASSWORT'] ?? 'Liebe>Hass!',
};

/** Hier legt anmelden.setup.ts die Sitzung ab; die angemeldeten Projekte laden sie. */
export const SITZUNG = '.auth/sitzung.json';
