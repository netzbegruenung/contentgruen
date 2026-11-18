import { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Ergebnisseite als eine Liste: Kopfband mit der erkannten Aussage, Chips je Typ,
 * Gruppen je Aussage, je Typ zuerst drei Karten, Bilder sichtbar. Die Suche ist
 * gemockt (route.fulfill), damit gemischte Treffer aller vier Typen sicher dastehen;
 * der Dev-Stack liefert nur Seite und Anmeldung. Liest nur, legt nichts an.
 */
const ERKANNT = { id: '22222222-2222-4333-8444-555555555555', text: 'Windräder töten die Vögel!' };
const ANDERE = { id: '44444444-2222-4333-8444-555555555555', text: 'Windkraft zerstört die Landschaft!' };
const ALTERNATIVEN = [
  { id: '55555555-2222-4333-8444-555555555555', text: 'Windräder sind zu laut', replysuggestions_count: 1, score: 0.8 },
  { id: '66666666-2222-4333-8444-555555555555', text: 'Infraschall macht krank', replysuggestions_count: 0, score: 0.7 },
];

type Typ = 'commentary' | 'generictext' | 'image' | 'post';
const FELD: Record<Typ, string> = {
  commentary: 'commentary_result',
  generictext: 'generictext_result',
  image: 'image_result',
  post: 'post_result',
};
const INHALTSTYP: Record<Typ, string> = { commentary: 'commentary', generictext: 'generic_text', image: 'image', post: 'post' };

function treffer(typ: Typ, id: string, aussage: { id: string; text: string } | null, score: number) {
  const inhalt: Record<string, unknown> = {
    id,
    content_type: INHALTSTYP[typ],
    title: `[e2e-mock] ${typ} ${id}`,
    text: 'Gemockter Text für die Darstellung der Ergebnisseite.',
    created: '2026-11-01T10:00:00Z',
    status: 'visible',
    references: [],
    references_count: 0,
  };
  if (typ === 'image') inhalt['image_url'] = '/marke/icon-512.png';
  if (typ === 'post') Object.assign(inhalt, { platform: 'bluesky', url: 'https://example.org/post/1', engagement: 0 });
  return {
    score,
    statement_id: aussage?.id ?? null,
    statement_text: aussage?.text ?? '',
    statement_similarity_score: 0.9,
    reply_relevance: 0.8,
    themen: [],
    [FELD[typ]]: inhalt,
  };
}

const kommentare = [
  treffer('commentary', 'k-1', ERKANNT, 0.95),
  treffer('commentary', 'k-2', ERKANNT, 0.9),
  treffer('commentary', 'k-3', ANDERE, 0.88),
  treffer('commentary', 'k-4', ERKANNT, 0.85),
  treffer('commentary', 'k-5', ERKANNT, 0.8),
  treffer('commentary', 'k-6', null, 0.5),
];
const ANTWORT = {
  query_was_newly_added_as_statement: false,
  statement_id: '11111111-2222-4333-8444-555555555555',
  statement_text: 'Windräder töten Vögel und zerstören die Landschaft',
  commentary_search_results_count: kommentare.length,
  commentary_search_results: kommentare,
  generictext_search_results_count: 1,
  generictext_search_results: [treffer('generictext', 'h-1', ERKANNT, 0.7)],
  image_search_results_count: 2,
  image_search_results: [treffer('image', 'b-1', ERKANNT, 0.75), treffer('image', 'b-2', ANDERE, 0.6)],
  post_search_results_count: 1,
  post_search_results: [treffer('post', 'p-1', ERKANNT, 0.65)],
};

async function oeffnen(page: Page): Promise<void> {
  await page.route('**/api/v1/search/searchByText**', (r) => r.fulfill({ json: ANTWORT }));
  await page.route('**/api/v1/statement/aehnliche**', (r) => r.fulfill({ json: { results: ALTERNATIVEN } }));
  await page.goto(`/result?searchQuery=${encodeURIComponent(ANTWORT.statement_text)}`);
  await expect(page.locator('.erkannt-aussage')).toHaveText(`„${ERKANNT.text}“`, { timeout: 45_000 });
}

for (const [name, breite] of [['390', 390], ['1280', 1280]] as const) {
  test.describe(`Ergebnisseite ${name} px`, () => {
    test.use({ viewport: { width: breite, height: breite < 600 ? 844 : 900 } });

    test(`Zeile "Erkannt als", beste Antwort, eingeklappte Karten, Gruppen und Bilder (${name})`, async ({ page, bild }) => {
      await oeffnen(page);

      // V3 (Designrunde 17.11.): keine Chips; die Titel tragen Typ und Zahl, die beste Antwort ganz
      await expect(page.locator('.typ-chip, .kopfband')).toHaveCount(0);
      await expect(page.locator('.gruppe').first().locator('.typ-ueberschrift')).toHaveText([
        'Beste Antwort', 'Weitere Antworten · 3', 'Hintergrundinfo · 1', 'Bild · 1', 'Post · 1',
      ], { ignoreCase: true });
      await expect(page.locator('.beste-antwort .kopieren-knopf')).toBeVisible();
      const zu = page.locator('.eingeklappte-karten .aufklapp-knopf');
      await expect(zu.first()).toHaveAttribute('aria-expanded', 'false');

      // Gruppen: erkannte offen; andere Aussage und direkte Treffer eingeklappt darunter.
      // Der Kopf der erkannten Gruppe nennt die Aussage nur fuer Screenreader (visually-hidden).
      await expect(page.locator('.gruppe > h2 .gruppe-label')).toHaveText([`Zu dieser Aussage: „${ERKANNT.text}“`]);
      const weitere = page.locator('.weitere-umschalter');
      await expect(weitere).toContainText('Weitere, weniger passende Treffer (3)');
      await weitere.click();
      await expect(weitere).toHaveAttribute('aria-expanded', 'true');
      await expect(page.locator('.gruppe > h2 .gruppe-label')).toHaveText([
        `Zu dieser Aussage: „${ERKANNT.text}“`,
        'Zu einer anderen Aussage:',
        'Passt zu deinem Suchtext',
      ]);
      await weitere.click();
      // Kartentitel unter Gruppe (h2) und Typ (h3) als h4
      await expect(page.locator('.typ-block h3.karte-titel')).toHaveCount(0);
      // Keine doppelte Antwort-auf-Zeile an den Karten
      await expect(page.locator('app-beitragskarte .statement-zeile')).toHaveCount(0);
      // Bilder erscheinen nach dem Aufklappen an Ort und Stelle
      const bildKnopf = page.locator('.gruppe').first().locator('[data-typ="image"] .aufklapp-knopf');
      await bildKnopf.click();
      await expect(bildKnopf).toHaveAttribute('aria-expanded', 'true');
      await expect(page.locator('[data-typ="image"] app-beitragskarte img').first()).toBeVisible();

      // Kein waagerechtes Scrollen der Seite
      const ueberlauf = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(ueberlauf).toBeLessThanOrEqual(0);
      await bild(`ergebnis-${name}-oben`);
      await bild(`ergebnis-${name}-ganz`, true);
    });

    test(`"Nicht gemeint?" bietet die Alternativen an (${name})`, async ({ page }) => {
      await oeffnen(page);
      const liste = page.locator('.erkannt-liste a');
      const umschalter = page.locator('.erkannt-umschalter');
      await expect(umschalter).toHaveAttribute('aria-expanded', 'false');
      await expect(liste.first()).toBeHidden();
      await umschalter.click();
      await expect(umschalter).toHaveAttribute('aria-expanded', 'true');
      await expect(liste).toHaveText(ALTERNATIVEN.map((a) => a.text));
    });

    test(`"Alle N zeigen" setzt den Fokus auf die erste neue Karte (${name})`, async ({ page }) => {
      await oeffnen(page);
      const block = page.locator('.gruppe').first().locator('[data-typ="commentary"]');
      await expect(block.locator('app-beitragskarte')).toHaveCount(3);
      await block.getByRole('button', { name: 'Alle 3 weiteren Antworten zeigen' }).click();
      await expect(block.locator('app-beitragskarte')).toHaveCount(4);
      const imVierten = await block
        .locator('app-beitragskarte')
        .nth(3)
        .evaluate((karte) => karte.contains(document.activeElement));
      expect(imVierten).toBe(true);
    });
  });
}

/** Linke Kante und Breite eines Elements, gerundet. */
async function kasten(page: Page, selektor: string): Promise<{ x: number; y: number; breite: number }> {
  const box = await page.locator(selektor).first().boundingBox();
  if (!box) throw new Error(`Nicht sichtbar: ${selektor}`);
  return { x: Math.round(box.x), y: Math.round(box.y), breite: Math.round(box.width) };
}

// Desktop ab 1024 px zweispaltig (Maintainer 18.11.), darunter eine Spalte; der Kopf springt nicht.
test.describe('Ergebnisseite zweispaltig: Geometrie', () => {
  test('1280 px: beste Antwort und weitere nebeneinander, Kopf vor und nach neuer Suche gleich breit', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await oeffnen(page);
    const beste = await kasten(page, '.beste-antwort');
    const rechts = await kasten(page, '.gruppe.mit-bester .eingeklappte-karten');
    expect(rechts.x).toBeGreaterThan(beste.x + beste.breite);
    const besteTitel = await kasten(page, '.gruppe.mit-bester .typ-block .beste-ueberschrift');
    const weitereTitel = await kasten(page, '.gruppe.mit-bester .typ-block .weitere-ueberschrift');
    expect(Math.abs(weitereTitel.y - besteTitel.y)).toBeLessThanOrEqual(2);
    const kopfVorher = await kasten(page, '.search-box');

    // Neue Suche mit verzoegerter Antwort: auch waehrend des Ladens bleibt der Kopf gleich
    let freigeben: () => void = () => undefined;
    const gehalten = new Promise<void>((weiter) => (freigeben = weiter));
    await page.unroute('**/api/v1/search/searchByText**');
    await page.route('**/api/v1/search/searchByText**', async (r) => {
      await gehalten;
      await r.fulfill({ json: ANTWORT });
    });
    await page.locator('.search-box input').fill('Windräder sind zu laut');
    await page.locator('.search-box input').press('Enter');
    await expect(page.locator('app-loading-spinner .loading-container')).toBeVisible();
    expect(await kasten(page, '.search-box')).toEqual(kopfVorher);
    freigeben();
    await expect(page.locator('.erkannt-aussage')).toBeVisible({ timeout: 45_000 });
    expect(await kasten(page, '.search-box')).toEqual(kopfVorher);
  });

  test('1023 px: beste Antwort und weitere untereinander', async ({ page }) => {
    await page.setViewportSize({ width: 1023, height: 900 });
    await oeffnen(page);
    await expect(page.locator('.gruppe.mit-bester')).toHaveCount(1);
    const beste = await kasten(page, '.beste-antwort');
    const weitere = await kasten(page, '.gruppe.mit-bester .eingeklappte-karten');
    expect(weitere.x).toBe(beste.x);
    expect(weitere.y).toBeGreaterThan(beste.y);
  });
});
