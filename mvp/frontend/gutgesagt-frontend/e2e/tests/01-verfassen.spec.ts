import { TESTDATEN_PRAEFIX, expect, test } from './fixtures';

/** Kommentar verfassen ueber /contribute - Aufbau und Bedienung, ohne zu speichern. */
test('Verfassen: Aufbau und Bedienung des Kommentarformulars', async ({ page, bild }) => {
  await page.goto('/contribute');
  await bild('01-contribute');
  await page.locator('.commentary-card').click();
  await page.waitForURL(/\/workflow\/add-commentary/);
  await expect(page.locator('app-add-commentary form')).toBeVisible();

  await test.step('Aufbau ohne Typband und Schrittnummern', async () => {
    await expect.soft(page.locator('.content-type-indicator')).toHaveCount(0);
    await expect.soft(page.locator('.contributions-button')).toHaveCount(0);
    await expect.soft(page.locator('.hilfe-emoji')).toHaveText('💬');
    await expect.soft(page.locator('.hilfe-zeile')).toHaveText('So formuliert, dass auch eine unentschiedene Nachbarin mitgeht.');
    await expect.soft(page.locator('.step-indicator')).toHaveCount(0);
    await expect.soft(page.locator('.mobile-header-title')).toHaveText('Kommentar');
    await bild('02-formular-leer');
  });

  await test.step('Hilfe-? auf und zu', async () => {
    await expect.soft(page.locator('.hilfe-panel')).toHaveCount(0);
    await page.locator('.erklaerung-umschalter').click();
    await expect.soft(page.locator('.hilfe-panel')).toContainText('Nimmt die Sorge hinter der Aussage ernst');
    await bild('03-hilfe-offen');
    await page.locator('.erklaerung-umschalter').click();
    await expect.soft(page.locator('.hilfe-panel')).toHaveCount(0);
  });

  await test.step('Platzhalter nicht abgeschnitten, Leiste weg bei Fokus', async () => {
    await page.locator('textarea#title').focus();
    const platzhalter = await page.$$eval('input[placeholder], textarea[placeholder]', (felder) =>
      felder.map((f) => {
        const el = f as HTMLInputElement;
        const c = document.createElement('canvas').getContext('2d')!;
        const st = getComputedStyle(el);
        c.font = st.font;
        return {
          text: el.placeholder,
          noetig: Math.ceil(c.measureText(el.placeholder).width),
          platz: Math.floor(el.clientWidth - parseFloat(st.paddingLeft) - parseFloat(st.paddingRight)),
        };
      }),
    );
    for (const p of platzhalter) {
      expect.soft(p.noetig, `Platzhalter "${p.text}"`).toBeLessThanOrEqual(p.platz);
    }
    await expect.soft(page.locator('app-formular-leiste .leiste')).toBeHidden();
    await bild('04-platzhalter-fokus');
  });

  await test.step('Zaehler, X/Bluesky-Hinweis, Autosize', async () => {
    await page.locator('textarea#title').fill(`${TESTDATEN_PRAEFIX} Windräder sind besser als ihr Ruf`);
    const satz = 'Windräder liefern günstigen Strom und schützen das Klima. ';
    const text250 = `${TESTDATEN_PRAEFIX} ${satz.repeat(6)}`.slice(0, 250);
    await page.locator('textarea#text').fill(text250);
    const hoehe250 = await page.locator('textarea#text').evaluate((el) => (el as HTMLElement).offsetHeight);
    await expect.soft(page.locator('mat-hint', { hasText: '250 / 500' })).toBeVisible();
    await expect.soft(page.locator('.plattform-hinweis')).toHaveText('passt auf X/Bluesky');
    await bild('05-text-250');

    await page.locator('textarea#text').fill(`${TESTDATEN_PRAEFIX} ${satz.repeat(8)}`.slice(0, 300));
    await expect.soft(page.locator('.plattform-hinweis')).toHaveText('zu lang für X/Bluesky');
    await expect.soft(page.locator('mat-form-field:has(#text) mat-error')).toHaveCount(0);
    const hoehe300 = await page.locator('textarea#text').evaluate((el) => (el as HTMLElement).offsetHeight);
    expect.soft(hoehe300, 'Textfeld waechst mit').toBeGreaterThan(hoehe250);
    await page.locator('textarea#text').blur();
    await bild('06-text-300');
  });

  await test.step('Herkunft kompakt hinzufuegen und loeschen', async () => {
    await page.locator('.herkunft-link').click();
    await expect(page.locator('.reference-input-container.kompakt')).toBeVisible();
    await page.locator('.reference-source-input').fill(`${TESTDATEN_PRAEFIX} Beispiel-Herkunft Windkraftstudie`);
    await page.locator('.reference-source-input').press('Enter');
    await expect.soft(page.locator('.reference-item')).toHaveCount(1);
    await expect.soft(page.locator('.reference-count')).toHaveCount(0);
    await expect.soft(page.locator('.status-message.info')).toHaveCount(0);
    await bild('07-herkunft');
    await page.locator('.entfernen-klein').click();
    await expect.soft(page.locator('.reference-item')).toHaveCount(0);
    await bild('08-herkunft-geloescht');
  });

  await test.step('Vorschau ohne Neu-Zeichen, 0× und Info-Icon', async () => {
    await page.locator('.preview-column').scrollIntoViewIfNeeded();
    await expect.soft(page.locator('.preview-column .badge-neu')).toHaveCount(0);
    await expect.soft(page.locator('.preview-column .badge-nutzung')).toHaveCount(0);
    await expect.soft(page.locator('.preview-header mat-icon')).toHaveCount(0);
    await expect.soft(page.locator('.preview-column .karte-meta')).toHaveText('Von: Du');
    await bild('09-vorschau');
  });

  await test.step('Leiste fest unten, beim Tippen weg', async () => {
    await page.locator('textarea#text').blur();
    await page.evaluate(() => window.scrollTo(0, 0));
    const leiste = page.locator('app-formular-leiste .leiste');
    await expect.soft(leiste).toBeVisible();
    const lage = await leiste.evaluate((el) => ({
      position: getComputedStyle(el).position,
      unten: Math.round(el.getBoundingClientRect().bottom),
      hoehe: Math.round(el.getBoundingClientRect().height),
      fenster: innerHeight,
    }));
    expect.soft(lage.position).toBe('fixed');
    expect.soft(lage.unten).toBe(lage.fenster);
    test.info().annotations.push({ type: 'Leistenhoehe', description: `${lage.hoehe}px` });
    await bild('10-leiste');
    await page.locator('textarea#text').focus();
    await expect.soft(leiste).toBeHidden();
    await bild('11-leiste-beim-tippen');
    await page.locator('textarea#text').blur();
  });

  await test.step('Zuruecksetzen mit Rueckfrage', async () => {
    await page.locator('.zuruecksetzen').click();
    const dialog = page.locator('mat-dialog-container');
    await expect(dialog).toContainText('Formular zurücksetzen?');
    // Viewport-Bild erst nach der Oeffnungs-Animation
    await page.waitForTimeout(400);
    await bild('12-zuruecksetzen-rueckfrage');
    await dialog.getByRole('button', { name: 'Abbrechen' }).click();
    await expect.soft(page.locator('textarea#title')).toHaveValue(`${TESTDATEN_PRAEFIX} Windräder sind besser als ihr Ruf`);
    await page.locator('.zuruecksetzen').click();
    await dialog.locator('.bestaetigen').click();
    await expect.soft(page.locator('textarea#title')).toHaveValue('');
    await expect.soft(page.locator('textarea#text')).toHaveValue('');
    await expect(dialog).toHaveCount(0);
    // Die Seite darf nach dem Dialog nicht seitlich verschoben sein (mat-sidenav-container).
    const verschoben = await page.evaluate(() => document.querySelector('mat-sidenav-container')!.scrollLeft);
    expect.soft(verschoben, 'Seite nach dem Dialog seitlich verschoben').toBe(0);
    await bild('13-zurueckgesetzt');
  });
});
