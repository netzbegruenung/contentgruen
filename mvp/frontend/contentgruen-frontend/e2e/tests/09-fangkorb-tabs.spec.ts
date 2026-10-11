import { expect, test } from '@playwright/test';

/** Fangkorb-Tabs: bei 320 und 360 px werden die Namen nicht gekuerzt. */

for (const breite of [320, 360]) {
  test(`Tabs bei ${breite}`, async ({ page }) => {
    await page.setViewportSize({ width: breite, height: 740 });
    await page.goto('/fangkorb');
    await page.locator('button.tab').first().waitFor();
    const werte = await page.$$eval('button.tab', (tabs) =>
      tabs.map((t) => {
        const wort = t.querySelector('.tab-wort') as HTMLElement;
        return { wort: wort.textContent!.trim(), gekuerzt: wort.scrollWidth > wort.clientWidth, noetig: wort.scrollWidth, platz: wort.clientWidth, tab: Math.round(t.getBoundingClientRect().width) };
      }),
    );
    const schiene = await page.locator('.tabs').evaluate((el) => Math.round(el.getBoundingClientRect().width));
    for (const w of werte) {
      expect.soft(w.gekuerzt, `${w.wort} bei ${breite} px`).toBe(false);
    }
    test.info().annotations.push({ type: `Tabs ${breite}`, description: `${schiene}px: ${JSON.stringify(werte)}` });
    await page.screenshot({ path: `${process.env.E2E_SCREENSHOTS ?? 'screenshots'}/42-fangkorb-tabs-${breite}.png`, clip: { x: 0, y: 0, width: breite, height: 200 } });
  });
}
