import {
  TESTDATEN_PRAEFIX,
  aufErgebnisWarten,
  ausfuellen,
  expect,
  lauf,
  tastaturSchliessen,
  test,
} from './fixtures';

/** Speichern ohne Netz, dann "Erneut versuchen" - Eingaben bleiben, nicht doppelt gespeichert. */
test('Fehlerfall: offline speichern, online erneut versuchen', async ({ page, context, bild }) => {
  const kennung = lauf();
  const titel = `${TESTDATEN_PRAEFIX} Ein zweiter Versuch rettet den Kommentar ${kennung}`;
  const text = `${TESTDATEN_PRAEFIX} Dieser Kommentar ging erst beim zweiten Versuch durch ${kennung}.`;

  await page.goto('/workflow/add-commentary');
  await ausfuellen(page, titel, text);
  await page.locator('.antwort-eingabe').fill(`${TESTDATEN_PRAEFIX} Offline-Aussage ${kennung}`);

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
  const seit = Date.now();
  await page.locator('app-formular-leiste .submit-btn').click();
  await aufErgebnisWarten(page, seit);
  await expect.soft(page.locator('.gespeichert-karte')).toContainText(titel);
  // Die Ergebnisseite zeigt die tatsaechlich verknuepfte Aussage - aus einem frueheren Lauf
  // kann das eine sehr aehnliche mit anderer Kennung sein.
  await expect.soft(page.locator('.gespeichert-aussage')).toContainText(`${TESTDATEN_PRAEFIX} Offline-Aussage`);
  await bild('51-nach-erneut-versuchen');

  // Nicht doppelt gespeichert: in "Meine Beitraege" genau einmal.
  const beitraege = await (await page.request.get('/api/v1/contribution/getContributionsOfUser?page=1&page_size=100')).json().catch(() => null);
  const gespeichert = beitraege?.results?.filter((b: any) => b.title === titel) ?? null;
  test.info().annotations.push({ type: 'Treffer mit diesem Titel', description: String(gespeichert?.length ?? null) });
  expect.soft(gespeichert?.length ?? null).toBe(1);
  // Neue Beitraege sind sofort sichtbar (GLOSSARY.md, "Zustaende eines Beitrags").
  expect.soft(gespeichert?.[0]?.status, 'Zustand des neuen Beitrags').toBe('visible');
});
