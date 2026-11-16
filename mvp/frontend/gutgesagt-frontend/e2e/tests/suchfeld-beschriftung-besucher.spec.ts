import type { Locator, Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Die Beschriftung des Suchfelds sagt, dass der fremde Text gemeint ist, auf den man
 * antworten will (Ersteindruck-Test 14.11.). Bei 360 px darf sie nicht abgeschnitten sein:
 * weder die lange Fassung auf der Startseite noch die kompakte neben der Lupe auf der
 * Trefferseite, leer und mit Text. Ohne Stack: jede Anfrage an /api beantwortet der Test,
 * also auch gegen `ng serve` ohne Backend (E2E_BASE_URL). Liest nur.
 */
const AUSSAGE = { id: '22222222-2222-4333-8444-555555555555', text: 'Windräder töten die Vögel!' };
const KOMMENTAR = {
  id: '33333333-2222-4333-8444-555555555555',
  content_type: 'commentary',
  title: 'Windräder kosten weniger Vögel als Glasfassaden',
  text: 'An Glasscheiben sterben jedes Jahr weit mehr Vögel als an Windrädern.',
  created: '2026-11-01T10:00:00Z',
  status: 'visible',
  references: [],
  references_count: 0,
};
const ANTWORT = {
  query_was_newly_added_as_statement: false,
  statement_id: '11111111-2222-4333-8444-555555555555',
  statement_text: 'Windräder töten Vögel',
  commentary_search_results_count: 1,
  commentary_search_results: [
    {
      score: 0.9,
      statement_id: AUSSAGE.id,
      statement_text: AUSSAGE.text,
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

async function ohneStack(page: Page): Promise<void> {
  await page.route('**/api/**', (anfrage) => {
    const pfad = new URL(anfrage.request().url()).pathname;
    if (pfad.includes('/search/searchByText')) return anfrage.fulfill({ json: ANTWORT });
    if (pfad.includes('/statement/aehnliche')) return anfrage.fulfill({ json: { results: [] } });
    const status = pfad === '/api/user-info' || pfad === '/api/check-session' ? 401 : 404;
    return anfrage.fulfill({ status, json: {} });
  });
}

/** Die Beschriftung ist ganz zu sehen: kein Überlauf im Label, und sie liegt im Feld. */
async function nichtAbgeschnitten(label: Locator, text: string): Promise<void> {
  await expect(label).toHaveText(text);
  const masse = await label.evaluate((el) => {
    const l = el.getBoundingClientRect();
    const feld = el.closest('.mat-mdc-text-field-wrapper')!.querySelector('.mat-mdc-form-field-infix')!.getBoundingClientRect();
    return { scroll: el.scrollWidth, client: el.clientWidth, links: l.left - feld.left, rechts: feld.right - l.right };
  });
  expect(masse.scroll, `„${text}“ abgeschnitten: ${masse.scroll} > ${masse.client}`).toBeLessThanOrEqual(masse.client);
  // Innerhalb des Eingabebereichs (infix), nicht unter der Lupe oder über den Rand hinaus
  expect(masse.links, `„${text}“ ragt links aus dem Feld`).toBeGreaterThanOrEqual(-0.5);
  expect(masse.rechts, `„${text}“ ragt rechts aus dem Feld`).toBeGreaterThanOrEqual(-0.5);
}

test.describe('Beschriftung des Suchfelds bei 360 px', () => {
  test.use({ viewport: { width: 360, height: 740 } });

  test('Startseite: lange Fassung ganz zu sehen', async ({ page }) => {
    await ohneStack(page);
    await page.goto('/search');
    await nichtAbgeschnitten(page.locator('app-search .mdc-floating-label'), 'Worauf willst du antworten? Text einfügen');
  });

  test('Trefferseite: kompakte Fassung neben der Lupe, mit Text und leer', async ({ page }) => {
    await ohneStack(page);
    await page.goto(`/result?searchQuery=${encodeURIComponent('Windräder töten Vögel')}`);
    await expect(page.locator('app-beitragskarte').first()).toBeVisible({ timeout: 45_000 });
    const label = page.locator('app-search .mdc-floating-label');
    // Mit Text steht die Beschriftung klein über dem Feld
    await nichtAbgeschnitten(label, 'Worauf antworten? Text einfügen');
    // Leer steht sie in voller Größe im Feld, neben der Lupe: dort ist es am engsten
    await page.locator('app-search textarea, app-search input').first().fill('');
    await page.locator('body').click({ position: { x: 5, y: 5 } });
    // Wirklich in voller Größe im Feld, nicht noch klein darüber
    await expect(label).not.toHaveClass(/mdc-floating-label--float-above/);
    await nichtAbgeschnitten(label, 'Worauf antworten? Text einfügen');
  });
});
