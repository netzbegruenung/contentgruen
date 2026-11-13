import { Locator } from '@playwright/test';
import { farben, kontrast } from './darstellung';
import { expect, test } from './fixtures';

/**
 * Kanten und Fluchten auf 360, 390 und 1280 px, hell und dunkel: Kann-Befunde der
 * Designrunde vom 12.11. Liest nur. Die Suche nutzt das Beispiel der Startseite, zu dem
 * der Seed schon eine Aussage hat.
 */

/** Linke und rechte Kante in px, gerundet. */
async function kanten(element: Locator): Promise<[number, number]> {
  const box = (await element.boundingBox())!;
  return [Math.round(box.x), Math.round(box.x + box.width)];
}

const DESKTOP = { viewport: { width: 1280, height: 900 }, isMobile: false, hasTouch: false, deviceScaleFactor: 1 };
const ANONYM = { cookies: [], origins: [] };

for (const modus of ['light', 'dark'] as const) {
  test.describe(`Darstellung Kanten, ${modus}`, () => {
    test.use({ colorScheme: modus, reducedMotion: 'reduce' });

    test.describe('1280 px', () => {
      test.use(DESKTOP);

      test('Suchergebnisse: Raster mittig im Rahmen', async ({ page }) => {
        await page.goto(`/result?searchQuery=${encodeURIComponent('Windräder töten die Vögel!')}`);
        const raster = page.locator('.kartenliste--spalten').first();
        await expect(raster.locator('app-beitragskarte').first()).toBeVisible({ timeout: 45_000 });
        const { links, rechts } = await raster.evaluate((liste) => {
          const stil = getComputedStyle(liste);
          const rahmen = liste.getBoundingClientRect();
          const karten = [...liste.querySelectorAll(':scope > li .karte')].map((k) => k.getBoundingClientRect());
          return {
            links: Math.min(...karten.map((k) => k.left)) - rahmen.left - parseFloat(stil.paddingLeft),
            rechts: rahmen.right - parseFloat(stil.paddingRight) - Math.max(...karten.map((k) => k.right)),
          };
        });
        // Nur bei voller erster Reihe gleich; mit einer Karte steht sie in der linken Spalte.
        const spalten = (await raster.evaluate((l) => getComputedStyle(l).gridTemplateColumns)).split(' ').length;
        test.skip((await raster.locator(':scope > li').count()) < spalten, 'zu wenige Treffer für eine volle Reihe');
        expect(Math.abs(links - rechts)).toBeLessThanOrEqual(1);
      });

      test('Beitrag verfassen: Rundgang-Band fluchtet mit Kopf und Kacheln', async ({ page }) => {
        // Das Angebot erscheint nur, solange es nicht beantwortet ist.
        await page.addInitScript(() => localStorage.removeItem('gutgesagt-mitmachen-angeboten'));
        await page.goto('/contribute');
        const band = page.locator('app-rundgang-band .band');
        await expect(band).toBeVisible();
        const kacheln = page.locator('.typ-zeilen');
        const [kachelnLinks] = await kanten(kacheln.locator('.typ-zeile').first());
        const kachelnRechts = Math.max(
          ...(await Promise.all((await kacheln.locator('.typ-zeile').all()).map(async (z) => (await kanten(z))[1]))),
        );
        expect(await kanten(band)).toEqual(await kanten(page.locator('.header')));
        expect(await kanten(band)).toEqual([kachelnLinks, kachelnRechts]);
      });

      test('Versionskennung im Fuß ist lesbar (AA)', async ({ page }) => {
        await page.goto('/search');
        await expect(page.locator('.build-kennung')).toBeVisible();
        const { vorne, hinten } = await farben(page, '.build-kennung');
        expect(kontrast(vorne, hinten)).toBeGreaterThanOrEqual(4.5);
      });
    });

    test.describe('390 px', () => {
      test.use({ viewport: { width: 390, height: 844 } });

      test('Zweck-Umschalter: beide Beschriftungen vertikal mittig', async ({ page }) => {
        await page.goto('/workflow/add-commentary');
        const segmente = page.locator('.zweck-wahl mat-button-toggle');
        await expect(segmente).toHaveCount(2);
        for (const segment of await segmente.all()) {
          const aussen = (await segment.boundingBox())!;
          const text = (await segment.locator('.mat-button-toggle-label-content').boundingBox())!;
          const versatz = text.y + text.height / 2 - (aussen.y + aussen.height / 2);
          expect.soft(Math.abs(versatz), `${await segment.textContent()}`).toBeLessThanOrEqual(1);
        }
      });
    });

    test.describe('360 px, anonym', () => {
      test.use({ storageState: ANONYM });

      test('Startseite: Marke „mit Konto“ steht in beiden Kacheln gleich', async ({ page }) => {
        await page.goto('/search');
        const kacheln = page.locator('.start-kachel');
        await expect(kacheln.locator('.kachel-konto')).toHaveCount(2);
        const lagen = await kacheln.evaluateAll((alle) =>
          alle.map((kachel) => {
            const titel = kachel.querySelector('.kachel-titel')!.getBoundingClientRect();
            const marke = kachel.querySelector('.kachel-konto')!.getBoundingClientRect();
            return Math.round(marke.top - titel.top);
          }),
        );
        expect(lagen[0]).toBe(lagen[1]);
      });
    });
  });
}
