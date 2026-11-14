import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Der Link „Mehr dazu im Datenschutz“ unter dem Suchfeld springt zum Abschnitt „Deine
 * Suchanfragen“, mobil und am Desktop (Persona-Test Gerd). Ohne Stack: jede Anfrage an /api
 * beantwortet der Test, also auch gegen `ng serve` ohne Backend (E2E_BASE_URL). Liest nur.
 *
 * Gescrollt wird das Dokument, nicht mat-sidenav-content, und der Kopf scrollt mit: Die
 * Überschrift muss oben im Fenster stehen, ohne dass etwas sie verdeckt.
 */
async function ohneStack(page: Page): Promise<void> {
  await page.route('**/api/**', (anfrage) => {
    const pfad = new URL(anfrage.request().url()).pathname;
    const status = pfad === '/api/user-info' || pfad === '/api/check-session' ? 401 : 404;
    return anfrage.fulfill({ status, json: {} });
  });
}

for (const [name, viewport] of [
  ['mobil', { width: 360, height: 740 }],
  ['desktop', { width: 1280, height: 900 }],
] as const) {
  test(`Hinweis am Suchfeld springt zu „Deine Suchanfragen“ (${name})`, async ({ page, bild }) => {
    await page.setViewportSize(viewport);
    await ohneStack(page);
    await page.goto('/');

    await page.getByRole('link', { name: 'Mehr dazu im Datenschutz' }).first().click();
    await expect(page).toHaveURL(/\/datenschutz#suchanfragen$/);

    const ueberschrift = page.locator('#suchanfragen h2');
    await expect(ueberschrift).toHaveText('Deine Suchanfragen');
    await expect
      .poll(async () => (await ueberschrift.boundingBox())?.y ?? -1, { message: 'Überschrift oben im Fenster' })
      .toBeGreaterThanOrEqual(0);
    const oben = (await ueberschrift.boundingBox())!.y;
    expect(oben).toBeLessThan(viewport.height / 4);
    // Nichts liegt über der Überschrift (etwa ein klebender Kopf)
    const box = (await ueberschrift.boundingBox())!;
    const getroffen = await page.evaluate(
      ([x, y]) => document.elementFromPoint(x, y)?.closest('#suchanfragen h2') !== null,
      [box.x + 5, box.y + box.height / 2],
    );
    expect(getroffen).toBe(true);
    await bild(`datenschutz-sprung-${name}`);
  });
}
