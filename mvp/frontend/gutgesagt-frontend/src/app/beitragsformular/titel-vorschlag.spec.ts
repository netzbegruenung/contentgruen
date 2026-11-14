import { TITEL_MAX } from '../shared/beitrag-grenzen';
import { TITEL_VORSCHLAG_ZIEL, titelVorschlag } from './titel-vorschlag';

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

  it('lässt einen ersten Satz bis etwa 80 Zeichen ganz', () => {
    const satz = 'Wärmepumpen lohnen sich auch im Altbau, wenn die Heizkörper groß genug sind.';
    expect(satz.length).toBeLessThanOrEqual(TITEL_VORSCHLAG_ZIEL);
    expect(titelVorschlag(`${satz} Weiter.`)).toBe(satz);
  });

  it('kürzt einen längeren ersten Satz an einer Satzgrenze innerhalb des Satzes', () => {
    const satz =
      'Wärmepumpen lohnen sich auch in älteren Häusern mit alten Heizkörpern, wenn man die Vorlauftemperatur sauber einstellt und dämmt.';
    expect(titelVorschlag(satz)).toBe('Wärmepumpen lohnen sich auch in älteren Häusern mit alten Heizkörpern');
  });

  it('kürzt ohne Satzgrenze an einer Wortgrenze, mit Auslassungszeichen', () => {
    const vorschlag = titelVorschlag('wort '.repeat(60));
    expect(vorschlag.length).toBeLessThanOrEqual(TITEL_VORSCHLAG_ZIEL);
    expect(vorschlag.endsWith('wort…')).toBeTrue();
    expect(TITEL_MAX).toBeGreaterThanOrEqual(TITEL_VORSCHLAG_ZIEL);
  });

  it('ist leer ohne Text', () => {
    expect(titelVorschlag('')).toBe('');
    expect(titelVorschlag(null)).toBe('');
  });
});
