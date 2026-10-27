import { expect, test } from './fixtures';

/** Formulare fuer Hintergrundinfo und Bild nur ansehen: Bei 360 px kein seitlicher Ueberlauf. */
for (const [nr, name, pfad] of [
  ['60', 'hintergrundinfo', '/workflow/add-generictext'],
  ['61', 'bild', '/workflow/add-image'],
] as const) {
  test(`${name} bei 360 px`, async ({ page, bild }) => {
    await page.goto(pfad);
    await expect(page.locator('form').first()).toBeVisible();
    const ueberlauf = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
    expect.soft(ueberlauf, 'kein seitlicher Ueberlauf').toBe(false);
    await expect.soft(page.locator('.step-indicator:visible')).toHaveCount(0);
    await bild(`${nr}-${name}`);
    await bild(`${nr}-${name}-ganz`, true);
  });
}
