import { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Darstellung bei 360 px, hell und dunkel: Befunde der Designrunde vom 12.11.
 * Liest nur, legt nichts an.
 */

/** Kontrast zweier CSS-Farben `rgb(...)` nach WCAG 2.1. */
function kontrast(vorne: string, hinten: string): number {
  const leuchtdichte = (farbe: string): number => {
    const [r, g, b] = farbe.match(/[\d.]+/g)!.slice(0, 3).map((wert) => {
      const kanal = Number(wert) / 255;
      return kanal <= 0.03928 ? kanal / 12.92 : ((kanal + 0.055) / 1.055) ** 2.4;
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const [hell, dunkel] = [leuchtdichte(vorne), leuchtdichte(hinten)].sort((a, b) => b - a);
  return (hell + 0.05) / (dunkel + 0.05);
}

/**
 * Schriftfarbe und die erste deckende Hintergrundfarbe darunter (Element oder Vorfahr).
 * Nur fuer deckende Hintergruende und sRGB-Ausgabe (`rgb(...)`) gedacht: Halbtransparente
 * Flaechen, Verlaeufe, Bilder und andere Farbraeume misst sie nicht richtig.
 */
async function farben(page: Page, selektor: string): Promise<{ vorne: string; hinten: string }> {
  return page.locator(selektor).first().evaluate((element) => {
    let ebene: Element | null = element;
    let hinten = 'rgb(255, 255, 255)';
    while (ebene) {
      const farbe = getComputedStyle(ebene).backgroundColor;
      if (farbe && farbe !== 'transparent' && !farbe.startsWith('rgba(0, 0, 0, 0)')) {
        hinten = farbe;
        break;
      }
      ebene = ebene.parentElement;
    }
    return { vorne: getComputedStyle(element).color, hinten };
  });
}

for (const modus of ['light', 'dark'] as const) {
  test.describe(`Darstellung 360 px, ${modus}`, () => {
    // Ohne Animation: Material blendet das Haekchen ein, gemessen wird nicht mitten im Uebergang.
    test.use({ colorScheme: modus, reducedMotion: 'reduce' });

    test('Kommentarformular: Zweck-Umschalter schneidet nichts ab', async ({ page }) => {
      await page.goto('/workflow/add-commentary');
      const gruppe = page.locator('.zweck-wahl');
      const segmente = gruppe.locator('mat-button-toggle');
      const knoepfe = gruppe.locator('.mat-button-toggle-button');
      await expect(knoepfe).toHaveCount(2);
      // Beide Zustaende: Das gewaehlte Segment bekommt das Haekchen und damit weniger Platz.
      for (const gewaehlt of [0, 1]) {
        await knoepfe.nth(gewaehlt).click();
        await expect(segmente.nth(gewaehlt)).toHaveClass(/mat-button-toggle-checked/);
        // Die Gruppe schneidet mit overflow: hidden ab; ein zu breites rechtes Segment
        // faellt nur am rechten Rand auf, nicht an scrollWidth.
        const rechterRand = (await gruppe.boundingBox())!.x + (await gruppe.boundingBox())!.width;
        for (const knopf of await knoepfe.all()) {
          const name = `${await knopf.textContent()}`.trim();
          const { breit, sichtbar } = await knopf.evaluate((element) => ({
            breit: element.scrollWidth,
            sichtbar: element.clientWidth,
          }));
          expect.soft(breit, name).toBeLessThanOrEqual(sichtbar);
          const box = (await knopf.boundingBox())!;
          expect.soft(box.x + box.width, `${name}: rechter Rand`).toBeLessThanOrEqual(rechterRand + 0.5);
        }
      }
    });

    test('Kommentarformular: langer Link bei „Antwort auf“ sprengt die Seite nicht', async ({ page }) => {
      await page.goto('/workflow/add-commentary');
      await page
        .locator('.antwort-eingabe')
        .fill('Siehe https://www.example.org/ein/sehr/langer/pfad/ohne/jede/moeglichkeit/umzubrechen?parameter=wert');
      await expect(page.locator('.neue-aussage')).toBeVisible();
      const { breit, sichtbar } = await page.locator('main').evaluate((element) => ({
        breit: element.scrollWidth,
        sichtbar: element.clientWidth,
      }));
      expect(breit).toBeLessThanOrEqual(sichtbar);
    });

    test('Gewählter Themen-Chip ist lesbar (AA)', async ({ page }) => {
      await page.goto('/hier-fehlt-eine-antwort');
      await expect(page.locator('.thema-chip.gewaehlt').first()).toBeVisible();
      const { vorne, hinten } = await farben(page, '.thema-chip.gewaehlt');
      expect(kontrast(vorne, hinten)).toBeGreaterThanOrEqual(4.5);
    });

    test('Beispiel-Link auf dem gelben Band ist lesbar (AA)', async ({ page }) => {
      await page.goto('/search');
      await expect(page.locator('.beispiel-link')).toBeVisible();
      const { vorne, hinten } = await farben(page, '.beispiel-link');
      expect(kontrast(vorne, hinten)).toBeGreaterThanOrEqual(4.5);
    });

    test('Hinweisbox im Datenschutz ist lesbar (AA)', async ({ page }) => {
      await page.goto('/datenschutz');
      await expect(page.locator('.warning-box p').first()).toBeVisible();
      const { vorne, hinten } = await farben(page, '.warning-box p');
      expect(kontrast(vorne, hinten)).toBeGreaterThanOrEqual(4.5);
    });
  });
}
