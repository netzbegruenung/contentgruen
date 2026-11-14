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

  it('endet nicht an Abkürzungen wie „z. B.“ oder „bzw.“ (Review)', () => {
    expect(titelVorschlag('Das ist z. B. teuer. Aber es lohnt sich.')).toBe('Das ist z. B. teuer.');
    expect(titelVorschlag('Strom bzw. Wärme wird billiger. Weiter.')).toBe('Strom bzw. Wärme wird billiger.');
    expect(titelVorschlag('Seit dem 1. Januar gilt das GEG. Mehr dazu.')).toBe('Seit dem 1. Januar gilt das GEG.');
    expect(titelVorschlag('Das sagt u.a. die Studie. Weiter.')).toBe('Das sagt u.a. die Studie.');
  });

  it('endet am Punkt nach einer Jahreszahl oder Zahl am Satzende (Review #686)', () => {
    expect(titelVorschlag('Das Gesetz gilt seit 2024. Trotzdem fehlt die Förderung.')).toBe('Das Gesetz gilt seit 2024.');
    expect(titelVorschlag('Die Quote liegt bei 80. Das reicht nicht.')).toBe('Die Quote liegt bei 80.');
    expect(titelVorschlag('Die Anlage läuft seit 2019.')).toBe('Die Anlage läuft seit 2019.');
  });

  it('endet nicht an einer Ordinalzahl vor einem Monat, „Jahrhundert“ oder einem kleinen Wort', () => {
    expect(titelVorschlag('Ab dem 1. Januar 2025 gilt das. Weiter.')).toBe('Ab dem 1. Januar 2025 gilt das.');
    expect(titelVorschlag('Am 3. Oktober feiern wir. Weiter.')).toBe('Am 3. Oktober feiern wir.');
    expect(titelVorschlag('Seit dem 19. Jahrhundert wächst die Stadt. Weiter.')).toBe('Seit dem 19. Jahrhundert wächst die Stadt.');
    expect(titelVorschlag('Am 3. und 4. Mai ist Markt. Weiter.')).toBe('Am 3. und 4. Mai ist Markt.');
    expect(titelVorschlag('Nach dem 2. Weltkrieg wurde neu gebaut. Weiter.')).toBe('Nach dem 2. Weltkrieg wurde neu gebaut.');
    expect(titelVorschlag('Die 3. Klasse lernt das. Weiter.')).toBe('Die 3. Klasse lernt das.');
    expect(titelVorschlag('Der 1. FC Köln spielt. Weiter.')).toBe('Der 1. FC Köln spielt.');
  });

  it('endet weiter an einem normalen Satzende mit Punkt', () => {
    expect(titelVorschlag('Wind ist günstig. Solar auch.')).toBe('Wind ist günstig.');
  });

  it('ist leer ohne Text', () => {
    expect(titelVorschlag('')).toBe('');
    expect(titelVorschlag(null)).toBe('');
  });
});
