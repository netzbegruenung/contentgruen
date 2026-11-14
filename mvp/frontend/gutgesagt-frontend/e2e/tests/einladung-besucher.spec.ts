import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Login und Einladung als Besucherin (Persona-Test BDK), ganz ohne Stack: Jede Anfrage an
 * /api beantwortet der Test selbst, also auch gegen `ng serve` ohne Backend
 * (E2E_BASE_URL). Legt nichts an.
 *
 * 1. Von der Login-Seite ohne Aufklappen zu „Einladung einlösen“, Link einfügen, Konto anlegen.
 * 2. Daumen ohne Anmeldung, „Anmelden“ in der Snackbar: Danach zurück auf dieselbe Seite, mit
 *    dem Satz, dass Abstimmen jetzt geht; die Stimme gibt die App nicht von selbst ab.
 */
const BEITRAG = 'e2e-beitrag';

interface Stand {
  angemeldet: boolean;
  stimmen: number;
  einloesen: Array<{ code: string; email: string }>;
}

async function ohneStack(page: Page): Promise<Stand> {
  const stand: Stand = { angemeldet: false, stimmen: 0, einloesen: [] };
  await page.route('**/api/**', (anfrage) => {
    const url = new URL(anfrage.request().url());
    const methode = anfrage.request().method();
    const pfad = url.pathname;
    if (pfad === '/api/user-info') {
      return stand.angemeldet
        ? anfrage.fulfill({ json: { isAuthenticated: true, userId: 'e2e-konto', userName: 'Testkonto', claims: {} } })
        : anfrage.fulfill({ status: 401, json: {} });
    }
    if (pfad === '/api/check-session') {
      // PublicGuard: ohne Sitzung setzt er die Person auf "nicht angemeldet"
      return anfrage.fulfill(stand.angemeldet ? { json: {} } : { status: 401, json: {} });
    }
    if (pfad === '/api/auth/modes') {
      return anfrage.fulfill({ json: { keycloakEnabled: false, managedAuthEnabled: true } });
    }
    if (pfad === '/api/auth/login/managed') {
      stand.angemeldet = true;
      return anfrage.fulfill({ json: { userId: 'e2e-konto', userName: 'Testkonto' } });
    }
    if (pfad === '/api/v1/art9-einwilligung') {
      return anfrage.fulfill({
        json: {
          eingewilligt: true,
          wortlaut: '2026-11-05',
          eingewilligt_am: '2026-11-05T00:00:00Z',
          widerrufen_am: null,
          aktueller_wortlaut: { kennung: '2026-11-05', text: 'Ich willige ein (Testwortlaut).' },
        },
      });
    }
    if (pfad.startsWith('/api/v1/content/beitrag/')) {
      return anfrage.fulfill({
        json: {
          id: BEITRAG,
          content_type: 'commentary',
          title: 'Eine kaputte Heizung darf repariert werden',
          text: 'Niemand muss eine funktionierende Heizung herausreißen.',
          references: [],
          created_at: '2025-09-01T00:00:00Z',
        },
      });
    }
    if (pfad.startsWith('/api/v1/voting/') && methode !== 'GET') {
      stand.stimmen += 1;
      return anfrage.fulfill({ json: {} });
    }
    if (pfad === '/api/v1/einladungen/pruefen') {
      return anfrage.fulfill({ json: { einloesbar: anfrage.request().postDataJSON().code === 'E2eCode_123' } });
    }
    if (pfad === '/api/v1/einladungen/einloesen') {
      stand.einloesen.push(anfrage.request().postDataJSON());
      return anfrage.fulfill({ status: 202, json: { success: true } });
    }
    return anfrage.fulfill({ status: 404, json: {} });
  });
  return stand;
}

test('Login-Seite: Einladung ohne Aufklappen finden, Link einfügen, Konto anlegen', async ({ page, bild }) => {
  const stand = await ohneStack(page);
  await page.goto('/login');

  const weg = page.locator('.einladung-weg');
  await expect(weg).toContainText('Noch kein Konto, aber eine Einladung bekommen?');
  await expect(weg).toBeInViewport();
  await bild('login-einladung-weg');
  // Auch unter „So bekommst du ein Konto“
  await page.getByText('So bekommst du ein Konto').click();
  await expect(page.locator('.registration-options')).toContainText('Einladung');
  await bild('login-so-bekommst-du-ein-konto', true);

  await weg.getByRole('link', { name: 'Einladung einlösen' }).click();
  await expect(page).toHaveURL(/\/einladung$/);
  const feld = page.getByLabel('Link der Einladung');
  await expect(feld).toBeVisible();
  await expect(page.locator('app-einladung')).not.toContainText('gilt nicht');
  await bild('einladung-link-eingeben');

  // Kein Link einer Einladung: Hinweis, keine Anfrage
  await feld.fill('Hallo Welt?');
  await page.getByRole('button', { name: 'Weiter' }).click();
  await expect(page.getByRole('alert')).toContainText('kein Link einer Einladung');

  await feld.fill(`  https://gutgesagt.example/einladung#E2eCode_123 `);
  await page.getByRole('button', { name: 'Weiter' }).click();
  const mail = page.getByLabel('Mail-Adresse');
  await expect(mail).toBeVisible();
  await mail.fill('neu@example.org');
  await page.getByRole('button', { name: 'Konto anlegen' }).click();
  await expect(page.locator('app-einladung')).toContainText('Schau in dein Postfach');
  expect(stand.einloesen).toEqual([{ code: 'E2eCode_123', email: 'neu@example.org' }]);

  // Leere Seite ohne horizontales Scrollen bei 360 px
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
});

test('Anmelden aus der Daumen-Snackbar führt zurück auf die Seite, ohne von selbst abzustimmen', async ({ page, bild }) => {
  const stand = await ohneStack(page);
  await page.goto(`/beitrag/${BEITRAG}?quelle=e2e`);
  const karte = page.locator('app-beitragskarte').first();
  await expect(karte).toBeVisible();

  await karte.getByRole('button', { name: /Hilfreich/ }).first().click();
  const snackbar = page.locator('mat-snack-bar-container');
  await expect(snackbar).toContainText('Bitte melde dich an, um abzustimmen');
  await snackbar.getByRole('button', { name: 'Anmelden' }).click();

  await expect(page).toHaveURL(/\/login\?returnUrl=/);
  const ziel = new URL(page.url()).searchParams.get('returnUrl');
  expect(ziel).toBe(`/beitrag/${BEITRAG}?quelle=e2e&anlass=abstimmen`);
  await bild('login-mit-rueckkehrziel');

  await page.locator('.gutgesagt-button').click();
  await page.locator('input[formControlName="email"]').fill('test@example.org');
  await page.locator('input[formControlName="password"]').fill('geheim');
  await page.locator('button[type="submit"]').click();

  // Zurück auf derselben Seite samt Query, der Anlass ist aus der Adresse verschwunden
  await expect(page).toHaveURL(new RegExp(`/beitrag/${BEITRAG}\\?quelle=e2e$`));
  // Ersetzt „Anmeldung erfolgreich!“ der Direktanmeldung
  await expect(page.locator('mat-snack-bar-container', { hasText: 'Jetzt kannst du abstimmen' })).toBeVisible();
  await expect(page.locator('mat-snack-bar-container', { hasText: 'Anmeldung erfolgreich' })).toHaveCount(0);
  await bild('zurueck-jetzt-abstimmen');
  expect(stand.stimmen).toBe(0);
});
