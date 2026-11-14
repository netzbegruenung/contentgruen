import { request as anfrageKontext } from '@playwright/test';
import { TESTDATEN_PRAEFIX, ausfuellen, expect, lauf, speichernUndErgebnis, test, zurueck } from './fixtures';

const WER = ['Kraniche', 'Feldhamster', 'Imkerinnen', 'Fährleute', 'Schornsteinfeger', 'Seilbahnen', 'Tuba-Orchester', 'Kleingärtner', 'Leuchttürme', 'Hebammen', 'Zirkuspferde', 'Glockengießer'];
const WAS = ['meiden', 'verteuern', 'verdrängen', 'überwachen', 'verstopfen', 'beschallen', 'vergraulen', 'vermessen', 'besteuern', 'verzaubern'];
const WEN = ['Moorlandschaften', 'Dorfbäckereien', 'Bergseen', 'Hafenkräne', 'Turmuhren', 'Wanderdünen', 'Lesecafés', 'Mühlbäche', 'Kegelbahnen', 'Sternwarten'];
const WO = ['im Spreewald', 'im Allgäu', 'im Emsland', 'im Vogtland', 'an der Mosel', 'in der Rhön', 'auf Föhr', 'am Kaiserstuhl'];

function zufallsSatz(): string {
  const eins = <T>(liste: T[]): T => liste[Math.floor(Math.random() * liste.length)];
  return Math.random() < 0.5
    ? `${eins(WER)} ${eins(WAS)} heimlich die ${eins(WEN)} ${eins(WO)}`
    : `${eins(WO)} ${eins(WAS)} die ${eins(WER)} jetzt sogar die ${eins(WEN)}`;
}

/**
 * Die Antwort landet an der Aussage: aus "Hier fehlt eine Antwort" und aus einer
 * Suche mit erkannter Aussage (Kopfband).
 *
 * Eine Aussage aus Suchen ohne Treffer kommt erst ab zwei Personen auf die Liste. Die
 * zwei Personen sind das Testkonto und ein Besucher ohne Sitzung (eigenes
 * Tagespseudonym); beide suchen ueber die API. Auf einem Stand mit Vormoderation (#664)
 * muesste ein Admin die Suchanfrage vorher freigeben.
 */
test('Hier fehlt eine Antwort: Antworten, gespeichert, die Aussage verschwindet', async ({ page, baseURL, bild }) => {
  const kennung = lauf();
  let aussage = '';

  await test.step('Zwei Personen suchen ohne Treffer', async () => {
    let aussageId: string | null = null;
    const treffer = async (wer: typeof page.request, text: string): Promise<number> => {
      const antwort = await wer.post('/api/v1/search/searchByText', { data: { query_text: text, limit: 10 } });
      expect(antwort.status()).toBe(200);
      const daten = await antwort.json();
      // Ohne Aussage (Rate-Limit beim Anlegen) zaehlt die Suche nicht.
      expect(daten.statement_id, 'Aussage der Suche').toBeTruthy();
      aussageId ??= daten.statement_id;
      expect(daten.statement_id, 'beide Suchen landen auf derselben Aussage').toBe(aussageId);
      return ['commentary', 'generictext', 'post', 'image']
        .map((typ) => (daten[`${typ}_search_results`] ?? []).length)
        .reduce((a, b) => a + b, 0);
    };
    // Ein Satz, zu dem der Bestand nichts hat, je Lauf ein anderer: Sonst faende die
    // Suche die beantwortete Aussage eines Vorlaufs. Trifft er doch etwas, der naechste.
    // Ohne TESTDATEN_PRAEFIX und ohne die Kennung des Laufs: Schon das Praefix macht zwei
    // Aussagen so aehnlich, dass jeder Kommentar eines Vorlaufs ein Treffer waere, und
    // Ziffernfolgen wirken ebenso.
    for (let versuch = 0; versuch < 8 && !aussage; versuch++) {
      const kandidat = zufallsSatz();
      aussageId = null;
      if ((await treffer(page.request, kandidat)) === 0) {
        aussage = kandidat;
      }
    }
    // Trifft der Bestand jeden Zufallssatz (viele Vorlaeufe), laesst sich keine Luecke bauen.
    test.skip(!aussage, 'kein Satz ohne Treffer gefunden; in einem frischen Stack wiederholen');
    // Ohne Sitzung: newContext uebernaehme sonst die gespeicherte des Projekts.
    const besucher = await anfrageKontext.newContext({ baseURL, storageState: { cookies: [], origins: [] } });
    expect(await treffer(besucher, aussage)).toBe(0);
    await besucher.dispose();
  });

  const karte = () => page.getByTestId('unbeantwortete-aussage').filter({ hasText: aussage });

  await test.step('Die Aussage steht in "Hier fehlt eine Antwort"', async () => {
    await page.goto('/hier-fehlt-eine-antwort');
    await expect(karte()).toHaveCount(1, { timeout: 30_000 });
    await expect(karte().locator('.gesucht')).toHaveText('2 Personen suchten das ohne Treffer');
    await bild('80-hier-fehlt-vorher');
  });

  await test.step('Antworten: Die Aussage ist vorgewaehlt', async () => {
    await karte().locator('a.antworten').click();
    await page.waitForURL(/\/workflow\/add-commentary\?/);
    expect(new URL(page.url()).searchParams.get('aussage')).toMatch(/^[0-9a-f-]{36}$/);
    await expect(page.locator('.gewaehlt-karte .karte-titel')).toHaveText(aussage, { timeout: 15_000 });
    await bild('81-hier-fehlt-formular');
  });

  await test.step('Speichern: verknuepft mit der Aussage', async () => {
    await ausfuellen(
      page,
      `${TESTDATEN_PRAEFIX} Dafür gibt es keinen einzigen Beleg ${kennung}`,
      `${TESTDATEN_PRAEFIX} Wer so etwas behauptet, sollte eine Quelle nennen – bisher gibt es keine Zählung, die das zeigt.`,
    );
    await speichernUndErgebnis(page);
    await expect(page.locator('.gespeichert-aussage')).toContainText(aussage);
    await bild('82-hier-fehlt-gespeichert');
  });

  await test.step('Zurueck: Die Aussage ist nicht mehr in der Liste', async () => {
    const nachPfeil = await zurueck(page, 'pfeil');
    expect(nachPfeil.pathname).toBe('/hier-fehlt-eine-antwort');
    await expect(page.getByTestId('unbeantwortete-aussage').first().or(page.locator('.leer, .leerer-zustand').first())).toBeVisible({
      timeout: 30_000,
    });
    await expect(karte()).toHaveCount(0);
    await bild('83-hier-fehlt-nachher');
  });
});

test('Suche mit erkannter Aussage: Antworten waehlt sie vor', async ({ page, bild }) => {
  // Aus den Seed-Daten: Die Suche findet Kommentare zu "Die Grünen wollen mir meine
  // Heizung verbieten!", ist aber nicht derselbe Wortlaut und legt deshalb eine eigene
  // Aussage an, die getById Nicht-Admins nicht ausliefert (#436). Vorher bot das
  // Formular dann nur den Suchtext neben der gefundenen Aussage an.
  const anfrage = 'Die Grünen wollen uns die Heizung verbieten';

  await page.goto(`/result?searchQuery=${encodeURIComponent(anfrage)}`);
  const gefunden = page.locator('.kopfband-aussage');
  await expect(gefunden).toBeVisible({ timeout: 45_000 });
  const erkannt = (await gefunden.textContent())!.trim().replace(/^„|“$/g, '');
  test.skip(erkannt === anfrage, 'Die Suche landet auf derselben Aussage; nichts zu unterscheiden');
  await bild('84-suche-gefunden-zu');

  await page.locator('.typ-leiste .ergaenzen-link', { hasText: 'Antworten' }).click();
  await page.waitForURL(/\/workflow\/add-commentary\?/);
  await expect(page.locator('.gewaehlt-karte .karte-titel')).toHaveText(erkannt, { timeout: 15_000 });
  expect(new URL(page.url()).searchParams.get('searchQuery')).toBe(anfrage);
  await bild('85-suche-formular-erkannt');
});
