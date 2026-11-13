import { expect, test } from './fixtures';

/**
 * Rundgang und Zurück im Browser: Zurück beendet den Rundgang, statt den Schritt auf der
 * vorigen Seite stehen zu lassen. Läuft als Besucher (Projekt „besucher“), legt nichts an.
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
