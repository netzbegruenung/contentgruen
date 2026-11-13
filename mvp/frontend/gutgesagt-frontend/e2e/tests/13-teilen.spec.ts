import { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Teilen (B7): "Teilen" an der Karte, "Ergebnis teilen" im Kopfband, "Teilen" auf der
 * Beitragsseite. Alle Anfragen an /api sind gemockt (route.fulfill), es braucht nur ein
 * ng serve (E2E_BASE_URL); der Dev-Stack wird nicht gefragt, nichts wird angelegt.
 *
 * Mobil (390 px) ersetzt ein Init-Skript navigator.share und merkt sich die Aufrufe;
 * am Desktop (1280 px) gibt es kein navigator.share, dann liegt der Link in der
 * Zwischenablage und die Snackbar sagt es.
 */
const ERKANNT = { id: '22222222-2222-4333-8444-555555555555', text: 'Windräder töten die Vögel!' };
const SUCHE = 'Windräder töten Vögel';
const KOMMENTAR_ID = '33333333-2222-4333-8444-555555555555';

const KOMMENTAR = {
  id: KOMMENTAR_ID,
  content_type: 'commentary',
  title: 'Windräder kosten weniger Vögel als Glasfassaden',
  text: 'An Glasscheiben sterben in Deutschland jedes Jahr über 100 Millionen Vögel, an Windrädern ein Bruchteil davon.',
  created: '2026-11-01T10:00:00Z',
  status: 'visible',
  references: [],
  references_count: 0,
};

const ANTWORT = {
  query_was_newly_added_as_statement: false,
  statement_id: '11111111-2222-4333-8444-555555555555',
  statement_text: SUCHE,
  commentary_search_results_count: 1,
  commentary_search_results: [
    {
      score: 0.95,
      statement_id: ERKANNT.id,
      statement_text: ERKANNT.text,
      statement_similarity_score: 0.9,
      reply_relevance: 0.8,
      themen: [],
      commentary_result: KOMMENTAR,
    },
  ],
  generictext_search_results_count: 0,
  generictext_search_results: [],
  image_search_results_count: 0,
  image_search_results: [],
  post_search_results_count: 0,
  post_search_results: [],
};

/** Mockt jede Anfrage an /api; liefert die Zahl der Nutzungs-Meldungen (POST …/usage). */
async function mocken(page: Page): Promise<{ nutzungen: () => number }> {
  let nutzungen = 0;
  await page.route('**/api/**', (r) => {
    const url = r.request().url();
    if (url.includes('/search/searchByText')) return r.fulfill({ json: ANTWORT });
    if (url.includes('/statement/aehnliche')) return r.fulfill({ json: { results: [] } });
    if (url.includes(`/content/beitrag/${KOMMENTAR_ID}`)) {
      return r.fulfill({ json: { ...KOMMENTAR, aussage: ERKANNT, weitere_antworten: [] } });
    }
    if (r.request().method() === 'POST' && /\/usage\/content\/[^/]+\/usage/.test(url)) {
      nutzungen++;
      return r.fulfill({ json: { success: true, message: 'ok', usage_count: 1 } });
    }
    return r.fulfill({ status: 404, json: {} });
  });
  return { nutzungen: () => nutzungen };
}

/** Ein navigator.share, das sich die Aufrufe merkt; mit abbrechen=true wie "Menue geschlossen". */
async function teilenMenue(page: Page, abbrechen = false): Promise<void> {
  await page.addInitScript((abbruch) => {
    const w = window as unknown as { geteilt: ShareData[] };
    w.geteilt = [];
    Object.defineProperty(navigator, 'share', {
      configurable: true,
      value: (daten: ShareData) => {
        w.geteilt.push(daten);
        return abbruch ? Promise.reject(new DOMException('abgebrochen', 'AbortError')) : Promise.resolve();
      },
    });
    Object.defineProperty(navigator, 'canShare', { configurable: true, value: () => true });
  }, abbrechen);
}

async function ohneTeilenMenue(page: Page): Promise<void> {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
  });
}

const geteilt = (page: Page) => page.evaluate(() => (window as unknown as { geteilt: ShareData[] }).geteilt);

async function sucheOeffnen(page: Page): Promise<void> {
  await page.goto(`/result?searchQuery=${encodeURIComponent(SUCHE)}`);
  await expect(page.locator('.kopfband-aussage')).toHaveText(`„${ERKANNT.text}“`, { timeout: 45_000 });
}

test.describe('Teilen mobil 390 px', () => {
  test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });

  test('Karte und Ergebnis ueber das Teilen-Menue', async ({ page, bild }) => {
    const { nutzungen } = await mocken(page);
    await teilenMenue(page);
    await sucheOeffnen(page);

    const karte = page.locator('app-beitragskarte').first();
    const teilen = karte.getByRole('button', { name: `Beitrag teilen: „${KOMMENTAR.title}“` });
    await expect(teilen).toBeVisible();
    const groesse = await teilen.boundingBox();
    expect(groesse!.width).toBeGreaterThanOrEqual(44);
    expect(groesse!.height).toBeGreaterThanOrEqual(44);
    // Kein waagerechtes Scrollen durch den zusaetzlichen Knopf
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
    await bild('teilen-390-ergebnis');
    await karte.scrollIntoViewIfNeeded();
    await bild('teilen-390-karte');

    await teilen.click();
    await expect.poll(() => geteilt(page)).toHaveLength(1);
    const [karteGeteilt] = await geteilt(page);
    expect(karteGeteilt.url).toMatch(new RegExp(`/beitrag/${KOMMENTAR_ID}$`));
    expect(karteGeteilt.text).toBe(KOMMENTAR.text);
    await expect.poll(nutzungen).toBe(1);

    await page.getByRole('button', { name: `Ergebnis teilen: Antworten auf „${ERKANNT.text}“` }).click();
    await expect.poll(() => geteilt(page)).toHaveLength(2);
    const ergebnis = (await geteilt(page))[1];
    expect(ergebnis.url).toMatch(/\/result\?searchQuery=Windr%C3%A4der%20t%C3%B6ten%20V%C3%B6gel$/);
    expect(ergebnis.text).toBe(`Antworten auf: „${ERKANNT.text}“`);
    // Eine Ergebnisseite teilen zaehlt nicht als Nutzung
    expect(nutzungen()).toBe(1);
  });

  test('Abbruch im Teilen-Menue bleibt still', async ({ page }) => {
    const { nutzungen } = await mocken(page);
    await teilenMenue(page, true);
    await sucheOeffnen(page);

    await page.locator('app-beitragskarte').first().locator('button.teilen-knopf').click();
    await expect.poll(() => geteilt(page)).toHaveLength(1);
    await page.waitForTimeout(500);
    await expect(page.locator('mat-snack-bar-container')).toHaveCount(0);
    expect(nutzungen()).toBe(0);
  });

  test('Beitragsseite: Teilen unter der Karte', async ({ page, bild }) => {
    const { nutzungen } = await mocken(page);
    await teilenMenue(page);
    await page.goto(`/beitrag/${KOMMENTAR_ID}`);
    const knopf = page.getByRole('button', { name: 'Teilen', exact: true });
    await expect(knopf).toBeVisible({ timeout: 45_000 });
    // In der Karte selbst steht hier kein zweiter Teilen-Knopf
    await expect(page.locator('app-beitragskarte button.teilen-knopf')).toHaveCount(0);
    await bild('teilen-390-beitragsseite');

    await knopf.click();
    await expect.poll(() => geteilt(page)).toHaveLength(1);
    await expect.poll(nutzungen).toBe(1);
  });
});

test.describe('Teilen Desktop 1280 px', () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test('ohne Teilen-Menue: Link kopiert, mit Rueckmeldung', async ({ page, context, bild }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    const { nutzungen } = await mocken(page);
    await ohneTeilenMenue(page);
    await sucheOeffnen(page);
    await bild('teilen-1280-ergebnis');

    await page.locator('app-beitragskarte').first().locator('button.teilen-knopf').click();
    await expect(page.locator('mat-snack-bar-container')).toContainText('Link kopiert – füg ihn ein, wo du teilen willst.');
    expect(await page.evaluate(() => navigator.clipboard.readText())).toMatch(new RegExp(`/beitrag/${KOMMENTAR_ID}$`));
    await expect.poll(nutzungen).toBe(1);
    await bild('teilen-1280-kopiert');

    await page.locator('.ergebnis-teilen').click();
    await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toMatch(/\/result\?searchQuery=/);
    expect(nutzungen()).toBe(1);
  });
});
