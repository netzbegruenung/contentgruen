import { expect, test } from './fixtures';
import { KONTO } from './konto';

/**
 * Besucher: ohne Anmeldung suchen und Ergebnisse lesen; was Mitwirkenden vorbehalten
 * ist, fuehrt zur Anmeldung. Laeuft ohne gespeicherte Sitzung.
 */
test('Besucher: Suche ohne Anmeldung', async ({ page, bild }) => {
  const suche = page.waitForResponse((r) => r.url().includes('/api/v1/search/searchByText'));
  await page.goto(`/result?searchQuery=${encodeURIComponent('Windräder töten Vögel')}`);
  expect((await suche).status()).toBe(200);
  await expect(page.locator('app-kartenliste app-beitragskarte').first()).toBeVisible({ timeout: 45_000 });
  expect(new URL(page.url()).pathname).toBe('/result');
  // Ohne Anmeldung kein Autor auf den Karten (beitragskarte: zeigtAutor)
  await expect.soft(page.locator('app-kartenliste .karte-meta', { hasText: 'Von:' })).toHaveCount(0);
  await bild('90-besucher-suche');
});

test('Besucher: von der Startseite suchen und zurueck', async ({ page }) => {
  await page.goto('/search');
  await expect(page).toHaveURL(/\/search$/);
  const feld = page.locator('input[name="searchQuery"]');
  await feld.fill('Windräder töten Vögel');
  await feld.press('Enter');
  await page.waitForURL(/\/result\?/);
  expect(new URL(page.url()).searchParams.get('searchQuery')).toBe('Windräder töten Vögel');
  await expect(page.locator('app-kartenliste app-beitragskarte').first()).toBeVisible({ timeout: 45_000 });
  await page.goBack();
  await expect(page).toHaveURL(/\/search$/);
});

test('Besucher: 401 der Suche fuehrt nicht zur Anmeldung', async ({ page }) => {
  // Die Suche ist oeffentlich (PublicEndpoints): Ein 401 zeigt einen Fehler, statt umzuleiten.
  await page.route('**/api/v1/search/searchByText**', (anfrage) => anfrage.fulfill({ status: 401, json: {} }));
  await page.goto(`/result?searchQuery=${encodeURIComponent('Windräder töten Vögel')}`);
  await expect(page.locator('app-error-message .error-card')).toBeVisible();
  await page.waitForLoadState('networkidle');
  expect(new URL(page.url()).pathname).toBe('/result');
});

for (const pfad of ['/contribute', '/contributions', '/einwerfen', '/fangkorb']) {
  test(`Besucher: ${pfad} fuehrt zur Anmeldung`, async ({ page }) => {
    await page.goto(pfad);
    await page.waitForURL(/\/login\?/);
    expect(new URL(page.url()).searchParams.get('returnUrl')).toBe(pfad);
  });
}

test('Besucher: nach der Anmeldung zurueck, wohin es gehen sollte', async ({ page }) => {
  await page.goto('/fangkorb');
  await page.waitForURL(/\/login\?/);
  await page.getByRole('button', { name: /Direktanmeldung/ }).click();
  await page.waitForURL(/\/login\/managed/);
  await page.locator('input[formControlName="email"]').fill(KONTO.email);
  await page.locator('input[formControlName="password"]').fill(KONTO.passwort);
  await page.locator('form.login-form button[type="submit"]').click();
  await page.waitForURL(/\/fangkorb/);
  await expect(page.locator('.tabs')).toBeVisible();
});
