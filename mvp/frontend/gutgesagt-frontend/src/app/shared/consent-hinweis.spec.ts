import { CONSENT_HINWEIS, CONSENT_HINWEIS_SATZ } from './consent-hinweis';

function ganz(hinweis: { vorLink: string; link: string; nachLink: string }): string {
  return `${hinweis.vorLink}${hinweis.link}${hinweis.nachLink}`;
}

describe('CONSENT_HINWEIS', () => {
  // Der Wortlaut ist eine Produktentscheidung (#431, #439): Aenderungen hier bewusst.
  it('hat den beschlossenen Wortlaut, ohne "unwiderruflich"', () => {
    expect(ganz(CONSENT_HINWEIS)).toBe(
      'Mit dem Absenden stellst du deine eigene Formulierung unter CC0 und bestätigst die ' +
        'Nutzungsbedingungen – keine personenbezogenen Daten Dritter.',
    );
  });

  it('hat je Wortlaut eine eigene Kennung (docs/CC0_HINWEIS_WORTLAUTE.md)', () => {
    expect(CONSENT_HINWEIS.kennung).toBe('2026-10-29-formular');
    expect(CONSENT_HINWEIS_SATZ.kennung).toBe('2026-10-29-satz');
  });

  it('sagt beim Satz, dass er beim Tippen gespeichert wird, ebenfalls ohne "unwiderruflich"', () => {
    expect(ganz(CONSENT_HINWEIS_SATZ)).toBe(
      'Dein Satz wird beim Tippen gespeichert. Damit stellst du deine eigene Formulierung unter CC0 ' +
        'und bestätigst die Nutzungsbedingungen – keine personenbezogenen Daten Dritter.',
    );
  });
});
