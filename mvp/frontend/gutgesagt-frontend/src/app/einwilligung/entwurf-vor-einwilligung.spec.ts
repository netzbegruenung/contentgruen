import {
  ENTWURF_HOECHSTENS_MS,
  ENTWURF_PRAEFIX,
  entwuerfeLoeschen,
  entwurfHolen,
  entwurfSichern,
} from './entwurf-vor-einwilligung';

/** Begonnene Eingabe waehrend der Einwilligung (UX-Review B4, Review zu #670). */
describe('entwurf-vor-einwilligung', () => {
  afterEach(() => entwuerfeLoeschen());

  it('legt ab und gibt einmal zurueck', () => {
    entwurfSichern('/einwerfen', { hinweis: 'x' }, 1000);
    expect(entwurfHolen('/einwerfen', 2000)).toEqual({ hinweis: 'x' });
    expect(entwurfHolen('/einwerfen', 2000)).toBeUndefined();
  });

  it('verwirft nach einer Stunde', () => {
    entwurfSichern('/einwerfen', 'Satz', 0);
    expect(entwurfHolen('/einwerfen', ENTWURF_HOECHSTENS_MS + 1)).toBeUndefined();
  });

  it('loescht alle Entwuerfe, aber nichts anderes', () => {
    entwurfSichern('/a', 'eins');
    entwurfSichern('/b', 'zwei');
    sessionStorage.setItem('anderes', '1');

    entwuerfeLoeschen();

    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/a')).toBeNull();
    expect(sessionStorage.getItem(ENTWURF_PRAEFIX + '/b')).toBeNull();
    expect(sessionStorage.getItem('anderes')).toBe('1');
    sessionStorage.removeItem('anderes');
  });
});
