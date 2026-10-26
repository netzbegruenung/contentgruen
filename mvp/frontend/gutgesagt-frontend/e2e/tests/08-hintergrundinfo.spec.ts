import {
  TESTDATEN_PRAEFIX,
  aufErgebnisWarten,
  ausfuellen,
  einwurfAnlegen,
  einwurfStand,
  ergebnisKnoepfe,
  expect,
  lauf,
  speichernUndErgebnis,
  tastaturSchliessen,
  test,
} from './fixtures';

/** Die Hintergrundinfo hat dieselbe Anatomie wie der Kommentar. */

test('Hintergrundinfo verfassen: Aufbau, neue Aussage, Ergebnisseite', async ({ page, bild }) => {
  const kennung = lauf();
  const aussage = `${TESTDATEN_PRAEFIX} Balkonsolar lohnt sich nie ${kennung}`;
  const titel = `${TESTDATEN_PRAEFIX} Ein Balkonkraftwerk amortisiert sich in fünf bis acht Jahren ${kennung}`;

  await page.goto('/contribute');
  await page.locator('.generictext-card').click();
  await expect(page.locator('app-add-generictext form')).toBeVisible();

  await test.step('Aufbau', async () => {
    await expect.soft(page.locator('.content-type-indicator')).toHaveCount(0);
    await expect.soft(page.locator('mat-slide-toggle')).toHaveCount(0);
    await expect.soft(page.locator('.hilfe-zeile')).toHaveText('Knapp und überprüfbar – am besten mit Beleg.');
    await expect.soft(page.locator('.hilfe-emoji')).toHaveText('📄');
    await page.locator('.erklaerung-umschalter').click();
    await expect.soft(page.locator('.hilfe-panel')).toContainText('Meinung ohne Beleg (→ Kommentar)');
    await expect.soft(page.locator('.hilfe-panel')).toContainText('Fremde Texte übernehmen – in eigenen Worten zusammenfassen (CC0)');
    await bild('80-hintergrundinfo-hilfe');
    await page.locator('.erklaerung-umschalter').click();
    await expect.soft(page.locator('.herkunft-satz')).toHaveText('Zahlen und Fakten mit Herkunft sind glaubwürdiger.');
    await expect.soft(page.locator('.preview-column app-beitragskarte')).toBeVisible();
    await expect.soft(page.locator('app-formular-leiste .submit-btn')).toContainText('Hintergrundinfo speichern');
    await bild('81-hintergrundinfo-leer');
  });

  await test.step('Text: 2000er-Zaehler, kein X/Bluesky, waechst mit', async () => {
    await page.locator('textarea#text').fill(`${TESTDATEN_PRAEFIX} ${'Zahlen. '.repeat(40)}`.slice(0, 300));
    await expect.soft(page.locator('mat-hint', { hasText: '300 / 2000' })).toBeVisible();
    await expect.soft(page.locator('.plattform-hinweis')).toHaveCount(0);
  });

  await test.step('Neue Aussage, speichern, Ergebnisseite', async () => {
    await page.locator('.antwort-eingabe').fill(aussage);
    await expect(page.locator('.neue-aussage')).toBeVisible();
    await page.locator('.neue-aussage').click();
    await expect.soft(page.locator('.neu-marke')).toHaveText('neu');
    await ausfuellen(
      page,
      titel,
      `${TESTDATEN_PRAEFIX} Bei 800 Watt und 30 Cent je Kilowattstunde spart ein Balkonkraftwerk rund 150 Euro im Jahr.`,
    );
    await page.locator('.herkunft-link').click();
    await page.locator('.reference-source-input').fill(`${TESTDATEN_PRAEFIX} Herkunft: Verbraucherzentrale, Rechner Balkonkraftwerk`);
    await page.locator('.reference-source-input').press('Enter');
    await expect.soft(page.locator('.reference-item')).toHaveCount(1);
    await bild('82-hintergrundinfo-ausgefuellt');

    const id = await speichernUndErgebnis(page);
    test.info().annotations.push({ type: 'Hintergrundinfo-ID', description: id });
    await expect.soft(page.locator('.gespeichert-satz')).toHaveText('Deine Hintergrundinfo ist gespeichert.');
    // Die tatsaechlich verknuepfte Aussage (das Backend nimmt ab Score 0,9 eine vorhandene).
    await expect.soft(page.locator('.gespeichert-aussage .karte-titel')).toContainText(TESTDATEN_PRAEFIX);
    test.info().annotations.push({ type: 'verknuepfte Aussage', description: (await page.locator('.gespeichert-aussage .karte-titel').textContent()) ?? '' });
    await expect.soft(page.locator('.gespeichert-karte')).toContainText(titel);
    await expect.soft(page.locator('.gespeichert-karte .karte-meta')).toContainText('vor wenigen Sekunden');
    expect.soft(await ergebnisKnoepfe(page)).toEqual(['Noch eine Hintergrundinfo', 'Meine Beiträge']);
    await bild('83-hintergrundinfo-ergebnis');
  });
});

test('Hintergrundinfo aus dem Fangkorb: Kopfband, vorbelegt, Ergebnisseite', async ({ page, bild }) => {
  const kennung = lauf();
  const einwurf = await einwurfAnlegen(
    page,
    `${TESTDATEN_PRAEFIX} Einwurf H: Studie zu Balkonsolar ${kennung}`,
    `https://example.org/e2e-test/einwurf-h-${kennung}`,
  );
  const satz = `${TESTDATEN_PRAEFIX} Balkonsolar spart einem Haushalt rund 150 Euro im Jahr ${kennung}`;

  await page.goto(`/destillieren/${einwurf.id}`);
  await page.locator('#satz').fill(satz);
  await page.locator('.weiter').click();
  await expect(page.locator('section.typwahl')).toBeVisible();
  await expect.soft(page.locator('section.typwahl')).toContainText('Fakten und Zahlen, die eine Antwort stützen.');
  await page.locator('mat-radio-button.typ-generictext label').first().click();
  await bild('84-typwahl-hintergrundinfo');
  await page.locator('.formular-oeffnen').click();
  await page.waitForURL(new RegExp(`/workflow/add-generictext\\?.*=${einwurf.id}`));

  await expect.soft(page.locator('.einwurf-kopf .einwurf-kopfsatz')).toHaveText(`„${satz}“`);
  await expect.soft(page.locator('textarea#title')).toHaveValue(satz);
  await expect.soft(page.locator('.reference-item')).toContainText(einwurf.link);
  await bild('85-hintergrundinfo-einwurf');

  await page.locator('textarea#text').fill(`${TESTDATEN_PRAEFIX} Laut Studie im Link rechnet sich die Anlage nach sechs Jahren.`);
  await speichernUndErgebnis(page);
  expect.soft(await ergebnisKnoepfe(page)).toEqual(['Nächster Einwurf', 'Zum Fangkorb', 'Meine Beiträge']);
  expect.soft((await einwurfStand(page, einwurf.id)).status).toBe('processed');
  await bild('86-hintergrundinfo-ergebnis-fangkorb');
});

test('Hintergrundinfo: offline speichern, Erneut versuchen behaelt die Eingaben', async ({ page, context, bild }) => {
  const kennung = lauf();
  const titel = `${TESTDATEN_PRAEFIX} Ein Funkloch kostet keine Hintergrundinfo ${kennung}`;
  await page.goto('/workflow/add-generictext');
  await ausfuellen(page, titel, `${TESTDATEN_PRAEFIX} Erst der zweite Versuch geht durch ${kennung}.`);
  await tastaturSchliessen(page);
  await context.setOffline(true);
  await page.locator('app-formular-leiste .submit-btn').click();
  await expect(page.locator('app-formular-leiste .leiste-fehler')).toBeVisible();
  await expect.soft(page.locator('textarea#title')).toHaveValue(titel);
  await bild('87-hintergrundinfo-offline');
  await context.setOffline(false);
  const seit = Date.now();
  await page.locator('app-formular-leiste .submit-btn').click();
  await aufErgebnisWarten(page, seit);
  expect.soft(new URL(page.url()).pathname).toMatch(/^\/workflow\/add-generictext\/gespeichert\//);
  await expect.soft(page.locator('.gespeichert-karte')).toContainText(titel);
});
