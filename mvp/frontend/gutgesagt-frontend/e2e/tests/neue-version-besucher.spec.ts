import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Nach einem Deploy fehlen die alten Chunks: Wer die App offen hat und eine noch nicht geladene
 * Route oeffnet, bekommt beim dynamischen Import eine 404. Die App laedt dann das Ziel hart
 * neu und kommt so an die neue Version, ohne dass jemand von Hand neu laden muss.
 *
 * Nachgestellt: Nach dem ersten Laden beantwortet der Test jedes neue Skript mit 404, bis der
 * naechste Seitenaufruf (Dokument) kommt. Ohne Stack: jede Anfrage an /api beantwortet der
 * Test, also auch gegen `ng serve` ohne Backend (E2E_BASE_URL).
 */
async function ohneStack(page: Page): Promise<void> {
  await page.route('**/api/**', (anfrage) => {
    const pfad = new URL(anfrage.request().url()).pathname;
    const status = pfad === '/api/user-info' || pfad === '/api/check-session' ? 401 : 404;
    return anfrage.fulfill({ status, json: {} });
  });
}

test('fehlender Chunk nach einem Deploy: die App laedt das Ziel selbst neu', async ({ page }) => {
  await ohneStack(page);
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Impressum' }).first()).toBeVisible();
  // Erst wenn die Startseite alle ihre Chunks hat, gilt der Deploy als vorbei.
  await page.waitForLoadState('networkidle');
  // Merker im laufenden Dokument: Nach einem harten Seitenwechsel ist er weg.
  await page.evaluate(() => ((window as unknown as { alteSeite: boolean }).alteSeite = true));

  let deployVorbei = false;
  const verweigert: string[] = [];
  const seitenaufrufe: string[] = [];
  page.on('request', (anfrage) => {
    if (anfrage.resourceType() === 'document' && anfrage.frame() === page.mainFrame()) {
      deployVorbei = true;
      seitenaufrufe.push(new URL(anfrage.url()).pathname);
    }
  });
  await page.route(/\.m?js(\?.*)?$/, (anfrage) => {
    if (deployVorbei) return anfrage.fallback();
    verweigert.push(new URL(anfrage.request().url()).pathname);
    return anfrage.fulfill({ status: 404, contentType: 'text/html', body: 'Not Found' });
  });

  await page.getByRole('link', { name: 'Impressum' }).first().click();

  await expect(page).toHaveURL(/\/impressum$/);
  await expect(page.getByRole('heading', { name: 'Impressum', level: 1 })).toBeVisible();
  expect(verweigert.length, 'mindestens ein Chunk kam mit 404').toBeGreaterThan(0);
  expect(seitenaufrufe, 'genau ein harter Seitenwechsel, aufs Ziel').toEqual(['/impressum']);
  expect(await page.evaluate(() => (window as unknown as { alteSeite?: boolean }).alteSeite)).toBeUndefined();
  // Kein Notfall-Hinweis: Der Speicher war da, also wurde automatisch neu geladen.
  await expect(page.getByText('Gut gesagt wurde aktualisiert')).toHaveCount(0);
});
