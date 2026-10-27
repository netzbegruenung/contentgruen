import { test as basis, expect, Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/** Alle Texte, die die Tests anlegen, beginnen hiermit - so lassen sie sich finden. */
export const TESTDATEN_PRAEFIX = '[e2e-test]';

/** Ablage fuer benannte Screenshots zusaetzlich zu den Report-Anhaengen. */
const SCREENSHOTS = process.env['E2E_SCREENSHOTS'] ?? path.join(__dirname, '..', 'screenshots');

export interface Einwurf {
  id: string;
  hinweis: string;
  link: string;
}

/** Wann eine Seite zuletzt ein 429 vom Rate-Limit bekam (siehe kontingentAbwarten). */
const zuletztGebremst = new WeakMap<Page, number>();

/** Benannter Screenshot, im Report angehaengt; ``ganzeSeite`` statt nur des sichtbaren Ausschnitts. */
export type Bild = (name: string, ganzeSeite?: boolean) => Promise<void>;

export const test = basis.extend<{ bild: Bild; bremseMerken: void }>({
  bild: async ({ page }, use, testInfo) => {
    fs.mkdirSync(SCREENSHOTS, { recursive: true });
    await use(async (name, ganzeSeite = false) => {
      const datei = path.join(SCREENSHOTS, `${testInfo.project.name}-${name}.png`);
      await page.screenshot({ path: datei, fullPage: ganzeSeite });
      await testInfo.attach(name, { path: datei, contentType: 'image/png' });
    });
  },
  bremseMerken: [
    async ({ page }, use) => {
      page.on('response', (antwort) => {
        if (antwort.status() === 429) zuletztGebremst.set(page, Date.now());
      });
      await use();
    },
    { auto: true },
  ],
});

export { expect };

/**
 * Der Suchdienst erlaubt 10 Anlege-Anfragen pro Minute je Person
 * (middleware/rate_limit.py), eine Dublette kostet zwei. Die Specs zusammen brauchen
 * mehr. Kam seit ``seit`` ein 429, wartet das hier das Minutenfenster ab und liefert
 * true: Dann darf der Aufrufer es noch einmal versuchen. Das Rate-Limit ist eine
 * Grenze der Testumgebung, nicht Gegenstand der Tests.
 */
async function kontingentAbwarten(page: Page, seit: number): Promise<boolean> {
  if ((zuletztGebremst.get(page) ?? 0) < seit) {
    return false;
  }
  test.info().annotations.push({ type: 'Rate-Limit', description: '429, eine Minute gewartet' });
  test.setTimeout(test.info().timeout + 65_000);
  await page.waitForTimeout(61_000);
  return true;
}

/** Uhrzeit (HHMMSS) als Kennung des Laufs, damit sich Titel und Aussagen wiederfinden lassen. */
export function lauf(): string {
  return new Date().toISOString().slice(11, 19).replace(/:/g, '');
}

/** Einen Einwurf ueber das Formular einwerfen; die ID kommt aus der Antwort des Servers. */
export async function einwurfAnlegen(page: Page, hinweis: string, link: string): Promise<Einwurf> {
  await page.goto('/einwerfen');
  await page.locator('#einwurf-link').fill(link);
  await page.locator('#einwurf-hinweis').fill(hinweis);
  const einwerfen = async () => {
    const antwort = page.waitForResponse((r) => r.url().includes('/api/v1/rawinput/addRawInput') && r.request().method() === 'POST');
    await page.locator('.einwerfen-knopf').click();
    return antwort;
  };
  const start = Date.now();
  let antwort = await einwerfen();
  if (antwort.status() === 429 && (await kontingentAbwarten(page, start))) {
    antwort = await einwerfen();
  }
  const angelegt = await antwort.json();
  await expect(page.locator('.einwurf-rueckmeldung .erfolg')).toBeVisible();
  expect(angelegt.id, `Einwurf "${hinweis}" angelegt`).toBeTruthy();
  return { id: angelegt.id, hinweis, link };
}

/** Die Knoepfe unter dem gespeicherten Beitrag, in Reihenfolge. */
export async function ergebnisKnoepfe(page: Page): Promise<string[]> {
  return (await page.locator('.gespeichert-knoepfe > *').allTextContents()).map((k) => k.trim());
}

/** Stufe und verknuepfte Beitraege eines Einwurfs, direkt vom Server. */
export async function einwurfStand(page: Page, id: string): Promise<{ status: string; beitraege: string[] }> {
  const einwurf = await (await page.request.get(`/api/v1/rawinput/${id}`)).json();
  return { status: einwurf.status, beitraege: (einwurf.links ?? []).map((l: { content_id: string }) => l.content_id) };
}

/** Das Formular eines Kommentars oder einer Hintergrundinfo mit Titel und Text fuellen. */
export async function ausfuellen(page: Page, titel: string, text: string): Promise<void> {
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
  const start = Date.now();
  await tastaturSchliessen(page);
  await page.locator('app-formular-leiste .submit-btn').click();
  return aufErgebnisWarten(page, start);
}

/**
 * Nach dem Speichern auf die Ergebnisseite warten; liefert die Beitrags-ID.
 *
 * Ein frueherer Lauf hat fast denselben Beitrag schon gespeichert - die Kennung aus
 * lauf() aendert an der Aehnlichkeit kaum etwas. Kommt deshalb die Frage nach der
 * Dublette, wird trotzdem gespeichert: Geprueft wird, was danach kommt. Scheitert das
 * Speichern am Rate-Limit, wird nach einer Minute erneut versucht.
 *
 * ``seit``: Zeitpunkt vor dem Klick aufs Speichern, damit ein 429 aus einem frueheren
 * Schritt nicht zaehlt.
 */
export async function aufErgebnisWarten(page: Page, seit: number): Promise<string> {
  const ergebnis = page.locator('.gespeichert-satz');
  const trotzdem = page.getByRole('button', { name: 'Trotzdem speichern' });
  const fehler = page.locator('.leiste-fehler:visible, .speicher-fehler:visible');
  // Eine sichtbare Fehlermeldung allein entscheidet nichts: Sie kann noch vom vorigen
  // Versuch stammen. Gehandelt wird auf die Dublette und auf ein neues 429.
  let dublette = false;
  let gewartet = false;
  let frist = Date.now() + 20_000;
  while (!(await ergebnis.isVisible())) {
    if (!dublette && (await trotzdem.isVisible())) {
      dublette = true;
      test.info().annotations.push({ type: 'Dublette', description: 'aus einem frueheren Lauf, trotzdem gespeichert' });
      seit = Date.now();
      frist = seit + 20_000;
      await trotzdem.click();
    } else if (!gewartet && (await kontingentAbwarten(page, seit))) {
      // Hoechstens einmal: ein zweites 429 ist das Stundenlimit.
      gewartet = true;
      seit = Date.now();
      frist = seit + 20_000;
      await tastaturSchliessen(page);
      await page.locator('app-formular-leiste .submit-btn').click();
    } else if (Date.now() > frist) {
      const fehlertext = (await fehler.count()) ? await fehler.first().textContent() : 'kein Fehlertext';
      throw new Error(`Keine Ergebnisseite nach dem Speichern (${fehlertext?.trim()})`);
    } else {
      await page.waitForTimeout(250);
    }
  }
  await page.waitForURL(/\/gespeichert\//);
  return new URL(page.url()).pathname.split('/').pop()!;
}

/**
 * Zurueck von der aktuellen Seite, per System-Zurueck (``'system'``) oder ueber den Pfeil
 * oben links (``'pfeil'``). Wartet, bis die Seite verlassen ist, und liefert die neue Adresse.
 */
export async function zurueck(page: Page, wie: 'system' | 'pfeil'): Promise<URL> {
  const vorher = page.url();
  if (wie === 'system') {
    await page.goBack();
  } else {
    await page.locator('.back-button').click();
  }
  await expect(page).not.toHaveURL(vorher);
  return new URL(page.url());
}
