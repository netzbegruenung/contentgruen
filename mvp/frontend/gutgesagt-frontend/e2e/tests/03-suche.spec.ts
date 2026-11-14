import { TESTDATEN_PRAEFIX, ergebnisKnoepfe, expect, ausfuellen, lauf, speichernUndErgebnis, test, zurueck } from './fixtures';

/** aus der Suche ins Formular, Aussage vorbelegt, zurueck zur Suche. */
test('Suche: Beitrag ergaenzen und zurueck zur Suche', async ({ page, bild }) => {
  const kennung = lauf();
  const anfrage = `${TESTDATEN_PRAEFIX} Balkonkraftwerke sind nur Spielerei ${kennung}`;
  // Die Suche legt keine zweite Aussage an, wenn es schon eine sehr aehnliche gibt -
  // aus einem frueheren Lauf kann die Aussage also eine andere Kennung tragen.
  const aussageKern = `${TESTDATEN_PRAEFIX} Balkonkraftwerke sind nur Spielerei`;

  await page.goto(`/result?searchQuery=${encodeURIComponent(anfrage)}`);
  // Fertig ist die Suche, wenn Chips, Karten oder der Leerzustand stehen.
  await expect(page.locator('.typ-chips, .unified-empty-state, app-kartenliste').first()).toBeVisible({
    timeout: 45_000,
  });
  await bild('30-suche');
  // Hat die Suche Treffer zu einer erkannten Aussage (Kopfband), waehlt "Antworten"
  // diese vor, nicht die eigene Aussage der Suche - auch wenn ein Vorlauf sie lieferte.
  const gefundenZu = page.locator('.kopfband-aussage');
  const erwartet = (await gefundenZu.isVisible())
    ? (await gefundenZu.textContent())!.trim().replace(/^„|“$/g, '')
    : aussageKern;

  await test.step('Beitrag ergaenzen', async () => {
    // Mit Treffern: dezent neben den Chips und unter der Liste; ohne Treffer im Leerzustand.
    const unterSuchband = page.locator('.typ-leiste .ergaenzen-link');
    const unterListe = page.locator('.nicht-dabei-unten .neu-anlegen-knopf button, .unified-empty-state .action-buttons-top button').first();
    await expect.soft(unterListe).toBeVisible();
    if (await unterSuchband.isVisible()) {
      await expect.soft(unterSuchband).toHaveText(/Antworten/);
    }
    await unterListe.scrollIntoViewIfNeeded();
    await bild('30c-suche-ergaenzen-360');
    const knopf = unterListe;
    await knopf.click();
    await page.waitForURL(/\/workflow\/add-commentary\?/);
    test.info().annotations.push({ type: 'Formular-Adresse', description: new URL(page.url()).search });
    // Vorbelegt: als gewaehlte Aussage (mit ID) oder als Text im Feld.
    // Das Template wechselt dabei vom Feld zur Karte: gelesen wird, was gerade steht.
    const vorbelegt = page.locator('.gewaehlt-karte .karte-titel').or(page.locator('.antwort-eingabe')).first();
    await expect
      .poll(() => vorbelegt.evaluate((el) => (el instanceof HTMLTextAreaElement ? el.value : (el.textContent ?? '')).trim()))
      .toContain(erwartet);
    await bild('31-formular-vorbelegt');
  });

  await test.step('Speichern, Ergebnisseite, zurueck zur Suche', async () => {
    await ausfuellen(
      page,
      `${TESTDATEN_PRAEFIX} Balkonkraftwerke sparen spürbar Strom ${kennung}`,
      `${TESTDATEN_PRAEFIX} Ein Balkonkraftwerk deckt die Grundlast von Kühlschrank und Router – das merkt man auf der Rechnung.`,
    );
    const id = await speichernUndErgebnis(page);
    test.info().annotations.push({ type: 'Kommentar-ID', description: id });
    await expect.soft(page.locator('.gespeichert-aussage')).toContainText(erwartet);
    // Je nach Aussage stehen dazwischen weitere ("Zur Aussage", "Link kopieren").
    const knoepfe = await ergebnisKnoepfe(page);
    expect.soft(knoepfe[0]).toBe('Zurück zur Suche');
    expect.soft(knoepfe.at(-1)).toBe('Meine Beiträge');
    await bild('32-ergebnis-suche');

    await page.locator('.zur-suche').click();
    await page.waitForURL(/\/result\?/);
    expect.soft(new URL(page.url()).searchParams.get('searchQuery')).toBe(anfrage);
    await bild('33-zurueck-zur-suche');
  });

  await test.step('Zurueck (System und Pfeil) von der Ergebnisseite', async () => {
    await page.goBack();
    await page.waitForURL(/\/gespeichert\//);
    const nachZurueck = await zurueck(page, 'system');
    test.info().annotations.push({ type: 'suche: System-Zurueck', description: nachZurueck.pathname + nachZurueck.search });
    expect.soft(nachZurueck.pathname).not.toMatch(/\/workflow\/add-commentary$/);
    await bild('73-suche-system-zurueck');

    await page.goForward();
    await page.waitForURL(/\/gespeichert\//);
    const nachPfeil = await zurueck(page, 'pfeil');
    test.info().annotations.push({ type: 'suche: Pfeil', description: nachPfeil.pathname + nachPfeil.search });
    expect.soft(nachPfeil.pathname).toBe('/result');
    expect.soft(nachPfeil.searchParams.get('searchQuery')).toBe(anfrage);
    await bild('74-suche-pfeil');
  });
});
