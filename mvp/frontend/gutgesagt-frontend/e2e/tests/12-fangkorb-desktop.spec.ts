import type { Page } from '@playwright/test';
import { expect, test } from './fixtures';

/**
 * Stichprobe 1280: der Fangkorb mit Seitenleiste (ab 1024 px). Liest nur: Die
 * Einwuerfe kommen aus einem festen Beispielsatz, den der Browser statt der API
 * bekommt; schreibende Anfragen an den Fangkorb beantwortet er selbst, ohne Server.
 */

const stunden = (h: number): string => new Date(Date.now() - h * 3600e3).toISOString();
let nummer = 0;
const id = (): string => `00000000-0000-4000-8000-${String(++nummer).padStart(12, '0')}`;

function satz(text: string, name: string) {
  return { id: id(), user_id: null, user_name: name, ist_eigener_satz: false, sentence: text, updated_at: stunden(2) };
}

function einwurf(felder: Record<string, unknown>) {
  return {
    id: id(), content: null, url: null, image_url: null, submitted_by: null, submitted_by_name: 'Mitglied',
    ist_eigener_einwurf: false, source_channel: 'web', status: 'open', created_at: stunden(5),
    destilled_by: null, own_draft: null, processed_content_id: null, processed_by: null, processed_at: null,
    drafts: [], links: [], ...felder,
  };
}

const EINWUERFE = [
  einwurf({ content: 'Behauptung im Video: Windräder machen den Strom teurer.', url: 'https://www.instagram.com/reel/Cx12abc/', created_at: stunden(1) }),
  einwurf({ content: 'Kommentarspalte voll mit „Heizungsgesetz zwingt Rentner zum Verkauf“.', url: 'https://www.youtube.com/watch?v=abc', created_at: stunden(3) }),
  einwurf({ url: 'https://www.tiktok.com/@beispiel/video/7301234567890', created_at: stunden(4) }),
  einwurf({ content: 'Wieder das Narrativ, Radwege seien schuld am Ladensterben.', url: 'https://www.beispielzeitung.de/lokales/radweg.html',
    created_at: stunden(7), drafts: [satz('Wo Radwege gebaut werden, steigt der Umsatz im Einzelhandel.', 'Alex P.')] }),
  einwurf({ content: 'Post behauptet, E-Autos brennen öfter als Verbrenner.', url: 'https://x.com/beispiel/status/1723456789',
    created_at: stunden(9), drafts: [satz('E-Autos brennen seltener als Verbrenner.', 'Sam K.')] }),
];

async function beispielFangkorb(page: Page): Promise<void> {
  await page.route('**/api/v1/rawinput/**', (route) => {
    const anfrage = route.request();
    if (anfrage.method() !== 'GET') {
      return route.fulfill({ status: 200, json: {} });
    }
    return route.fulfill({
      json: { results_count: EINWUERFE.length, results: EINWUERFE, total_records_count: EINWUERFE.length },
    });
  });
}

test('Fangkorb mit Seitenleiste und queren Karten', async ({ page, bild }) => {
  await beispielFangkorb(page);
  await page.goto('/fangkorb');
  const tabliste = page.getByRole('tablist', { name: 'Arbeitslisten im Fangkorb' });
  await expect(tabliste).toHaveAttribute('aria-orientation', 'vertical');
  await page.getByRole('tab', { name: /Destillieren/ }).click();
  await expect(page.locator('article.karte--quer')).toHaveCount(3);

  // Seitenleiste links neben der Liste, Einwerfen als Knopf darin, kein schwebender
  const leiste = (await page.locator('.steuerung').boundingBox())!;
  const liste = (await page.locator('.liste').boundingBox())!;
  expect(leiste.x + leiste.width).toBeLessThanOrEqual(liste.x);
  await expect(page.locator('.steuerung').getByRole('button', { name: 'Etwas einwerfen' })).toBeVisible();
  await expect(page.locator('.einwerfen-fab')).toHaveCount(0);

  // Quer: Meta-Zeile links neben dem Griff
  const karte = page.locator('article.karte--quer').first();
  const meta = (await karte.locator('.einwurf-meta').boundingBox())!;
  const griff = (await karte.locator('.einwurf-primaer').boundingBox())!;
  expect(meta.x + meta.width).toBeLessThanOrEqual(griff.x);

  // Pfeil runter waehlt die naechste Arbeitsliste
  await page.getByRole('tab', { name: /Destillieren/ }).focus();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('tab', { name: /Ausformulieren/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('tab', { name: /Ausformulieren/ })).toBeFocused();
  await expect(page.locator('article.karte--quer')).toHaveCount(2);

  expect.soft(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await bild('16-fangkorb-seitenleiste', true);
  // Naechster Lauf beginnt wieder beim Destillieren (der Tab steht in der Sitzung)
  await page.getByRole('tab', { name: /Destillieren/ }).click();
});
