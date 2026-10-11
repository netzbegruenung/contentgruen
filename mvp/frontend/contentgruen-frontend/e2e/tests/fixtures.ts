import { test as basis, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/** Alle Texte, die die Tests anlegen, beginnen hiermit - so lassen sie sich finden. */
export const TESTDATEN_PRAEFIX = '[4b-test]';

/** Ablage fuer benannte Screenshots zusaetzlich zu den Report-Anhaengen. */
const SCREENSHOTS = process.env.E2E_SCREENSHOTS ?? path.join(__dirname, '..', 'screenshots');

export interface Einwurf {
  id: string;
  hinweis: string;
  link: string;
}

export const test = basis.extend<{ bild: (name: string, ganz?: boolean) => Promise<void> }>({
  bild: async ({ page }, use, testInfo) => {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    await use(async (name, ganz = false) => {
      const datei = path.join(SCREENSHOTS, `${name}.png`);
      await page.screenshot({ path: datei, fullPage: ganz });
      await testInfo.attach(name, { path: datei, contentType: 'image/png' });
    });
  },
});

export { expect };

/** Eindeutiger Zusatz, damit wiederholte Laeufe sich nicht als Dubletten verschlucken. */
export function lauf(): string {
  return new Date().toISOString().slice(11, 19).replace(/:/g, '');
}

/** Einen Einwurf ueber das Formular anlegen und seine ID ueber die API holen. */
export async function einwurfAnlegen(page: Page, hinweis: string, link: string): Promise<Einwurf> {
  await page.goto('/einwerfen');
  await page.locator('#einwurf-link').fill(link);
  await page.locator('#einwurf-hinweis').fill(hinweis);
  await page.locator('.einwerfen-knopf').click();
  await expect(page.locator('.einwurf-rueckmeldung .erfolg')).toBeVisible();
  const liste = await (await page.request.get('/api/v1/rawinput/getRawInputs?page=1&page_size=100')).json();
  const einwurf = liste.results.find((e: any) => e.content === hinweis);
  expect(einwurf, `Einwurf "${hinweis}" in der Liste`).toBeTruthy();
  return { id: einwurf.id, hinweis, link };
}

/** Das Kommentarformular mit Titel und Text fuellen. */
export async function kommentarAusfuellen(page: Page, titel: string, text: string): Promise<void> {
  await page.locator('textarea#title').fill(titel);
  await page.locator('textarea#text').fill(text);
}

/**
 * Wie das Schliessen der Tastatur am Handy: Solange ein Textfeld den Fokus hat,
 * blendet sich die Speicher-Leiste aus.
 */
export async function tastaturSchliessen(page: Page): Promise<void> {
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
}

/** Speichern ueber die Leiste und auf die Ergebnisseite warten; liefert die Beitrags-ID. */
export async function speichernUndErgebnis(page: Page): Promise<string> {
  await tastaturSchliessen(page);
  await page.locator('app-formular-leiste .submit-btn').click();
  await page.waitForURL(/\/gespeichert\//);
  await expect(page.locator('.gespeichert-satz')).toBeVisible();
  return new URL(page.url()).pathname.split('/').pop()!;
}
