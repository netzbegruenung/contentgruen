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

/**
 * Neun Antworten zur erkannten Aussage: am Desktop die beste und vier offen, zwei eingeklappt,
 * zwei hinter "Alle 4 weiteren Antworten zeigen" (Maintainer 18.11.). Die dritte offene hat
 * einen langen Text, damit sich zeigt, dass ihre Nachbarin nicht mitwaechst.
 */
const neunKommentare = Array.from({ length: 9 }, (_, i) => {
  const karte = treffer('commentary', `n-${i + 1}`, ERKANNT, 0.99 - i / 100);
  if (i === 2) {
    (karte['commentary_result'] as Record<string, unknown>)['text'] = 'Ein langer gemockter Text. '.repeat(30);
  }
  return karte;
});
const NEUN = {
  ...ANTWORT,
  commentary_search_results: neunKommentare,
  commentary_search_results_count: neunKommentare.length,
};

async function oeffnen(page: Page, antwort: typeof ANTWORT = ANTWORT): Promise<void> {
  await page.route('**/api/v1/search/searchByText**', (r) => r.fulfill({ json: antwort }));
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
      // Desktop: alle drei weiteren Antworten offen mit Kopieren (weniger als fuenf); am Handy keine
      await expect(page.locator('.offene-karten .kopieren-knopf')).toHaveCount(breite >= 1024 ? 3 : 0);
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
      // Handy: beste und zwei eingeklappt; Desktop: beste, vier offen, zwei eingeklappt
      const desktop = breite >= 1024;
      const bisher = desktop ? 7 : 3;
      await oeffnen(page, NEUN);
      const block = page.locator('.gruppe').first().locator('[data-typ="commentary"]');
      await expect(block.locator('app-beitragskarte')).toHaveCount(bisher);
      await block.getByRole('button', { name: `Alle ${desktop ? 4 : 8} weiteren Antworten zeigen` }).click();
      await expect(block.locator('app-beitragskarte')).toHaveCount(9);
      const imErstenNeuen = await block
        .locator('app-beitragskarte')
        .nth(bisher)
        .evaluate((karte) => karte.contains(document.activeElement));
      expect(imErstenNeuen).toBe(true);
    });
  });
}

/** Linke Kante und Breite eines Elements, gerundet. */
async function kasten(page: Page, selektor: string): Promise<{ x: number; y: number; breite: number }> {
  const box = await page.locator(selektor).first().boundingBox();
  if (!box) throw new Error(`Nicht sichtbar: ${selektor}`);
  return { x: Math.round(box.x), y: Math.round(box.y), breite: Math.round(box.width) };
}

// Desktop ab 1024 px (Maintainer 18.11.): oben beste Antwort und "Zu dieser Antwort" 50/50,
// darunter die weiteren Karten zu zweit; unter 1024 px eine Spalte; der Kopf springt nicht.
test.describe('Ergebnisseite zweispaltig: Geometrie', () => {
  test('1280 px: beste Antwort und Kasten nebeneinander, darunter zwei Karten nebeneinander, Kopf gleich breit', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await oeffnen(page, NEUN);
    const beste = await kasten(page, '.beste-antwort');
    const daneben = await kasten(page, '.gruppe.mit-bester .zu-dieser-antwort-spalte');
    expect(daneben.x).toBeGreaterThan(beste.x + beste.breite);
    expect(Math.abs(daneben.breite - beste.breite)).toBeLessThanOrEqual(2);
    const besteTitel = await kasten(page, '.gruppe.mit-bester .beste-ueberschrift');
    const kastenTitel = await kasten(page, '.gruppe.mit-bester .zda-titel');
    expect(Math.abs(kastenTitel.y - besteTitel.y)).toBeLessThanOrEqual(2);

    // Darunter ueber die volle Breite (Maintainer 18.11.): vier offene Antworten zu zweit, in
    // Rangfolge zeilenweise; die lange dritte (oben rechts) zieht ihre Nachbarin nicht mit
    const offene = page.locator('.gruppe.mit-bester .offene-karten app-beitragskarte');
    await expect(offene).toHaveCount(4);
    await expect(offene.locator('.kopieren-knopf')).toHaveCount(4);
    await expect(offene.locator('.aufklapp-knopf')).toHaveCount(0);
    await expect(offene.locator('.karte-titel')).toHaveText(['n-2', 'n-3', 'n-4', 'n-5'].map((id) => `[e2e-mock] commentary ${id}`));
    const o = await Promise.all([0, 1, 2, 3].map(async (i) => (await offene.nth(i).boundingBox())!));
    expect(Math.round(o[0].x)).toBe(beste.x);
    expect(o[0].y).toBeGreaterThan(beste.y + 10);
    expect(o[1].x).toBeGreaterThan(o[0].x + o[0].width);
    expect(Math.abs(o[1].y - o[0].y)).toBeLessThanOrEqual(2);
    expect(o[1].height).toBeGreaterThan(o[0].height + 50);
    expect(Math.round(o[2].x)).toBe(beste.x);
    expect(o[2].y).toBeGreaterThan(o[1].y + o[1].height - 2);
    expect(Math.abs(o[3].y - o[2].y)).toBeLessThanOrEqual(2);

    // Erst danach die eingeklappten, ebenfalls zu zweit auf einer Zeile
    const karten = page.locator('.gruppe.mit-bester .eingeklappte-karten').first().locator('app-beitragskarte');
    await expect(karten).toHaveCount(2);
    const links = await karten.nth(0).boundingBox();
    const rechts = await karten.nth(1).boundingBox();
    if (!links || !rechts) throw new Error('Zwei eingeklappte Karten erwartet');
    expect(Math.round(links.x)).toBe(beste.x);
    expect(rechts.x).toBeGreaterThan(links.x + links.width);
    expect(Math.abs(rechts.y - links.y)).toBeLessThanOrEqual(2);
    expect(links.y).toBeGreaterThan(o[3].y + o[3].height);
    await expect(page.locator('.gruppe.mit-bester .alle-zeigen')).toHaveText('Alle 4 weiteren Antworten zeigen');

    // Aufgeklappt waechst nur die eine Karte, nicht ihre Nachbarin
    const hoeheRechts = rechts.height;
    await karten.nth(0).locator('.aufklapp-knopf').click();
    await expect(karten.nth(0).locator('.karte-inhalt')).toBeVisible();
    expect(Math.round((await karten.nth(1).boundingBox())!.height)).toBe(Math.round(hoeheRechts));
    await karten.nth(0).locator('.aufklapp-knopf').click();
    // Die Seite ist mit neun Antworten laenger: nach oben, sonst misst y den Scroll mit
    await page.evaluate(() => window.scrollTo(0, 0));
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

  test('1280 px: aufgeklappte weniger passende Treffer zu zweit, "Nicht dabei?" auf Lesebreite', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const zweiAndere = [...kommentare, treffer('commentary', 'k-7', ANDERE, 0.84)];
    await oeffnen(page, {
      ...ANTWORT,
      commentary_search_results: zweiAndere,
      commentary_search_results_count: zweiAndere.length,
    });
    await page.locator('.weitere-umschalter').click();
    const beste = await kasten(page, '.beste-antwort');
    const karten = page.locator('.weitere-liste .eingeklappte-karten').first().locator('app-beitragskarte');
    const links = await karten.nth(0).boundingBox();
    const rechts = await karten.nth(1).boundingBox();
    if (!links || !rechts) throw new Error('Zwei weniger passende Karten erwartet');
    expect(Math.round(links.x)).toBe(beste.x);
    expect(rechts.x).toBeGreaterThan(links.x + links.width);
    expect(Math.abs(rechts.y - links.y)).toBeLessThanOrEqual(2);
    const nichtDabei = await kasten(page, '.nicht-dabei-unten');
    expect(nichtDabei.breite).toBeLessThanOrEqual(760);
  });

  test('1023 px: beste Antwort und weitere untereinander, ohne Kasten', async ({ page }) => {
    await page.setViewportSize({ width: 1023, height: 900 });
    await oeffnen(page, NEUN);
    await expect(page.locator('.gruppe.mit-bester')).toHaveCount(1);
    await expect(page.locator('app-zu-dieser-antwort')).toBeHidden();
    await expect(page.locator('.offene-karten')).toHaveCount(0);
    const beste = await kasten(page, '.beste-antwort');
    const weitere = await kasten(page, '.gruppe.mit-bester .eingeklappte-karten');
    expect(weitere.x).toBe(beste.x);
    expect(weitere.y).toBeGreaterThan(beste.y);
  });

  test('Breitenwechsel 1280 → 1023 → 1280: offene Antworten kommen und gehen, nichts doppelt', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await oeffnen(page, NEUN);
    const block = page.locator('.gruppe').first().locator('[data-typ="commentary"]');
    await expect(block.locator('.offene-karten app-beitragskarte')).toHaveCount(4);
    await page.setViewportSize({ width: 1023, height: 900 });
    await expect(block.locator('.offene-karten')).toHaveCount(0);
    await expect(block.locator('app-beitragskarte')).toHaveCount(3);
    await page.setViewportSize({ width: 1280, height: 900 });
    await expect(block.locator('.offene-karten app-beitragskarte')).toHaveCount(4);
    await expect(block.locator('app-beitragskarte')).toHaveCount(7);
  });
});
