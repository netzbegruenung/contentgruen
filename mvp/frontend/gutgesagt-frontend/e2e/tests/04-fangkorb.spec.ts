import { Page } from '@playwright/test';
import {
  Bild,
  Einwurf,
  TESTDATEN_PRAEFIX,
  einwurfAnlegen,
  einwurfStand,
  ergebnisKnoepfe,
  expect,
  lauf,
  speichernUndErgebnis,
  test,
} from './fixtures';

/**
 * Destillieren (Satz) und Ausformulieren als Kommentar (Typwahl, Formular), speichern;
 * liefert die Kommentar-ID.
 */
async function ausformulieren(page: Page, bild: Bild, einwurf: Einwurf, satz: string, nr: number): Promise<string> {
  await expect(page.locator('#satz')).toBeVisible();
  await page.locator('#satz').fill(satz);
  await page.locator('.weiter').click();
  await expect(page.locator('section.typwahl')).toBeVisible();
  await expect.soft(page.locator('section.typwahl .einwurf-kopf .einwurf-kopfsatz')).toHaveText(`„${satz}“`);
  await bild(`4${nr}a-typwahl`);
  await page.locator('mat-radio-button.typ-commentary label').first().click();
  await page.locator('.formular-oeffnen').click();
  await page.waitForURL(new RegExp(`/workflow/add-commentary\\?.*=${einwurf.id}`));

  // Ueber dem Formular derselbe Kopf: Hinweis, Link, Satz; Titel und Herkunft vorbelegt.
  const kopf = page.locator('.einwurf-kopf');
  await expect.soft(kopf.locator('.einwurf-titel')).toHaveText(einwurf.hinweis);
  await expect.soft(kopf.locator('.einwurf-kopfsatz')).toHaveText(`„${satz}“`);
  await expect.soft(kopf.locator('.einwurf-linkzeile')).toBeVisible();
  await expect.soft(page.locator('textarea#title')).toHaveValue(satz);
  await expect.soft(page.locator('.reference-item')).toHaveCount(1);
  await expect.soft(page.locator('.reference-item')).toContainText(einwurf.link);
  await bild(`4${nr}b-formular-einwurf`);

  await page
    .locator('textarea#text')
    .fill(`${TESTDATEN_PRAEFIX} Aus dem Fangkorb ausformuliert: ${satz} – mit Beleg im Link.`);
  const id = await speichernUndErgebnis(page);
  await expect.soft(page.locator('.verknuepfen-fehlgeschlagen')).toHaveCount(0);
  expect.soft(await ergebnisKnoepfe(page)).toEqual(['Nächster Einwurf', 'Zum Fangkorb', 'Meine Beiträge']);
  expect.soft(new URL(page.url()).search).toContain(einwurf.id);
  await bild(`4${nr}c-ergebnis-fangkorb`);

  const stand = await einwurfStand(page, einwurf.id);
  expect.soft(stand.status, `Stufe Einwurf ${nr}`).toBe('processed');
  expect.soft(stand.beitraege, `Verknuepfung Einwurf ${nr}`).toContain(id);
  test.info().annotations.push({ type: `Einwurf ${nr}`, description: `${einwurf.id} -> ${stand.status}, Kommentar ${id}` });
  return id;
}

test('Fangkorb: zwei Einwuerfe ausformulieren, naechster Einwurf, Ausformuliert', async ({ page, bild }) => {
  const kennung = lauf();
  const erster = await einwurfAnlegen(
    page,
    `${TESTDATEN_PRAEFIX} Einwurf 1: Leserbrief gegen Windräder ${kennung}`,
    `https://example.org/e2e-test/einwurf-1-${kennung}`,
  );
  const zweiter = await einwurfAnlegen(
    page,
    `${TESTDATEN_PRAEFIX} Einwurf 2: Video zu Wärmepumpen ${kennung}`,
    `https://example.org/e2e-test/einwurf-2-${kennung}`,
  );
  await bild('40-einwerfen');

  await test.step('Einwurf 1 aus dem Fangkorb destillieren', async () => {
    await page.goto('/fangkorb');
    await expect.soft(page.locator('.tab.aktiv .tab-wort')).toHaveText('Destillieren');
    await expect.soft(page.locator('.tab.aktiv')).toHaveCSS('color', 'rgb(255, 255, 255)');
    const karte = page.locator('app-beitragskarte', { hasText: erster.hinweis });
    await expect(karte).toBeVisible();
    await bild('41-fangkorb');
    await karte.locator('.einwurf-primaer').click();
    await page.waitForURL(new RegExp(`/destillieren/${erster.id}`));
    await ausformulieren(page, bild, erster, `${TESTDATEN_PRAEFIX} Windräder schützen Vögel besser als Kohle ${kennung}`, 1);
  });

  await test.step('System-Zurueck von der Ergebnisseite: Typwahl mit Hinweis', async () => {
    // Davor liegt die Typwahl des jetzt ausformulierten Einwurfs: mit Hinweis, nicht umgeleitet.
    await page.goBack();
    await page.waitForURL(new RegExp(`/destillieren/${erster.id}`));
    await expect.soft(page.locator('.schon-verknuepft')).toContainText('Zu diesem Einwurf gibt es schon einen Beitrag');
    await expect.soft(page.locator('section.typwahl .typen')).toBeVisible();
    await expect.soft(page.locator('.schon-verknuepft .beitrag-ansehen')).toBeVisible();
    await bild('75-fangkorb-system-zurueck');
    await page.goForward();
    await page.waitForURL(/\/gespeichert\//);
    await expect(page.locator('.naechster-einwurf')).toBeVisible();
  });

  await test.step('Naechster Einwurf oeffnet den zweiten', async () => {
    // Die Reihenfolge kommt vom Server: eigene zuerst, dann die neuesten.
    await page.locator('.naechster-einwurf').click();
    await page.waitForURL(/\/destillieren\/[0-9a-f-]{36}/);
    expect.soft(new URL(page.url()).pathname.split('/').pop()).toBe(zweiter.id);
    await bild('45-naechster-einwurf');
    await ausformulieren(page, bild, zweiter, `${TESTDATEN_PRAEFIX} Wärmepumpen rechnen sich auch im Altbau ${kennung}`, 2);
  });

  const ergebnis = page.url();

  await test.step('Naechster Einwurf nach dem zweiten: Ende der Runde im Fangkorb', async () => {
    // Andere offene Einwuerfe (Seed, fruehere Laeufe) kommen vorher dran: "Spaeter"
    // ohne Satz stellt sie fuer diese Runde zurueck, ohne sie zu aendern.
    await page.locator('.naechster-einwurf').click();
    let zurueckgestellt = 0;
    for (;;) {
      await page.waitForURL(/\/(destillieren\/[0-9a-f-]{36}|fangkorb)/, { timeout: 20_000 });
      const ziel = new URL(page.url()).pathname;
      if (ziel === '/fangkorb') break;
      expect(ziel).not.toBe(`/destillieren/${erster.id}`);
      expect(ziel).not.toBe(`/destillieren/${zweiter.id}`);
      expect(zurueckgestellt, 'mehr andere offene Einwuerfe als erwartet').toBeLessThan(50);
      await expect(page.locator('#satz')).toHaveValue('');
      await page.locator('.spaeter').click();
      await page.waitForURL((url) => url.pathname !== ziel);
      zurueckgestellt++;
    }
    test.info().annotations.push({ type: 'andere offene Einwuerfe zurueckgestellt', description: String(zurueckgestellt) });
    // Ohne Zurueckstellen geht es in den Tab mit dem Ergebnis; sonst in den des
    // zuletzt zurueckgestellten.
    if (zurueckgestellt === 0) {
      await expect.soft(page.locator('.tab.aktiv .tab-wort')).toHaveText('Ausformuliert');
      await expect.soft(page.locator('app-beitragskarte', { hasText: zweiter.hinweis })).toBeVisible();
    }
    await bild('46-naechster-nach-zweitem');
  });

  await test.step('Pfeil von der Ergebnisseite', async () => {
    await page.goto(ergebnis);
    await expect(page.locator('.gespeichert-satz')).toBeVisible();
    await page.locator('.back-button').click();
    await page.waitForURL(/\/fangkorb/);
    await bild('76-fangkorb-pfeil');
  });

  await test.step('Zum Fangkorb: Tab Ausformuliert', async () => {
    await page.goto(ergebnis);
    await page.locator('.zum-fangkorb').click();
    await page.waitForURL(/\/fangkorb/);
    await expect.soft(page.locator('.tab.aktiv .tab-wort')).toHaveText('Ausformuliert');
    await expect.soft(page.locator('app-beitragskarte', { hasText: zweiter.hinweis })).toBeVisible();
    await bild('47-fangkorb-ausformuliert');
  });

  await test.step('Weiter destillieren, Formular, System-Zurueck: Typwahl mit Hinweis', async () => {
    const karte = page.locator('app-beitragskarte', { hasText: zweiter.hinweis });
    await expect(karte).toBeVisible();
    await karte.locator('.einwurf-menue').click();
    await page.getByRole('menuitem', { name: 'Weiter destillieren' }).click();
    await page.waitForURL(new RegExp(`/destillieren/${zweiter.id}`));
    await page.locator('.weiter').click();
    await expect(page.locator('section.typwahl')).toBeVisible();
    await expect.soft(page.locator('.schon-verknuepft')).toBeVisible();
    await page.locator('.formular-oeffnen').click();
    await page.waitForURL(new RegExp(`/workflow/add-commentary\\?.*=${zweiter.id}`));
    await page.goBack();
    await page.waitForURL(new RegExp(`/destillieren/${zweiter.id}`));
    await expect.soft(page.locator('section.typwahl')).toBeVisible();
    await expect.soft(page.locator('.schon-verknuepft')).toContainText('Zu diesem Einwurf gibt es schon einen Beitrag');
    await bild('48-weiter-destillieren-zurueck');
  });
});
