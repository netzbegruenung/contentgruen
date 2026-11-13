import { expect, test } from './fixtures';

/**
 * Platzhalter vor dem Kopieren füllen (Persona-Test Dennis, 13.11.): Ein Kommentar mit
 * „[Hier …]“ öffnet beim Kopieren den Dialog; kopiert wird der gefüllte Text, und erst
 * dann zählt die Nutzung. Legt nichts an und braucht keinen Stack: Alle Anfragen an
 * /api beantwortet der Test selbst (route.fulfill).
 */
const ID = 'e2e-platzhalter';
const TEXT = 'Vögel und Klima. [Hier ein eigenes Erlebnis: Windpark in deiner Gegend] Deshalb ja.';

test('Besucher: Platzhalter vor dem Kopieren füllen', async ({ page, context, bild }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const nutzung: string[] = [];
  await page.route('**/api/**', async (route) => {
    const url = route.request().url();
    if (url.includes(`/content/beitrag/${ID}`)) {
      await route.fulfill({
        json: {
          id: ID,
          content_type: 'commentary',
          title: 'Windkraft und Vogelschutz gehen zusammen',
          text: TEXT,
          created: '2026-11-13T10:00:00Z',
          usage_count: 0,
          references: [],
        },
      });
    } else if (url.includes(`/content/${ID}/usage`)) {
      nutzung.push(url);
      await route.fulfill({ json: { success: true } });
    } else {
      await route.fulfill({ status: 404, json: {} });
    }
  });

  await page.goto(`/beitrag/${ID}`);
  await expect(page.locator('app-beitragskarte mark.vorlagen-luecke')).toBeVisible({ timeout: 20_000 });
  await page.locator('.kopieren-knopf').click();

  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('heading')).toHaveText('Fülle den Platzhalter aus');
  await expect(dialog.locator('.platzhalter-hinweis')).toHaveText('Hier ein eigenes Erlebnis: Windpark in deiner Gegend');
  const kopieren = dialog.getByRole('button', { name: 'Kopieren', exact: true });
  await expect(kopieren).toBeDisabled();
  // Erst nach dem Einblenden fotografieren, sonst scheint die Seite durch
  await page.waitForFunction(() => document.getAnimations().length === 0);
  await bild('platzhalter-dialog');

  await dialog.getByLabel('Dein Satz').fill('Bei uns stehen drei Windräder, die Störche brüten weiter.');
  await kopieren.click();
  await expect(dialog).toBeHidden();

  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(
    'Vögel und Klima. Bei uns stehen drei Windräder, die Störche brüten weiter. Deshalb ja.',
  );
  await expect.poll(() => nutzung.length).toBe(1);
});

test('Besucher: abbrechen kopiert nichts, ohne Platzhalter kopiert sauber', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  const nutzung: string[] = [];
  await page.route('**/api/**', async (route) => {
    const url = route.request().url();
    if (url.includes(`/content/beitrag/${ID}`)) {
      await route.fulfill({
        json: { id: ID, content_type: 'commentary', title: 'Windkraft und Vogelschutz gehen zusammen', text: TEXT, created: '', references: [] },
      });
    } else if (url.includes(`/content/${ID}/usage`)) {
      nutzung.push(url);
      await route.fulfill({ json: { success: true } });
    } else {
      await route.fulfill({ status: 404, json: {} });
    }
  });

  await page.goto(`/beitrag/${ID}`);
  await page.locator('.kopieren-knopf').click({ timeout: 20_000 });
  await page.getByRole('dialog').getByRole('button', { name: 'Abbrechen' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  expect(nutzung).toEqual([]);

  await page.locator('.kopieren-knopf').click();
  await page.getByRole('dialog').getByRole('button', { name: 'Ohne Platzhalter kopieren' }).click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('Vögel und Klima. Deshalb ja.');
  await expect.poll(() => nutzung.length).toBe(1);
});
