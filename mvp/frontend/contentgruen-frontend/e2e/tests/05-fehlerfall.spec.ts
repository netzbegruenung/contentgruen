import { TESTDATEN_PRAEFIX, expect, kommentarAusfuellen, lauf, tastaturSchliessen, test } from './fixtures';

/** Weg 5: Speichern ohne Netz, dann "Erneut versuchen" - Eingaben bleiben, kein Duplikat. */
test('Fehlerfall: offline speichern, online erneut versuchen', async ({ page, context, bild }) => {
  const kennung = lauf();
  const titel = `${TESTDATEN_PRAEFIX} Offline gespeichert ${kennung}`;
  const text = `${TESTDATEN_PRAEFIX} Dieser Kommentar ging erst beim zweiten Versuch durch ${kennung}.`;

  await page.goto('/workflow/add-commentary');
  await kommentarAusfuellen(page, titel, text);
  await page.locator('.antwort-eingabe').fill(`${TESTDATEN_PRAEFIX} Offline-Aussage ${kennung}`);

  let anfragen = 0;
  page.on('request', (r) => {
    if (r.url().includes('/api/v1/commentary/addCommentary')) anfragen++;
  });

  await tastaturSchliessen(page);
  await context.setOffline(true);
  await page.locator('app-formular-leiste .submit-btn').click();
  await expect(page.locator('.speicher-fehler')).toBeVisible();
  await expect.soft(page.locator('textarea#title')).toHaveValue(titel);
  await expect.soft(page.locator('textarea#text')).toHaveValue(text);
  await expect.soft(page.locator('app-formular-leiste .submit-btn')).toContainText('Erneut versuchen');
  await bild('50-offline-fehler');

  await context.setOffline(false);
  await tastaturSchliessen(page);
  await page.locator('app-formular-leiste .submit-btn').click();
  await page.waitForURL(/\/gespeichert\//);
  await expect.soft(page.locator('.gespeichert-karte')).toContainText(titel);
  // Die Ergebnisseite zeigt die tatsaechlich verknuepfte Aussage - aus einem frueheren Lauf
  // kann das eine sehr aehnliche mit anderer Kennung sein.
  await expect.soft(page.locator('.gespeichert-aussage')).toContainText(`${TESTDATEN_PRAEFIX} Offline-Aussage`);
  await bild('51-nach-erneut-versuchen');

  // Duplikat: in "Meine Beitraege" genau einmal.
  const beitraege = await (await page.request.get('/api/v1/contribution/getContributionsOfUser?page=1&page_size=100')).json().catch(() => null);
  const treffer = beitraege?.results?.filter((b: any) => b.title === titel).length ?? null;
  test.info().annotations.push({ type: 'Anfragen addCommentary (online sichtbar)', description: String(anfragen) });
  test.info().annotations.push({ type: 'Treffer mit diesem Titel', description: String(treffer) });
  expect.soft(treffer).toBe(1);
});
