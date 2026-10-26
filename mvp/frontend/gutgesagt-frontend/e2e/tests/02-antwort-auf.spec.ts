import { TESTDATEN_PRAEFIX, expect, ausfuellen, lauf, speichernUndErgebnis, test } from './fixtures';

/** Antwort auf - Vorschlag waehlen und entfernen, neue Aussage anlegen, speichern. */
test('Antwort auf: Vorschlag, neue Aussage, Ergebnisseite, Suche', async ({ page, bild }) => {
  const kennung = lauf();
  const neueAussage = `${TESTDATEN_PRAEFIX} Quallen regieren heimlich die Stadtwerke ${kennung}`;
  const titel = `${TESTDATEN_PRAEFIX} Quallen haben keine Mehrheit im Stadtrat ${kennung}`;

  await page.goto('/contribute');
  await page.locator('.commentary-card').click();
  await expect(page.locator('app-add-commentary form')).toBeVisible();

  await test.step('Vorschlag uebernehmen und wieder entfernen', async () => {
    await page.locator('.antwort-eingabe').fill('Windräder töten Vögel');
    await expect(page.locator('.vorschlag').first()).toBeVisible();
    await bild('20-vorschlag');
    const vorschlag = (await page.locator('.vorschlag .vorschlag-text').first().textContent())!.trim();
    await page.locator('.vorschlag').first().click();
    await expect.soft(page.locator('.gewaehlt-karte .karte-titel')).toHaveText(vorschlag);
    await expect.soft(page.locator('.neu-marke')).toHaveCount(0);
    await bild('21-vorschlag-uebernommen');
    await page.locator('.antwort-auf .entfernen').click();
    await expect.soft(page.locator('.antwort-eingabe')).toHaveValue('');
    await bild('22-vorschlag-entfernt');
  });

  await test.step('Unsinnstext als neue Aussage', async () => {
    await page.locator('.antwort-eingabe').fill('Quallen');
    await expect.soft(page.locator('.antwort-auf mat-hint')).toContainText('Mindestens 10 Zeichen');
    await expect.soft(page.locator('app-formular-leiste .submit-btn')).toBeDisabled();
    await page.locator('.antwort-eingabe').fill(neueAussage);
    await expect.soft(page.locator('.antwort-auf mat-hint')).toContainText('Wird als neue Aussage angelegt.');
    await expect(page.locator('.neue-aussage')).toBeVisible();
    await bild('23-neue-aussage-option');
    await page.locator('.neue-aussage').click();
    await expect.soft(page.locator('.neu-marke')).toHaveText('neu');
    await expect.soft(page.locator('.gewaehlt-karte .karte-titel')).toHaveText(neueAussage);
    await bild('24-neue-aussage-marke');
  });

  let id = '';
  await test.step('Speichern, Ergebnisseite mit Antwort auf', async () => {
    await ausfuellen(
      page,
      titel,
      `${TESTDATEN_PRAEFIX} Wer Quallen fürchtet, sollte erst in den Haushaltsplan schauen – da steht nichts davon.`,
    );
    id = await speichernUndErgebnis(page);
    // Die tatsaechlich verknuepfte Aussage: ohne frueheren Lauf die neue, sonst eine sehr aehnliche.
    await expect.soft(page.locator('.gespeichert-aussage')).toContainText(`${TESTDATEN_PRAEFIX} Quallen regieren heimlich die Stadtwerke`);
    test.info().annotations.push({ type: 'verknuepfte Aussage', description: (await page.locator('.gespeichert-aussage .karte-titel').textContent()) ?? '' });
    await expect.soft(page.locator('.verknuepfung-fehlgeschlagen')).toHaveCount(0);
    await expect.soft(page.locator('.gespeichert-karte')).toContainText(titel);
    const knoepfe = await page.locator('.gespeichert-knoepfe > *').allTextContents();
    expect.soft(knoepfe.map((k) => k.trim())).toEqual(['Noch einen Kommentar', 'Meine Beiträge']);
    test.info().annotations.push({ type: 'Kommentar-ID', description: id });
    await bild('25-ergebnis-verfassen');
  });

  await test.step('Noch einen Kommentar, dann Zurueck (System und Pfeil)', async () => {
    await page.locator('.noch-einer').click();
    await page.waitForURL(/\/workflow\/add-commentary$/);
    await expect.soft(page.locator('textarea#title')).toHaveValue('');
    await bild('26-noch-einer');

    // System-Zurueck: zur Ergebnisseite, dann weiter zurueck - nie ins ausgefuellte Formular.
    await page.goBack();
    await page.waitForURL(/\/gespeichert\//);
    await bild('70-verfassen-zurueck-ergebnis');
    await page.goBack();
    await page.waitForTimeout(1500);
    const nachZurueck = new URL(page.url()).pathname;
    test.info().annotations.push({ type: 'verfassen: System-Zurueck von der Ergebnisseite', description: nachZurueck });
    expect.soft(nachZurueck, 'kein Ruecksprung ins Formular').not.toMatch(/\/workflow\/add-commentary$/);
    await bild('71-verfassen-system-zurueck');

    await page.goForward();
    await page.waitForURL(/\/gespeichert\//);
    await page.locator('.back-button').click();
    await page.waitForTimeout(1500);
    const nachPfeil = new URL(page.url()).pathname;
    test.info().annotations.push({ type: 'verfassen: Pfeil von der Ergebnisseite', description: nachPfeil });
    expect.soft(nachPfeil).toBe('/contribute');
    await bild('72-verfassen-pfeil');
  });

  await test.step('Kommentar erscheint unter der neuen Aussage in der Suche', async () => {
    await page.goto(`/result?searchQuery=${encodeURIComponent(neueAussage)}`);
    await expect.soft(page.getByText(titel)).toBeVisible({ timeout: 20_000 });
    await bild('27-suche-neue-aussage', true);
  });
});
