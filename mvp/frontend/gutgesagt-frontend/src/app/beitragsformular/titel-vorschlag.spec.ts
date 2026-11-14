import { TITEL_MAX } from '../shared/beitrag-grenzen';
import { titelVorschlag } from './titel-vorschlag';

describe('titelVorschlag (E2)', () => {
  it('nimmt den ersten Satz', () => {
    expect(titelVorschlag('Wärmepumpen lohnen sich im Altbau. Das zeigt die Studie.', 'Wärmepumpen sind zu teuer')).toBe(
      'Wärmepumpen lohnen sich im Altbau.',
    );
  });

  it('nimmt den ganzen Text ohne Satzzeichen und fasst Umbrüche zusammen', () => {
    expect(titelVorschlag('  Strom wird\nbilliger  ')).toBe('Strom wird billiger');
  });

  it('trennt nicht an Zahlen oder Abkürzungen ohne folgenden Leerraum', () => {
    expect(titelVorschlag('Es sind 2.5 Prozent mehr! Und dann?')).toBe('Es sind 2.5 Prozent mehr!');
  });

  it('kürzt einen langen Satz an einer Wortgrenze auf die Titelgrenze', () => {
    const vorschlag = titelVorschlag('wort '.repeat(60));
    expect(vorschlag.length).toBeLessThanOrEqual(TITEL_MAX);
    expect(vorschlag.endsWith('wort…')).toBeTrue();
  });

  it('ist leer ohne Text', () => {
    expect(titelVorschlag('')).toBe('');
    expect(titelVorschlag(null)).toBe('');
  });
});
