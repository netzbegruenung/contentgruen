import { expect, test, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Live-Check der Nachlese-Punkte bei 360 px gegen den Dev-Server aus dem Worktree
 * cg-nachlese2. Angelegt werden nur Einwuerfe mit dem Praefix unten.
 */
const PRAEFIX = '[nachlese]';
const BILDER = process.env.E2E_SCREENSHOTS ?? path.join(process.env.HOME!, 'reviews', 'nachlese');

async function bild(page: Page, name: string): Promise<void> {
  fs.mkdirSync(BILDER, { recursive: true });
  await page.screenshot({ path: path.join(BILDER, `${name}.png`) });
}

function lauf(): string {
  return new Date().toISOString().slice(11, 19).replace(/:/g, '');
}

test('Menue: Beitragen als Kopf, darunter Einwerfen, Fangkorb, Meine Beitraege', async ({ page }) => {
  await page.goto('/search');
  await page.locator('.menu-button').click();
  await expect(page.locator('.mobile-menu-gruppe')).toBeVisible();
  await bild(page, '01-menue');

  const gruppe = page.locator('.mobile-menu-gruppe .mobile-menu-item');
  expect((await gruppe.allTextContents()).map((t) => t.replace(/\s+/g, ' ').trim())).toEqual([
    '📥 Schnell einwerfen',
    '🧺 Fangkorb',
    '🗃️ Meine Beiträge',
  ]);
  await expect(page.locator('.mobile-menu-beitraege .menu-emoji')).toHaveText('🗃️');
  await expect(page.locator('.mobile-menu-beitragen mat-icon')).toHaveText('add');

  // Eingerueckt gegenueber dem Kopf "Beitragen"
  const kopf = await page.locator('.mobile-menu-beitragen').boundingBox();
  const kind = await page.locator('.mobile-menu-einwerfen').boundingBox();
  expect(kind!.x).toBeGreaterThan(kopf!.x);
});

test('Einwerfen heisst ueberall gleich: Kachel, Menue, Seitenkopf', async ({ page }) => {
  await page.goto('/contribute');
  await expect(page.locator('.einwerfen-block .typ-titel')).toHaveText('Schnell einwerfen');
  await bild(page, '12-kachel-schnell-einwerfen');

  await page.goto('/einwerfen');
  await expect(page.locator('.mobile-header-title')).toHaveText('Schnell einwerfen');
  await bild(page, '13-kopf-schnell-einwerfen');
});

test('Einwerfen: Pfeil nach /contribute, aus dem Fangkorb zurueck in den Fangkorb', async ({ page }) => {
  await page.goto('/contribute');
  await page.locator('.einwerfen-block').click();
  await page.waitForURL(/\/einwerfen/);
  await bild(page, '02-einwerfen-von-contribute');
  await page.locator('.back-button').click();
  await page.waitForURL(/\/contribute/);
  expect(new URL(page.url()).pathname).toBe('/contribute');
  await bild(page, '03-zurueck-contribute');

  await page.goto('/fangkorb');
  await page.locator('.einwerfen-fab, .fab, [aria-label*="inwerfen"]').first().click();
  await page.waitForURL(/\/einwerfen/);
  expect(new URL(page.url()).search).toContain('von=fangkorb');
  await bild(page, '04-einwerfen-vom-fangkorb');
  await page.locator('.back-button').click();
  await page.waitForURL(/\/fangkorb/);
  expect(new URL(page.url()).pathname).toBe('/fangkorb');
  await bild(page, '05-zurueck-fangkorb');
});

test('Destillieren: Kopfband im Satz-Schritt, neue Knopftexte, Hinweis', async ({ page }) => {
  const hinweis = `${PRAEFIX} Kopfband im Satzschritt ${lauf()}`;
  await page.goto('/einwerfen');
  await page.locator('#einwurf-link').fill('https://example.org/waermepumpe-altbau');
  await page.locator('#einwurf-hinweis').fill(hinweis);
  await page.locator('.einwerfen-knopf').click();
  await expect(page.locator('.einwurf-rueckmeldung .erfolg')).toBeVisible();

  const liste = await (await page.request.get('/api/v1/rawinput/getRawInputs?page=1&page_size=100')).json();
  const einwurf = liste.results.find((e: any) => e.content === hinweis);
  expect(einwurf, 'Einwurf angelegt').toBeTruthy();

  await page.goto(`/destillieren/${einwurf.id}`);
  await expect(page.locator('.einwurf-kopf .rohling-titel')).toHaveText(hinweis);
  await expect(page.locator('.einwurf-kopf .rohling-adresse')).toContainText('example.org');
  await expect(page.locator('.weiter')).toHaveText('Ausformulieren');
  await expect(page.locator('.spaeter')).toHaveText('Überspringen');
  await expect(page.locator('.verwerfen')).toHaveText('Einwurf verwerfen');
  await expect(page.locator('.spaeter-hinweis')).toHaveCount(0);
  await bild(page, '06-destillieren-satz');

  // Der Link im Kopfband muss anklickbar bleiben - vorher stand hier ein direkter Link.
  const linkzeile = page.locator('.einwurf-kopf .rohling-linkzeile');
  await expect(linkzeile).toHaveAttribute('href', 'https://example.org/waermepumpe-altbau');
  await expect(linkzeile).toHaveAttribute('target', '_blank');
  expect(await linkzeile.evaluate((el) => getComputedStyle(el).pointerEvents)).not.toBe('none');
  const [neuerTab] = await Promise.all([page.context().waitForEvent('page'), linkzeile.click()]);
  expect(neuerTab.url()).toBe('https://example.org/waermepumpe-altbau');
  await neuerTab.close();

  await page.locator('#satz').fill('Wärmepumpen rechnen sich im Altbau, wenn man die Förderung mitrechnet');
  await expect(page.locator('.spaeter-hinweis')).toHaveText('Satz wird gemerkt.');
  await bild(page, '07-destillieren-hinweis');
});

test('Fangkorb: der eigene Einwurf steht als "Von: Du"', async ({ page }) => {
  await page.goto('/fangkorb');
  await expect(page.locator('article.karte--rohling').first()).toBeVisible();
  const eigene = page.locator('article.karte--rohling', { hasText: PRAEFIX }).first();
  await expect(eigene.locator('.rohling-einwerfer')).toHaveText('Von: Du');
  await bild(page, '08-fangkorb-von-du');
});

test('Meine Beitraege: "Von: Du" im Sheet, eigene Kopie zaehlt nicht', async ({ page }) => {
  const beitraege = await (
    await page.request.get('/api/v1/contribution/getContributionsOfUser?page=1&page_size=1')
  ).json();
  const beitrag = beitraege.results[0];
  expect(beitrag, 'mindestens ein eigener Beitrag').toBeTruthy();

  const vorher = await (
    await page.request.get(`/api/v1/usage/content/${beitrag.id}/usage`)
  ).json();

  await page.goto('/contributions');
  await expect(page.locator('app-kartenliste article').first()).toBeVisible();
  await bild(page, '09-album');
  await page.locator('app-kartenliste article').first().click();

  const sheet = page.locator('app-beitrag-sheet');
  await expect(sheet).toBeVisible();
  await expect(sheet.locator('.karte-meta')).toContainText('Von: Du');
  const zaehlerVorKopie = (await sheet.locator('.badge-nutzung').textContent())!.trim();
  await sheet.locator('.karte-meta').scrollIntoViewIfNeeded();
  await bild(page, '10-sheet-von-du');

  await sheet.locator('.kopieren-knopf').click();
  await expect(page.locator('.mat-mdc-snack-bar-label').first()).toContainText('kopiert');
  await expect(sheet.locator('.badge-nutzung')).toHaveText(zaehlerVorKopie);
  await bild(page, '11-sheet-nach-kopie');

  // Und serverseitig: der Zaehler steht danach unveraendert.
  await page.waitForTimeout(1500);
  const nachher = await (
    await page.request.get(`/api/v1/usage/content/${beitrag.id}/usage`)
  ).json();
  expect(nachher.usage_count).toBe(vorher.usage_count);
});
