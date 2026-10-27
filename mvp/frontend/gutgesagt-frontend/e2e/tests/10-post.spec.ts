import {
  TESTDATEN_PRAEFIX,
  einwurfAnlegen,
  einwurfStand,
  ergebnisKnoepfe,
  expect,
  lauf,
  speichernUndErgebnis,
  test,
} from './fixtures';

/** Der Post: verfassen, in der Suche als Post-Karte finden, aus dem Fangkorb ausformulieren (#297). */

test('Post verfassen: Formular, Ergebnisseite, in der Suche als Post-Karte', async ({ page, bild }) => {
  const kennung = lauf();
  const titel = `${TESTDATEN_PRAEFIX} Ein Reel erklärt die Wärmepumpe ohne Fachjargon ${kennung}`;

  await page.goto('/contribute');
  await expect.soft(page.locator('.post-card')).toContainText('Ein gelungener Beitrag aus einem sozialen Netzwerk, zum Teilen.');
  await page.locator('.post-card').click();
  await page.waitForURL(/\/workflow\/add-post$/);
  await expect(page.locator('app-add-post form')).toBeVisible();

  await test.step('Aufbau', async () => {
    await expect.soft(page.locator('.hilfe-emoji')).toHaveText('📣');
    await expect.soft(page.locator('.submit-hint')).toContainText('CC0');
    await expect.soft(page.locator('app-formular-leiste .submit-btn')).toContainText('Post speichern');
    const ueberlauf = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    expect.soft(ueberlauf, 'kein seitlicher Ueberlauf').toBe(false);
    await bild('100-post-leer');
  });

  await test.step('Ausfuellen: die Plattform folgt dem Link', async () => {
    await page.locator('input#url').fill(`https://www.instagram.com/p/e2e${kennung}/`);
    await expect.soft(page.locator('mat-select#platform')).toContainText('Instagram');
    await page.locator('input#author').fill('@e2e-klimaverein');
    await page.locator('textarea#title').fill(titel);
    await page.locator('textarea#text').fill(
      `${TESTDATEN_PRAEFIX} Zeigt in dreißig Sekunden, wie eine Wärmepumpe aus kalter Luft Wärme holt.`,
    );
    await expect.soft(page.locator('.preview-column')).toContainText('@e2e-klimaverein · Instagram');
    await bild('101-post-ausgefuellt', true);
  });

  const id = await speichernUndErgebnis(page);
  test.info().annotations.push({ type: 'Post-ID', description: id });
  expect.soft(new URL(page.url()).pathname).toBe(`/workflow/add-post/gespeichert/${id}`);
  await expect.soft(page.locator('.gespeichert-satz')).toHaveText('Dein Post ist gespeichert.');
  await expect.soft(page.locator('.gespeichert-karte')).toContainText(titel);
  expect.soft(await ergebnisKnoepfe(page)).toEqual(['Noch einen Post', 'Meine Beiträge']);
  await bild('102-post-ergebnis');

  await test.step('In der Suche als Post-Karte', async () => {
    await page.goto(`/result?searchQuery=${encodeURIComponent(titel)}`);
    const postTab = page.locator('.tab-post');
    await expect(postTab).toBeVisible({ timeout: 45_000 });
    await postTab.click();
    const karte = page.locator('.mobile-section .karte.typ-post', { hasText: titel });
    await expect(karte).toBeVisible();
    await expect.soft(karte).toContainText('@e2e-klimaverein · Instagram');
    // Drei Tabs (Kommentare, Hintergrund, Posts) passen in 360 px.
    const ueberlauf = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    expect.soft(ueberlauf, 'kein seitlicher Ueberlauf mit dem Post-Tab').toBe(false);
    await karte.scrollIntoViewIfNeeded();
    await bild('103-post-in-der-suche');
  });
});

test('Post aus dem Fangkorb: Typwahl, vorbelegt, Einwurf ausformuliert', async ({ page, bild }) => {
  const kennung = lauf();
  const link = `https://www.tiktok.com/@e2e/video/${kennung}`;
  const einwurf = await einwurfAnlegen(page, `${TESTDATEN_PRAEFIX} Einwurf P: guter Clip ${kennung}`, link);
  const satz = `${TESTDATEN_PRAEFIX} Ein Clip, der Tempo 30 mit Kinderaugen zeigt ${kennung}`;

  await page.goto(`/destillieren/${einwurf.id}`);
  await page.locator('#satz').fill(satz);
  await page.locator('.weiter').click();
  await expect(page.locator('section.typwahl')).toBeVisible();
  await page.locator('mat-radio-button.typ-post label').first().click();
  await bild('104-typwahl-post');
  await page.locator('.formular-oeffnen').click();
  await page.waitForURL(new RegExp(`/workflow/add-post\\?.*=${einwurf.id}`));

  await expect.soft(page.locator('textarea#title')).toHaveValue(satz);
  await expect.soft(page.locator('input#url')).toHaveValue(link);
  await expect.soft(page.locator('mat-select#platform')).toContainText('TikTok');
  await page.locator('input#author').fill('@e2e');
  await page.locator('textarea#text').fill(`${TESTDATEN_PRAEFIX} Kinder erzählen, wie sich die Straße mit Tempo 30 anfühlt.`);
  await bild('105-post-einwurf');

  const id = await speichernUndErgebnis(page);
  expect.soft(await ergebnisKnoepfe(page)).toEqual(['Nächster Einwurf', 'Zum Fangkorb', 'Meine Beiträge']);
  const stand = await einwurfStand(page, einwurf.id);
  expect.soft(stand.status).toBe('processed');
  expect.soft(stand.beitraege).toContain(id);
  await bild('106-post-ergebnis-fangkorb');
});
