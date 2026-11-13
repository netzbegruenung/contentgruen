import { Locator } from '@playwright/test';
import { farben, kontrast } from './darstellung';
import { expect, test } from './fixtures';

/**
 * Kanten und Fluchten auf 360, 390, 1280 und 1440 px, hell und dunkel, und der Umschalter
 * hell/dunkel: Befunde der Designrunde vom 12.11. Liest nur (der Umschalter schreibt nur in
 * den localStorage des Browsers). Die Suche nutzt das Beispiel der Startseite, zu dem der Seed
 * schon eine Aussage hat.
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

      test('Beitragen: Rundgang-Band fluchtet mit Kopf und Kacheln', async ({ page }) => {
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

      test('Beitragen: erst die Kette in einer Reihe, darunter die Typen', async ({ page }) => {
        await page.goto('/contribute');
        const kette = page.locator('.ketten-liste .typ-zeile');
        await expect(kette).toHaveCount(3);
        const oben = await Promise.all((await kette.all()).map(async (z) => Math.round((await z.boundingBox())!.y)));
        expect(new Set(oben).size).toBe(1);
        const ersterTyp = (await page.locator('.commentary-card').boundingBox())!;
        expect(ersterTyp.y).toBeGreaterThan(oben[0]);
      });

      test('Versionskennung im Fuß ist lesbar (AA)', async ({ page }) => {
        await page.goto('/search');
        await expect(page.locator('.build-kennung')).toBeVisible();
        const { vorne, hinten } = await farben(page, '.build-kennung');
        expect(kontrast(vorne, hinten)).toBeGreaterThanOrEqual(4.5);
      });
    });

    test.describe('1440 px', () => {
      test.use({ ...DESKTOP, viewport: { width: 1440, height: 900 } });

      // Seitenrahmen (styles.css): Der Inhalt beginnt --page-margin rechts vom Rand von <main>,
      // wie die Kopfzeile. Gemessen wird der aeussere Kasten des Inhalts.
      for (const [name, pfad, inhalt] of [
        ['Kommentarformular', '/workflow/add-commentary', '.workflow-container > *'],
        ['Einwerfen', '/einwerfen', '.einwurf-container > *'],
        ['Datenschutz', '/datenschutz', '.content-section h2'],
        ['Beitragen', '/contribute', '.typ-zeile'],
      ] as const) {
        test(`${name}: linke Kante wie die Kopfzeile`, async ({ page }) => {
          await page.goto(pfad);
          const element = page.locator(inhalt).first();
          await expect(element).toBeVisible();
          const soll = await page.evaluate(() => {
            const main = document.querySelector('main')!.getBoundingClientRect();
            return main.left + parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--page-margin'));
          });
          // Linkeste sichtbare Teil der Kopfzeile (Zurueck-Pfeil oder Logo)
          const kopfLinks = await page.locator('.header').evaluate((kopf) =>
            Math.min(...[...kopf.querySelectorAll('button, a, img')].map((e) => e.getBoundingClientRect())
              .filter((r) => r.width > 0).map((r) => r.left)),
          );
          expect(Math.abs(kopfLinks - soll)).toBeLessThanOrEqual(1);
          expect(Math.abs((await element.boundingBox())!.x - soll)).toBeLessThanOrEqual(1);
        });
      }

      // Einzelansicht gegen eine gemockte Antwort: Das Dev-Backend kennt die Route nicht immer
      test('Beitrag-Ansicht: Karte 450 px breit, linke Kante wie die Kopfzeile', async ({ page }) => {
        await page.route('**/api/v1/content/beitrag/**', (anfrage) =>
          anfrage.fulfill({
            json: {
              id: 'e2e-ansicht',
              content_type: 'commentary',
              title: 'Windräder schützen das Klima',
              text: 'Jede Kilowattstunde aus Wind ersetzt Strom aus Kohle.',
              references: [],
              created_at: '2025-09-01T00:00:00Z',
            },
          }),
        );
        await page.goto('/beitrag/e2e-ansicht');
        const karte = page.locator('.beitrag-ansicht app-beitragskarte');
        await expect(karte).toBeVisible();
        const soll = await page.evaluate(() => {
          const main = document.querySelector('main')!.getBoundingClientRect();
          return main.left + parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--page-margin'));
        });
        const box = (await karte.boundingBox())!;
        expect(Math.abs(box.x - soll)).toBeLessThanOrEqual(1);
        expect(box.width).toBeLessThanOrEqual(450.5);
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

    for (const breite of [360, 1280]) {
      test.describe(`${breite} px, anonym`, () => {
        test.use({ storageState: ANONYM, ...(breite > 360 ? DESKTOP : {}), viewport: { width: breite, height: 900 } });

        test('Startseite: Marke „mit Konto“ steht in beiden Kacheln neben dem Titel', async ({ page }) => {
          await page.goto('/search');
          const kacheln = page.locator('.start-kachel');
          await expect(kacheln.locator('.kachel-konto')).toHaveCount(2);
          // Breiten haengen an der Schrift: erst messen, wenn sie geladen ist
          await page.evaluate(() => document.fonts.ready.then(() => undefined));
          const lagen = await kacheln.evaluateAll((alle) =>
            alle.map((kachel) => {
              const titel = kachel.querySelector('.kachel-titel')!.getBoundingClientRect();
              const marke = kachel.querySelector('.kachel-konto')!.getBoundingClientRect();
              return { abstand: Math.round(marke.top - titel.top), daneben: marke.left > titel.left + 40 };
            }),
          );
          expect(lagen[0]).toEqual(lagen[1]);
          expect(lagen[0].daneben).toBe(true);
        });
      });
    }
  });
}

test.describe('Umschalter hell/dunkel', () => {
  // Ohne Service Worker: Er koennte eine alte index.html ohne das Farbschema-Skript ausliefern
  test.use({ ...DESKTOP, colorScheme: 'light', serviceWorkers: 'block' });

  test('schaltet um, merkt sich die Wahl und gilt nach dem Neuladen ohne Aufblitzen', async ({ page }) => {
    await page.goto('/search');
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-theme', 'light');
    const knopf = page.getByRole('button', { name: 'Dunkles Farbschema' });
    await expect(knopf).toHaveAttribute('aria-pressed', 'false');
    await knopf.click();
    await expect(html).toHaveAttribute('data-theme', 'dark');
    await expect(knopf).toHaveAttribute('aria-pressed', 'true');
    // main traegt --bg-card der Dunkel-Palette (Wert aus dem Theme, nicht fest im Test)
    const { grund, karte } = await page.evaluate(() => {
      const probe = document.createElement('div');
      probe.style.backgroundColor = 'var(--bg-card)';
      document.body.appendChild(probe);
      const karte = getComputedStyle(probe).backgroundColor;
      probe.remove();
      return { grund: getComputedStyle(document.querySelector('main')!).backgroundColor, karte };
    });
    expect(grund).toBe(karte);
    expect(grund).not.toBe('rgb(255, 255, 255)');

    // Ohne die Skripte der App: Das Attribut setzt schon das Skript in index.html, vor dem ersten Bild
    await page.route('**/*.js', (anfrage) => anfrage.abort());
    await page.reload();
    await expect(html).toHaveAttribute('data-theme', 'dark');
    await page.unroute('**/*.js');
    await page.reload();

    await page.getByRole('button', { name: 'Dunkles Farbschema' }).click();
    await expect(html).toHaveAttribute('data-theme', 'light');
  });
});
