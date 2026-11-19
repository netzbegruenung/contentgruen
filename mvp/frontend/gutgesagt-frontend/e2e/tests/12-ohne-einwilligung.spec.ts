import { Page } from '@playwright/test';
import { TESTDATEN_PRAEFIX, expect, lauf, test } from './fixtures';

/**
 * Weg ohne Art.-9-Einwilligung (UX-Review B2–B4, B18): keine Umleitung bei jedem Start,
 * Rückfrage vor dem Widerruf, Hinweiskasten über dem Formular, Eingabe übersteht den Umweg.
 *
 * Widerruft für das Testkonto und willigt am Ende wieder ein, damit die übrigen Specs
 * weiterlaufen. Achtung: Der Widerruf löscht die Stimmen des Testkontos und legt mit #661
 * einen Löschauftrag an; nur gegen einen Dev-Stack laufen lassen.
 */
const EINWILLIGUNG = '/api/v1/art9-einwilligung';

async function wiederEinwilligen(page: Page): Promise<void> {
  const stand = await (await page.request.get(EINWILLIGUNG)).json();
  if (!stand.eingewilligt) {
    const antwort = await page.request.post(EINWILLIGUNG, { data: { wortlaut: stand.aktueller_wortlaut.kennung } });
    expect(antwort.status()).toBe(204);
  }
}

test.afterEach(async ({ page }) => {
  await wiederEinwilligen(page);
});

test('Widerruf mit Rueckfrage, danach keine Umleitung beim Start (B2, B3)', async ({ page, bild }) => {
  await wiederEinwilligen(page);
  await page.goto('/einwilligung');
  await page.getByRole('button', { name: 'Einwilligung widerrufen' }).click();

  const frage = page.getByRole('dialog');
  await expect(frage).toContainText('Bewertungen werden sofort gelöscht');
  await bild('12a-widerruf-rueckfrage');
  await frage.getByRole('button', { name: 'Abbrechen' }).click();
  await expect(frage).toBeHidden();
  expect((await (await page.request.get(EINWILLIGUNG)).json()).eingewilligt).toBe(true);

  await page.getByRole('button', { name: 'Einwilligung widerrufen' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Widerrufen' }).click();
  await expect(page.getByRole('button', { name: 'Einwilligen und weiter' })).toBeVisible();
  expect((await (await page.request.get(EINWILLIGUNG)).json()).eingewilligt).toBe(false);

  // Neuer App-Start: Wer widerrufen hat, bleibt, wo er hinwollte
  await page.goto('/search');
  await page.waitForLoadState('networkidle');
  expect(new URL(page.url()).pathname).toBe('/search');
});

test('Ohne Einwilligung: Hinweis im Formular, kein "erneut versuchen", Eingabe uebersteht die Einwilligung (B4, B18)', async ({
  page,
  bild,
}) => {
  expect((await page.request.delete(EINWILLIGUNG)).status()).toBe(204);
  const hinweis = `${TESTDATEN_PRAEFIX} ohne Einwilligung ${lauf()}`;

  await page.goto('/einwerfen');
  const kasten = page.getByTestId('einwilligung-hinweis');
  await expect(kasten).toContainText('Zum Beitragen brauchst du deine Einwilligung.');
  await page.locator('#einwurf-hinweis').fill(hinweis);

  // Trotzdem absenden: 403, der Kasten kommt in den Blick und hat den Fokus,
  // keine Fehlermeldung, keine Snackbar
  await page.getByRole('button', { name: 'Einwerfen' }).click();
  await expect(kasten).toBeFocused();
  await expect(kasten).toBeInViewport();
  await expect(page.locator('.einwurf-rueckmeldung .fehler')).toHaveCount(0);
  await expect(page.locator('mat-snack-bar-container')).toHaveCount(0);
  await bild('12b-einwerfen-ohne-einwilligung');

  await kasten.getByRole('button', { name: 'Einwilligen' }).click();
  await page.waitForURL(/\/einwilligung\?returnUrl=/);
  await expect(page.locator('.mobile-header-title')).toHaveText('Einwilligung');
  await page.locator('mat-checkbox input[type=checkbox]').check();
  await page.getByRole('button', { name: 'Einwilligen und weiter' }).click();

  await page.waitForURL(/\/einwerfen/);
  await expect(page.locator('#einwurf-hinweis')).toHaveValue(hinweis);
  await expect(page.getByTestId('einwilligung-hinweis')).toHaveCount(0);
  await bild('12c-einwerfen-nach-einwilligung');
});
