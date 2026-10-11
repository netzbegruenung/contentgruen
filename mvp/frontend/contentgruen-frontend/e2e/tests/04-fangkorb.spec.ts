import { Page } from '@playwright/test';
import {
  Einwurf,
  TESTDATEN_PRAEFIX,
  einwurfAnlegen,
  expect,
  lauf,
  speichernUndErgebnis,
  test,
} from './fixtures';

async function status(page: Page, id: string) {
  const einwurf = await (await page.request.get(`/api/v1/rawinput/${id}`)).json();
  return { status: einwurf.status, links: (einwurf.links ?? []).map((l: any) => l.content_id) };
}

/** Vom Destillieren ueber die Typwahl ins Formular, speichern; liefert die Kommentar-ID. */
async function ausformulieren(
  page: Page,
  bild: (name: string, ganz?: boolean) => Promise<void>,
  einwurf: Einwurf,
  satz: string,
  nr: number,
): Promise<string> {
  await expect(page.locator('#satz')).toBeVisible();
  await page.locator('#satz').fill(satz);
  await page.locator('.weiter').click();
  await expect(page.locator('section.typwahl')).toBeVisible();
  await expect.soft(page.locator('section.typwahl .einwurf-kopf .rohling-kopfsatz')).toHaveText(`„${satz}“`);
  await expect.soft(page.locator('.einwurf-link')).toHaveCount(0);
  await bild(`4${nr}a-typwahl`);
  await page.locator('mat-radio-button.typ-commentary label').first().click();
  await page.locator('.formular-oeffnen').click();
  await page.waitForURL(/\/workflow\/add-commentary\?.*rohinput=/);

  await expect.soft(page.locator('.einwurf-kopf .rohling-kopf')).toBeVisible();
  await expect.soft(page.locator('.einwurf-kopf .rohling-titel')).toHaveText(einwurf.hinweis);
  await expect.soft(page.locator('.einwurf-kopf .rohling-kopfsatz')).toHaveText(`„${satz}“`);
  await expect.soft(page.locator('.einwurf-kopf .rohling-linkzeile')).toBeVisible();
  await expect.soft(page.locator('textarea#title')).toHaveValue(satz);
  await expect.soft(page.locator('.reference-item')).toHaveCount(1);
  await expect.soft(page.locator('.reference-item')).toContainText(einwurf.link);
  await bild(`4${nr}b-formular-rohling`);

  await page
    .locator('textarea#text')
    .fill(`${TESTDATEN_PRAEFIX} Aus dem Fangkorb ausformuliert: ${satz} – mit Beleg im Link.`);
  const id = await speichernUndErgebnis(page);
  await expect.soft(page.locator('.markieren-fehlgeschlagen')).toHaveCount(0);
  const knoepfe = await page.locator('.gespeichert-knoepfe > *').allTextContents();
  expect.soft(knoepfe.map((k) => k.trim())).toEqual(['Nächster Einwurf', 'Zum Fangkorb', 'Meine Beiträge']);
  expect.soft(new URL(page.url()).searchParams.get('rohinput')).toBe(einwurf.id);
  await bild(`4${nr}c-ergebnis-fangkorb`);

  const stand = await status(page, einwurf.id);
  expect.soft(stand.status, `Status Einwurf ${nr}`).toBe('processed');
  expect.soft(stand.links, `content_id Einwurf ${nr}`).toContain(id);
  test.info().annotations.push({ type: `Einwurf ${nr}`, description: `${einwurf.id} -> ${stand.status}, Kommentar ${id}` });
  return id;
}

/**
 * Fremde offene Einwuerfe fuer die Runde zurueckstellen - wie "Spaeter", ohne sie zu
 * aendern. Die Runde lebt im RawInputService (nur im Speicher), also danach keine
 * Neuladung mehr, bis der letzte "Naechste Einwurf" geprueft ist.
 */
async function fremdeZurueckstellen(page: Page, eigene: string[]): Promise<string[]> {
  const liste = await (await page.request.get('/api/v1/rawinput/getRawInputs?page=1&page_size=100')).json();
  const fremde: string[] = liste.results
    .filter((e: any) => (e.status === 'open' || e.status === 'in_progress') && !e.own_draft && !eigene.includes(e.id))
    .map((e: any) => e.id);
  await page.evaluate((ids) => {
    const komponente = (window as any).ng.getComponent(document.querySelector('app-raw-input-list'));
    for (const id of ids) komponente.rawInputService.zurueckstellen(id);
  }, fremde);
  return fremde;
}

test('Fangkorb: zwei Einwuerfe ausformulieren, naechster Einwurf, Erledigt', async ({ page, bild }) => {
  const kennung = lauf();
  const erster = await einwurfAnlegen(
    page,
    `${TESTDATEN_PRAEFIX} Einwurf 1: Leserbrief gegen Windräder ${kennung}`,
    `https://example.org/4b-test/einwurf-1-${kennung}`,
  );
  const zweiter = await einwurfAnlegen(
    page,
    `${TESTDATEN_PRAEFIX} Einwurf 2: Video zu Wärmepumpen ${kennung}`,
    `https://example.org/4b-test/einwurf-2-${kennung}`,
  );
  await bild('40-einwerfen');

  await test.step('Einwurf 1 aus dem Fangkorb', async () => {
    await page.goto('/fangkorb');
    const karte = page.locator('article.karte--rohling', { hasText: erster.hinweis });
    await expect(karte).toBeVisible();
    const fremde = await fremdeZurueckstellen(page, [erster.id, zweiter.id]);
    test.info().annotations.push({ type: 'fremde offene Einwuerfe fuer die Runde zurueckgestellt', description: String(fremde.length) });
    await expect.soft(page.locator('.tab.aktiv')).toHaveCSS('color', 'rgb(255, 255, 255)');
    await bild('41-fangkorb');
    await karte.locator('.rohling-primaer').click();
    await page.waitForURL(new RegExp(`/destillieren/${erster.id}`));
    await ausformulieren(page, bild, erster, `${TESTDATEN_PRAEFIX} Windräder schützen Vögel besser als Kohle ${kennung}`, 1);
  });

  await test.step('System-Zurueck von der Ergebnisseite, ohne neu zu laden', async () => {
    // Davor liegt die Typwahl des jetzt verarbeiteten Einwurfs: mit Hinweis, nicht umgeleitet.
    await page.goBack();
    await page.waitForURL(/\/destillieren\//);
    await page.waitForTimeout(1500);
    const nachZurueck = new URL(page.url());
    test.info().annotations.push({ type: 'fangkorb: System-Zurueck', description: nachZurueck.pathname + nachZurueck.search });
    expect.soft(nachZurueck.pathname).toBe(`/destillieren/${erster.id}`);
    await expect.soft(page.locator('.schon-entstanden')).toContainText('Aus diesem Einwurf ist schon ein Beitrag entstanden');
    await expect.soft(page.locator('section.typwahl .typen')).toBeVisible();
    await expect.soft(page.locator('.schon-entstanden .beitrag-ansehen')).toBeVisible();
    await bild('75-fangkorb-system-zurueck');
    await page.goForward();
    await page.waitForURL(/\/gespeichert\//);
    await expect(page.locator('.naechster-einwurf')).toBeVisible();
  });

  await test.step('Naechster Einwurf oeffnet den zweiten', async () => {
    await page.locator('.naechster-einwurf').click();
    await page.waitForURL(/\/destillieren\/[0-9a-f-]{36}/);
    const geoeffnet = new URL(page.url()).pathname.split('/').pop();
    test.info().annotations.push({ type: 'Naechster nach Einwurf 1', description: geoeffnet! });
    expect.soft(geoeffnet).toBe(zweiter.id);
    await bild('45-naechster-einwurf');
    await ausformulieren(page, bild, zweiter, `${TESTDATEN_PRAEFIX} Wärmepumpen rechnen sich auch im Altbau ${kennung}`, 2);
  });

  const ergebnis = page.url();

  await test.step('Naechster Einwurf beim letzten: Fangkorb, Tab Erledigt', async () => {
    await page.locator('.naechster-einwurf').click();
    await page.waitForURL(/\/(destillieren\/[0-9a-f-]{36}|fangkorb)/, { timeout: 20_000 });
    const ziel = new URL(page.url()).pathname;
    test.info().annotations.push({ type: 'Naechster nach Einwurf 2', description: ziel });
    expect.soft(ziel).toBe('/fangkorb');
    await expect.soft(page.locator('.tab.aktiv')).toContainText('Erledigt');
    await expect.soft(page.locator('article.karte--rohling', { hasText: zweiter.hinweis })).toBeVisible();
    await bild('46-naechster-nach-letztem');
  });

  await test.step('Pfeil von der Ergebnisseite', async () => {
    await page.goto(ergebnis);
    await expect(page.locator('.gespeichert-satz')).toBeVisible();
    await page.locator('.back-button').click();
    await page.waitForTimeout(1500);
    const nachPfeil = new URL(page.url()).pathname;
    test.info().annotations.push({ type: 'fangkorb: Pfeil', description: nachPfeil });
    expect.soft(nachPfeil).toBe('/fangkorb');
    await bild('76-fangkorb-pfeil');
  });

  await test.step('Zum Fangkorb', async () => {
    await page.goto(ergebnis);
    await page.locator('.zum-fangkorb').click();
    await page.waitForURL(/\/fangkorb/);
    await expect.soft(page.locator('.tab.aktiv')).toContainText('Erledigt');
    await bild('47-fangkorb-erledigt');
  });

  await test.step('Weiter destillieren -> Typwahl -> Formular -> System-Zurueck -> Typwahl mit Hinweis', async () => {
    await page.goto('/fangkorb');
    const karte = page.locator('article.karte--rohling', { hasText: zweiter.hinweis });
    await expect(karte).toBeVisible();
    await karte.locator('.rohling-menue').click();
    await page.getByRole('menuitem', { name: 'Weiter destillieren' }).click();
    await page.waitForURL(new RegExp(`/destillieren/${zweiter.id}`));
    await page.locator('.weiter').click();
    await expect(page.locator('section.typwahl')).toBeVisible();
    await expect.soft(page.locator('.schon-entstanden')).toBeVisible();
    await page.locator('.formular-oeffnen').click();
    await page.waitForURL(/\/workflow\/add-commentary\?.*rohinput=/);
    await page.goBack();
    await page.waitForURL(new RegExp(`/destillieren/${zweiter.id}`));
    await expect.soft(page.locator('section.typwahl')).toBeVisible();
    await expect.soft(page.locator('.schon-entstanden')).toContainText('Aus diesem Einwurf ist schon ein Beitrag entstanden');
    await bild('48-weiter-destillieren-zurueck');
  });
});
