import { expect, test } from './fixtures';
import { KONTO } from './konto';

/**
 * Rundgang und Zurück im Browser: Zurück beendet den Rundgang, statt den Schritt auf der
 * vorigen Seite stehen zu lassen. Läuft als Besucher (Projekt „besucher“), legt nichts an;
 * der Test zur Hilfe meldet sich am Ende über die Direktanmeldung an.
 */
test('Besucher: Zurück im Browser beendet den Rundgang, er lässt sich neu starten', async ({ page }) => {
  await page.goto('/search');
  await page.getByRole('button', { name: 'Rundgang starten' }).click();
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
  const feld = page.locator('app-search.start-suche input[name="searchQuery"]');
  await feld.fill('Windräder töten Vögel');
  await expect(feld).toHaveValue('Windräder töten Vögel');
  await expect(page.getByRole('button', { name: 'Rundgang starten' })).toHaveCount(0);

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

test('Besucher: Hilfe teasert Selbst beitragen an, nach der Anmeldung startet es', async ({ page }) => {
  await page.goto('/search');
  await page.locator('.mobile-header .menu-button').click();
  await page.locator('.mobile-menu-item', { hasText: 'Hilfe' }).first().click();

  const knopf = page.locator('app-help-dialog .rundgang-mitmachen');
  await expect(knopf).toHaveText('Selbst beitragen (4 Schritte)');
  await expect(knopf).toHaveAttribute('aria-disabled', 'true');
  await expect(knopf).toHaveAccessibleDescription(/Nach der Anmeldung zeigen wir dir, wie Beitragen geht\./);
  await expect(knopf).toBeDisabled(); // Playwright wertet aria-disabled aus
  await knopf.click({ force: true });
  await expect(page.locator('app-help-dialog')).toBeVisible(); // ohne Wirkung, kein Rundgang
  await expect(page.locator('app-rundgang .blase')).toHaveCount(0);

  for (const sel of ['.rundgang-mitmachen-hinweis', '.rundgang-mitmachen']) {
    const { farbe, grund } = await page.locator(`app-help-dialog ${sel}`).evaluate((el) => {
      let g = el as HTMLElement | null;
      while (g && /rgba\(0, 0, 0, 0\)|transparent/.test(getComputedStyle(g).backgroundColor)) g = g.parentElement;
      return { farbe: getComputedStyle(el).color, grund: getComputedStyle(g!).backgroundColor };
    });
    expect(kontrast(farbe, grund), `${sel}: ${farbe} auf ${grund}`).toBeGreaterThanOrEqual(4.5);
  }

  // Anmelden führt über die Direktanmeldung zurück auf die Startseite mit offener Hilfe
  await page.locator('app-help-dialog .rundgang-anmelden').click();
  await expect(page).toHaveURL(/\/login\?returnUrl=%2Fsearch%3Fhilfe%3D1$/);
  await page.locator('.gutgesagt-button').click();
  await page.locator('input[formControlName="email"]').fill(KONTO.email);
  await page.locator('input[formControlName="password"]').fill(KONTO.passwort);
  await page.locator('button[type="submit"]').click();
  await expect(page.locator('app-help-dialog')).toBeVisible({ timeout: 20_000 });
  await expect(page).toHaveURL(/\/search$/); // Parameter wieder weg
  const frei = page.locator('app-help-dialog .rundgang-mitmachen');
  await expect(frei).not.toHaveAttribute('aria-disabled', 'true');
  await expect(page.locator('app-help-dialog .rundgang-mitmachen-hinweis')).toHaveCount(0);
  await frei.click();
  await expect(page.locator('.blase h3')).toHaveText('Beitragen', { timeout: 20_000 });
});
