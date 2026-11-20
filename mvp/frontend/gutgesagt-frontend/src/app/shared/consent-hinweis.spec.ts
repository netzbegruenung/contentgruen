import { CONSENT_HINWEIS, CONSENT_HINWEIS_SATZ, hinweisText } from './consent-hinweis';

describe('CONSENT_HINWEIS', () => {
  // Der Wortlaut ist eine Produktentscheidung (#431, #439, #415; seit 0.9.8 „es gelten die Nutzungsbedingungen“, weil die Zustimmung per Häkchen kommt, NB §2): Aenderungen hier bewusst.
  it('hat den beschlossenen Wortlaut, ohne "unwiderruflich"', () => {
    expect(hinweisText(CONSENT_HINWEIS)).toBe(
      'Mit dem Absenden stellst du deine eigene Formulierung unter CC0; es gelten die ' +
        'Nutzungsbedingungen – keine personenbezogenen Daten Dritter.',
    );
  });

  it('hat je Wortlaut eine eigene Kennung (docs/CC0_HINWEIS_WORTLAUTE.md)', () => {
    expect(CONSENT_HINWEIS.kennung).toBe('2026-11-20-formular');
    expect(CONSENT_HINWEIS_SATZ.kennung).toBe('2026-11-20-satz');
  });

  it('sagt beim Satz, dass er beim Tippen gespeichert wird, ebenfalls ohne "unwiderruflich"', () => {
    expect(hinweisText(CONSENT_HINWEIS_SATZ)).toBe(
      'Dein Satz wird beim Tippen gespeichert. Damit stellst du deine eigene Formulierung unter CC0; ' +
        'es gelten die Nutzungsbedingungen – keine personenbezogenen Daten Dritter.',
    );
  });
});
