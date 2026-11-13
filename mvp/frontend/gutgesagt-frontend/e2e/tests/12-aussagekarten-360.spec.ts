import { expect, test } from './fixtures';

/**
 * Aussagekarten auf "Hier fehlt eine Antwort" bei 360 px: eine sehr lange Aussage mit einem
 * Wort ohne Umbruchstelle sprengt die Seite nicht, und "Ganz lesen" klappt sie per Tastatur auf.
 * Legt nichts an: Die lange Aussage wird nur in die Antwort des Servers eingesetzt.
 */
const LANG =
  'Windräder töten jedes Jahr Millionen Vögel, ' +
  'Donaudampfschifffahrtsgesellschaftskapitänsmützenabzeichenhersteller '.repeat(3) +
  'und überhaupt ist die ganze Energiewende viel zu teuer, zu laut und zu hoch. '.repeat(6);

test('Hier fehlt eine Antwort: lange Aussage ohne Querscrollen, "Ganz lesen" per Tastatur', async ({ page }) => {
  await page.route('**/api/v1/statement/unbeantwortet**', async (route) => {
    const antwort = await route.fetch();
    const daten = await antwort.json();
    const liste = daten.aussagen ?? daten;
    liste.unshift({ statement_id: 'e2e-lang', statement_text: LANG, personen_ohne_treffer: 3, themen: [] });
    await route.fulfill({ response: antwort, json: daten });
  });
  await page.goto('/hier-fehlt-eine-antwort');

  const karte = page.locator('app-aussagekarte').first();
  await expect(karte).toBeVisible({ timeout: 20_000 });
  const { breit, sichtbar } = await page.locator('main').evaluate((element) => ({
    breit: element.scrollWidth,
    sichtbar: element.clientWidth,
  }));
  expect(breit).toBeLessThanOrEqual(sichtbar);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);

  const titel = karte.locator('.aussagekarte-titel');
  await expect(titel).toHaveClass(/aussagekarte-titel--zu/);
  const hoeheZu = (await titel.boundingBox())!.height;

  const knopf = karte.getByRole('button', { name: 'Ganz lesen' });
  await expect(knopf).toHaveAttribute('aria-expanded', 'false');
  await knopf.focus();
  await page.keyboard.press('Enter');
  await expect(karte.getByRole('button', { name: 'Weniger zeigen' })).toHaveAttribute('aria-expanded', 'true');

  // Aufgeklappt: ganz zu sehen, hoeher als vorher, und noch immer kein Querscrollen
  await expect(titel).not.toHaveClass(/aussagekarte-titel--zu/);
  expect((await titel.boundingBox())!.height).toBeGreaterThan(hoeheZu);
  const offen = await page.locator('main').evaluate((element) => ({
    breit: element.scrollWidth,
    sichtbar: element.clientWidth,
  }));
  expect(offen.breit).toBeLessThanOrEqual(offen.sichtbar);
});
