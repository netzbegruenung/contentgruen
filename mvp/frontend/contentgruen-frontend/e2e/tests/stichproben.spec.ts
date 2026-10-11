import { expect, test } from './fixtures';

/** Stichproben 600 und 960: Formular und Ergebnisse ohne seitlichen Ueberlauf. */
test('Kommentarformular', async ({ page, bild }, testInfo) => {
  const breite = testInfo.project.use.viewport!.width;
  await page.goto('/workflow/add-commentary');
  await expect(page.locator('app-add-commentary form')).toBeVisible();
  await page.locator('.antwort-eingabe').fill('Windräder töten Vögel');
  await expect(page.locator('.neue-aussage')).toBeVisible();
  expect.soft(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false);
  await bild(`${breite === 600 ? '14' : '15'}-formular-${breite}`, true);
});
