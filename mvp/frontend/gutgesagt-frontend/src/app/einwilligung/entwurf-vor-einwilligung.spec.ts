import {
  ENTWURF_HOECHSTENS_MS,
  ENTWURF_PRAEFIX,
  entwuerfeAufraeumen,
  entwuerfeLoeschen,
  entwurfHolen,
  entwurfSichern,
  kontoPruefwert,
} from './entwurf-vor-einwilligung';

/** Begonnene Eingabe waehrend der Einwilligung (UX-Review B4, Review zu #670). */
describe('entwurf-vor-einwilligung', () => {
  afterEach(() => entwuerfeLoeschen());

  it('legt ab und gibt einmal zurueck', () => {
    entwurfSichern('/einwerfen', { hinweis: 'x' }, 'kim', 1000);
    expect(entwurfHolen('/einwerfen', 'kim', 2000)).toEqual({ hinweis: 'x' });
    expect(entwurfHolen('/einwerfen', 'kim', 2000)).toBeUndefined();
  });

  it('legt nicht die Kennung ab, nur einen Pruefwert', () => {
    entwurfSichern('/einwerfen', 'x', 'kennung-kim', 1000);
    const roh = sessionStorage.getItem(ENTWURF_PRAEFIX + '/einwerfen')!;
    expect(roh).not.toContain('kennung-kim');
    expect(JSON.parse(roh).konto).toBe(kontoPruefwert('kennung-kim'));
  });

  it('verwendet nach einer Stunde nichts mehr', () => {
    entwurfSichern('/einwerfen', 'Satz', 'kim', 0);
    expect(entwurfHolen('/einwerfen', 'kim', ENTWURF_HOECHSTENS_MS + 1)).toBeUndefined();
  });

  it('gibt den Entwurf eines anderen Kontos nicht heraus', () => {
    entwurfSichern('/einwerfen', 'von kim', 'kim', 1000);
    expect(entwurfHolen('/einwerfen', 'alex', 2000)).toBeUndefined();
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/einwerfen')).toBeNull();
  });

  it('raeumt beim Ablegen abgelaufene Entwuerfe auf', () => {
    entwurfSichern('/alt', 'alt', 'kim', 0);
    entwurfSichern('/neu', 'neu', 'kim', ENTWURF_HOECHSTENS_MS + 1);
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/alt')).toBeNull();
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/neu')).not.toBeNull();
  });

  it('raeumt beim App-Start abgelaufene und fremde auf, laesst eigene', () => {
    entwurfSichern('/kim', 'von kim', 'kim', 1000);
    entwurfSichern('/alex', 'von alex', 'alex', 1000);
    sessionStorage.setItem(ENTWURF_PRAEFIX + '/alt', JSON.stringify({ zeit: 0, konto: kontoPruefwert('kim'), werte: 'alt' }));

    entwuerfeAufraeumen('kim', ENTWURF_HOECHSTENS_MS + 500);

    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/kim')).not.toBeNull();
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/alex')).toBeNull();
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/alt')).toBeNull();
  });

  it('loescht alle Entwuerfe, aber nichts anderes', () => {
    entwurfSichern('/a', 'eins', 'kim');
    entwurfSichern('/b', 'zwei', 'kim');
    sessionStorage.setItem('anderes', '1');

    entwuerfeLoeschen();

    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/a')).toBeNull();
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/b')).toBeNull();
    expect(sessionStorage.getItem('anderes')).toBe('1');
    sessionStorage.removeItem('anderes');
  });
});
