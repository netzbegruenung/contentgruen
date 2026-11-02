import { CC0_ERKLAERUNG_URL, CONSENT_HINWEIS, ConsentHinweis, hinweisText } from '../consent-hinweis';

/**
 * Prueft den CC0-Hinweis in einem Formular: voller Wortlaut, beide Links im neuen Tab (#415).
 * Gibt den Absatz zurueck, damit der Aufrufer seine Lage im Formular pruefen kann.
 */
export function erwarteCc0Hinweis(
  wurzel: HTMLElement,
  hinweis: ConsentHinweis = CONSENT_HINWEIS,
): HTMLParagraphElement {
  const absatz: HTMLParagraphElement | null = wurzel.querySelector('p.submit-hint');
  expect(absatz).withContext('CC0-Hinweis ueber dem Knopf').toBeTruthy();
  expect(absatz!.textContent!.replace(/\s+/g, ' ').trim()).toBe(hinweisText(hinweis));

  const cc0: HTMLAnchorElement | null = absatz!.querySelector(`a[href="${CC0_ERKLAERUNG_URL}"]`);
  expect(cc0).withContext('Link auf die CC0-Erklaerung').toBeTruthy();
  expect(cc0!.textContent).toBe(hinweis.cc0);
  expect(cc0!.target).toBe('_blank');

  const nb: HTMLAnchorElement | null = absatz!.querySelector('a[href="/nutzungsbedingungen"]');
  expect(nb).withContext('Link auf die Nutzungsbedingungen').toBeTruthy();
  expect(nb!.textContent).toBe(hinweis.nutzungsbedingungen);
  expect(nb!.target).toBe('_blank');

  return absatz!;
}
