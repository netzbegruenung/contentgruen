import {
  ALTER_ENTWURF_PRAEFIX,
  ENTWURF_HOECHSTENS_MS,
  entwuerfeAufraeumen,
  entwuerfeLoeschen,
  entwurfDa,
  entwurfHolen,
  entwurfSichern,
} from './entwurf-vor-einwilligung';

/** Begonnene Eingabe waehrend der Einwilligung, nur im Arbeitsspeicher (UX-Review B4, PR #670). */
describe('entwurf-vor-einwilligung', () => {
  afterEach(() => entwuerfeLoeschen());

  it('legt ab und gibt einmal zurueck, ohne den Browser-Speicher zu beruehren', () => {
    const setItem = spyOn(Storage.prototype, 'setItem').and.callThrough();
    entwurfSichern('/einwerfen', { hinweis: 'x' }, 'kim', 1000);
    expect(setItem).not.toHaveBeenCalled();
    expect(entwurfHolen('/einwerfen', 'kim', 2000)).toEqual({ hinweis: 'x' });
    expect(entwurfHolen('/einwerfen', 'kim', 2000)).toBeUndefined();
  });

  it('verwendet nach einer Stunde nichts mehr', () => {
    entwurfSichern('/einwerfen', 'Satz', 'kim', 0);
    expect(entwurfHolen('/einwerfen', 'kim', ENTWURF_HOECHSTENS_MS + 1)).toBeUndefined();
  });

  it('gibt den Entwurf eines anderen Kontos nicht heraus', () => {
    entwurfSichern('/einwerfen', 'von kim', 'kim', 1000);
    expect(entwurfHolen('/einwerfen', 'alex', 2000)).toBeUndefined();
    expect(entwurfDa('/einwerfen')).toBeFalse();
  });

  it('raeumt beim Ablegen abgelaufene Entwuerfe auf', () => {
    entwurfSichern('/alt', 'alt', 'kim', 0);
    entwurfSichern('/neu', 'neu', 'kim', ENTWURF_HOECHSTENS_MS + 1);
    expect(entwurfDa('/alt')).toBeFalse();
    expect(entwurfDa('/neu')).toBeTrue();
  });

  it('raeumt abgelaufene und fremde auf, laesst eigene, und alte Eintraege im sessionStorage gehen', () => {
    entwurfSichern('/alt', 'alt', 'kim', 0);
    entwurfSichern('/kim', 'von kim', 'kim', 1000);
    entwurfSichern('/alex', 'von alex', 'alex', 1000);
    sessionStorage.setItem(ALTER_ENTWURF_PRAEFIX + '/einwerfen', '{}');

    entwuerfeAufraeumen('kim', ENTWURF_HOECHSTENS_MS + 500);

    expect(entwurfDa('/kim')).toBeTrue();
    expect(entwurfDa('/alex')).toBeFalse();
    expect(entwurfDa('/alt')).toBeFalse();
    expect(sessionStorage.getItem(ALTER_ENTWURF_PRAEFIX + '/einwerfen')).toBeNull();
  });

  it('loescht alle Entwuerfe', () => {
    entwurfSichern('/a', 'eins', 'kim');
    entwurfSichern('/b', 'zwei', 'kim');

    entwuerfeLoeschen();

    expect(entwurfDa('/a')).toBeFalse();
    expect(entwurfDa('/b')).toBeFalse();
  });
});
