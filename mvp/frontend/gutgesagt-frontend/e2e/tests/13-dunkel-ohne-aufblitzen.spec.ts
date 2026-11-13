import * as fs from 'fs';
import * as path from 'path';
import { Route } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Dunkelmodus im Produktions-Build: Der Build inlined nur das kritische CSS und laedt das
 * volle Stylesheet nachtraeglich. Bis es da ist, sind Grund, Karten und Baender schon dunkel
 * (Inline-Style in index.html); der Rest kommt mit dem Stylesheet. Braucht keinen Stack: Die Dateien kommen aus dem Build, jede API-Anfrage
 * bekommt 404. Nur mit E2E_DIST (Pfad zu dist/.../browser nach `ng build`), sonst uebersprungen.
 */
const DIST = process.env['E2E_DIST'] && path.resolve(process.env['E2E_DIST']);
const URSPRUNG = 'http://gutgesagt-build.test';

const TYPEN: Record<string, string> = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2', '.woff': 'font/woff',
  '.ttf': 'font/ttf', '.otf': 'font/otf', '.ico': 'image/x-icon', '.webmanifest': 'application/manifest+json',
};

function ausDemBuild(route: Route): Promise<void> {
  const pfad = decodeURIComponent(new URL(route.request().url()).pathname);
  if (pfad.startsWith('/api/')) return route.fulfill({ status: 404, body: '' });
  let datei = path.join(DIST!, pfad);
  if (!datei.startsWith(DIST!) || !fs.existsSync(datei) || fs.statSync(datei).isDirectory()) {
    datei = path.join(DIST!, 'index.html'); // Router der App
  }
  return route.fulfill({ body: fs.readFileSync(datei), contentType: TYPEN[path.extname(datei)] ?? 'application/octet-stream' });
}

test.describe('Dunkelmodus ohne Aufblitzen (Produktions-Build)', () => {
  test.skip(!DIST, 'E2E_DIST nicht gesetzt');
  test.use({ baseURL: URSPRUNG, storageState: { cookies: [], origins: [] }, colorScheme: 'dark', serviceWorkers: 'block' });

  test('Grundflaechen und Baender dunkel, bis das Stylesheet da ist', async ({ page }) => {
    let freigeben: () => void = () => undefined;
    const freigabe = new Promise<void>((weiter) => (freigeben = weiter));
    await page.route(`${URSPRUNG}/**`, ausDemBuild);
    // Das volle Stylesheet haengt, bis der Test es freigibt
    await page.route(/\/styles-[^/]*\.css$/, async (route) => {
      await freigabe;
      await ausDemBuild(route);
    });

    await page.goto('/search', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    // Die App rendert ohne das volle Stylesheet; main traegt dann --bg-card aus dem Inline-Style
    await expect(page.locator('main')).toBeAttached({ timeout: 15_000 });
    // Such-Band und Willkommen-Band der Startseite
    await expect(page.locator('.such-band')).toBeAttached({ timeout: 15_000 });
    await expect(page.locator('app-rundgang-band .band')).toBeAttached();
    const farben = await page.evaluate(() => ({
      body: getComputedStyle(document.body).backgroundColor,
      main: getComputedStyle(document.querySelector('main')!).backgroundColor,
      suchband: getComputedStyle(document.querySelector('.such-band')!).backgroundColor,
      willkommen: getComputedStyle(document.querySelector('app-rundgang-band .band')!).backgroundColor,
      geladen: [...document.styleSheets].some((blatt) => /styles-[^/]*\.css$/.test(blatt.href ?? '')),
    }));
    expect(farben.geladen).toBe(false);
    expect(farben.body).toBe('rgb(30, 31, 30)'); // --bg-main der Palette n2, nicht das helle Beige
    expect(farben.suchband).toBe('rgb(46, 60, 25)'); // Moos statt Gelb
    expect(farben.willkommen).toBe('rgb(46, 60, 25)');

    // Nach dem Stylesheet dieselben Flaechen: Inline-Style und Theme sagen dasselbe
    freigeben();
    await expect
      .poll(() => page.evaluate(() => [...document.styleSheets].some((blatt) => /styles-[^/]*\.css$/.test(blatt.href ?? ''))))
      .toBe(true);
    const danach = await page.evaluate(() => ({
      body: getComputedStyle(document.body).backgroundColor,
      main: getComputedStyle(document.querySelector('main')!).backgroundColor,
      suchband: getComputedStyle(document.querySelector('.such-band')!).backgroundColor,
      willkommen: getComputedStyle(document.querySelector('app-rundgang-band .band')!).backgroundColor,
    }));
    const { geladen: _vorher, ...vorher } = farben;
    expect(danach).toEqual(vorher);
  });
});
