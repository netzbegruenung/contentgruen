import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';
import { KONTO } from './konto';

/**
 * Rundgang und Zurück im Browser: Zurück beendet den Rundgang, statt den Schritt auf der
 * vorigen Seite stehen zu lassen. Läuft als Besucher (Projekt „besucher“) und legt keine
 * Inhalte an; ohne Konto ist Selbst beitragen die Bildergeschichte auf /mit-konto, der Test
 * zum Menü meldet sich am Ende über die Direktanmeldung an.
 */
test('Besucher: Zurück im Browser beendet den Rundgang, er lässt sich neu starten', async ({ page }) => {
  await page.goto('/search');
  await page.getByRole('button', { name: 'Rundgang (1 Min.)' }).click();
  await expect(page.locator('.blase h3')).toHaveText('Aussage eingeben');
  await page.locator('.blase .weiter').click();
  await expect(page.locator('.blase h3')).toHaveText('Passende Treffer', { timeout: 45_000 });
  await expect(page).toHaveURL(/\/result\?/);

  await page.goBack();
  await expect(page).toHaveURL(/\/search$/);
  // Vorher blieb „Passende Treffer“ stehen, mit Lichtkegel auf einer Karte unter
  // „Neueste Inhalte“, und die Sperre deckte die Startseite ab.
  await expect(page.locator('app-rundgang .blase')).toHaveCount(0);
  await expect(page.locator('app-rundgang .sperre')).toHaveCount(0);
  await expect(page.locator('app-rundgang .kegel')).toHaveCount(0);
  // Die Startseite ist wieder bedienbar, das Band kommt in diesem Besuch nicht zurück
  const feld = page.locator('app-search.start-suche [name="searchQuery"]');
  await feld.fill('Windräder töten Vögel');
  await expect(feld).toHaveValue('Windräder töten Vögel');
  await expect(page.getByRole('button', { name: 'Rundgang (1 Min.)' })).toHaveCount(0);

  // Über das Menü neu starten: wieder ab Schritt 1
  await page.locator('.mobile-header .menu-button').click();
  await page.locator('.mobile-menu-rundgang').click();
  await expect(page.locator('.blase h3')).toHaveText('Aussage eingeben');
});

/** Kontrast nach WCAG aus zwei CSS-Farben (rgb/rgba, Alpha über dem Hintergrund verrechnet). */
function kontrast(vorne: string, hinten: string): number {
  const teile = (f: string) => f.match(/[\d.]+/g)!.map(Number);
  const [hr, hg, hb] = teile(hinten);
  const [vr, vg, vb, va = 1] = teile(vorne);
  const mischen = (v: number, h: number) => v * va + h * (1 - va);
  const leuchte = (r: number, g: number, b: number) =>
    [r, g, b]
      .map((k) => k / 255)
      .map((k) => (k <= 0.03928 ? k / 12.92 : ((k + 0.055) / 1.055) ** 2.4))
      .reduce((s, k, i) => s + k * [0.2126, 0.7152, 0.0722][i], 0);
  const a = leuchte(mischen(vr, hr), mischen(vg, hg), mischen(vb, hb));
  const b = leuchte(hr, hg, hb);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

/** Schrift gegen den ersten deckenden Hintergrund darunter, hell und dunkel mindestens 4,5:1. */
async function kontrastPruefen(page: Page, selektoren: string[]): Promise<void> {
  for (const schema of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme: schema });
    for (const sel of selektoren) {
      const { farbe, grund } = await page.locator(sel).evaluate((el) => {
        let g = el as HTMLElement | null;
        while (g && /rgba\(0, 0, 0, 0\)|transparent/.test(getComputedStyle(g).backgroundColor)) g = g.parentElement;
        return { farbe: getComputedStyle(el).color, grund: getComputedStyle(g!).backgroundColor };
      });
      expect(kontrast(farbe, grund), `${schema} ${sel}: ${farbe} auf ${grund}`).toBeGreaterThanOrEqual(4.5);
    }
  }
  await page.emulateMedia({ colorScheme: 'light' });
}

// Ohne Konto ist Selbst beitragen die Bildergeschichte auf /mit-konto (17.11.), ohne Sperre
async function bildergeschichte(page: Page): Promise<void> {
  await expect(page).toHaveURL(/\/mit-konto\?ansicht=rundgang/);
  await expect(page.locator('.mk-titel')).toHaveText('So machst du mit Konto mit');
  await expect(page.locator('.mk-zaehler')).toHaveText('Schritt 1 von 3');
  await expect(page.locator('.mk-anmelden')).toHaveCount(0);
  await page.locator('.mk-weiter').click();
  await page.locator('.mk-weiter').click();
  await expect(page.locator('.mk-zaehler')).toHaveText('Schritt 3 von 3');
  await expect(page.locator('.mk-weiter')).toHaveCount(0);
  await expect(page.locator('.mk-anmelden')).toBeVisible();
  await kontrastPruefen(page, ['.mk-schritt-satz', '.mk-weiter-suchen']);
}

test('Besucher: Hilfe startet Selbst beitragen als Bildergeschichte', async ({ page }) => {
  await page.goto('/search');
  await page.locator('.mobile-header .menu-button').click();
  await page.locator('.mobile-menu-item', { hasText: 'Hilfe' }).first().click();

  const knopf = page.locator('app-help-dialog .rundgang-mitmachen');
  await expect(knopf).toHaveText('Selbst beitragen (3 Bilder)');
  await expect(knopf).not.toHaveAttribute('aria-disabled', 'true');
  await knopf.click();
  await expect(page.locator('app-help-dialog')).toHaveCount(0);
  await expect(page.locator('app-rundgang .blase')).toHaveCount(0);
  await bildergeschichte(page);
});

test('Besucher: Menü startet Selbst beitragen als Bildergeschichte, nach der Anmeldung Beitragen', async ({ page }) => {
  await page.goto('/search');
  await page.locator('.mobile-header .menu-button').click();

  const eintrag = page.locator('app-mobile-menu .mobile-menu-rundgang-mitmachen');
  await expect(eintrag).toContainText('Selbst beitragen (3 Bilder)');
  await expect(eintrag).not.toHaveAttribute('aria-disabled', 'true');
  await eintrag.scrollIntoViewIfNeeded();
  await eintrag.click();
  await bildergeschichte(page);

  // Im Dev-Stack ohne Keycloak über die Login-Auswahl; danach geht es nach Beitragen
  await page.locator('.mk-anmelden').click();
  await expect(page).toHaveURL(/\/login\?returnUrl=%2Fcontribute$/);
  await page.locator('.gutgesagt-button').click();
  await page.locator('input[formControlName="email"]').fill(KONTO.email);
  await page.locator('input[formControlName="password"]').fill(KONTO.passwort);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/(contribute|einwilligung)/, { timeout: 20_000 });
});
