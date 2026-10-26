import { TESTDATEN_PRAEFIX, expect, ausfuellen, lauf, speichernUndErgebnis, test } from './fixtures';

/** aus der Suche ins Formular, Aussage vorbelegt, zurueck zur Suche. */
test('Suche: Beitrag ergaenzen und zurueck zur Suche', async ({ page, bild }) => {
  const kennung = lauf();
  const anfrage = `${TESTDATEN_PRAEFIX} Balkonkraftwerke sind nur Spielerei ${kennung}`;
  // Die Suche legt keine zweite Aussage an, wenn es schon eine sehr aehnliche gibt -
  // aus einem frueheren Lauf kann die Aussage also eine andere Kennung tragen.
  const aussageKern = `${TESTDATEN_PRAEFIX} Balkonkraftwerke sind nur Spielerei`;

  await page.goto(`/result?searchQuery=${encodeURIComponent(anfrage)}`);
  // Fertig ist die Suche, wenn Tabs, Karten oder der Leerzustand stehen.
  await expect(page.locator('.mobile-tab-bar, .mobile-empty-state, app-kartenliste').first()).toBeVisible({
    timeout: 45_000,
  });
  await bild('30-suche');

  await test.step('Beitrag ergaenzen', async () => {
    // Mobil mit Treffern: dezent unter dem Suchband und unter der Liste; ohne Treffer im Leerzustand.
    const unterSuchband = page.locator('.mobile-ergaenzen-kopf button');
    const unterListe = page.locator('.mobile-ergaenzen button, .mobile-action-buttons button').first();
    await expect.soft(unterListe).toBeVisible();
    if (await unterSuchband.isVisible()) {
      await expect.soft(unterSuchband).toHaveText(/Eigenen Kommentar ergänzen/);
    }
    await unterListe.scrollIntoViewIfNeeded();
    await bild('30c-suche-ergaenzen-360');
    const knopf = unterListe;
    await knopf.click();
    await page.waitForURL(/\/workflow\/add-commentary\?/);
    test.info().annotations.push({ type: 'Formular-Adresse', description: new URL(page.url()).search });
    // Vorbelegt: als gewaehlte Aussage (mit ID) oder als Text im Feld.
    const vorbelegt =
      (await page.locator('.gewaehlt-karte .karte-titel').textContent().catch(() => null)) ??
      (await page.locator('.antwort-eingabe').inputValue().catch(() => ''));
    expect.soft(vorbelegt?.trim()).toContain(aussageKern);
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
    await expect.soft(page.locator('.gespeichert-aussage')).toContainText(aussageKern);
    const knoepfe = await page.locator('.gespeichert-knoepfe > *').allTextContents();
    expect.soft(knoepfe.map((k) => k.trim())).toEqual(['Zurück zur Suche', 'Meine Beiträge']);
    await bild('32-ergebnis-suche');

    await page.locator('.zur-suche').click();
    await page.waitForURL(/\/result\?/);
    expect.soft(new URL(page.url()).searchParams.get('searchQuery')).toBe(anfrage);
    await bild('33-zurueck-zur-suche');
  });

  await test.step('Zurueck (System und Pfeil) von der Ergebnisseite', async () => {
    await page.goBack();
    await page.waitForURL(/\/gespeichert\//);
    await page.goBack();
    await page.waitForTimeout(1500);
    const nachZurueck = new URL(page.url());
    test.info().annotations.push({ type: 'suche: System-Zurueck', description: nachZurueck.pathname + nachZurueck.search });
    expect.soft(nachZurueck.pathname).not.toMatch(/\/workflow\/add-commentary$/);
    await bild('73-suche-system-zurueck');

    await page.goForward();
    await page.waitForURL(/\/gespeichert\//);
    await page.locator('.back-button').click();
    await page.waitForTimeout(1500);
    const nachPfeil = new URL(page.url());
    test.info().annotations.push({ type: 'suche: Pfeil', description: nachPfeil.pathname + nachPfeil.search });
    expect.soft(nachPfeil.pathname).toBe('/result');
    expect.soft(nachPfeil.searchParams.get('searchQuery')).toBe(anfrage);
    await bild('74-suche-pfeil');
  });
});
