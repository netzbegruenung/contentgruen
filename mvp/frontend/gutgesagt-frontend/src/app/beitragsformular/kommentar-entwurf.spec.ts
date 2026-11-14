import {
  KOMMENTAR_ENTWURF_HOECHSTENS_MS,
  KOMMENTAR_ENTWURF_SCHLUESSEL,
  KommentarEntwurfWerte,
  kommentarEntwurfHolen,
  kommentarEntwurfLoeschen,
  kommentarEntwurfSichern,
} from './kommentar-entwurf';

describe('Kommentar-Entwurf (E1)', () => {
  const WERTE: KommentarEntwurfWerte = { title: 'T', text: 'Ein Text', kurz: '', lang: '', zweck: 'kommentarspalte', stil: null };
  const JETZT = 1_800_000_000_000;

  afterEach(() => sessionStorage.removeItem(KOMMENTAR_ENTWURF_SCHLUESSEL));

  it('legt den Entwurf im sessionStorage ab, mit Prüfwert statt Kennung', () => {
    kommentarEntwurfSichern(WERTE, 'Aussage', 'kennung-1', JETZT);

    const roh = sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)!;
    expect(roh).not.toContain('kennung-1');
    expect(localStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)).toBeNull();
    expect(kommentarEntwurfHolen('Aussage', 'kennung-1', JETZT + 1000)).toEqual(WERTE);
  });

  it('gibt ihn nach einer Stunde nicht mehr her und löscht ihn', () => {
    kommentarEntwurfSichern(WERTE, 'Aussage', 'kennung-1', JETZT);

    expect(kommentarEntwurfHolen('Aussage', 'kennung-1', JETZT + KOMMENTAR_ENTWURF_HOECHSTENS_MS + 1)).toBeNull();
    expect(sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)).toBeNull();
  });

  it('gibt ihn einem anderen Konto nicht und löscht ihn', () => {
    kommentarEntwurfSichern(WERTE, 'Aussage', 'kennung-1', JETZT);

    expect(kommentarEntwurfHolen('Aussage', 'kennung-2', JETZT)).toBeNull();
    expect(sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)).toBeNull();
  });

  it('lässt ihn bei einer anderen Aussage liegen', () => {
    kommentarEntwurfSichern(WERTE, 'Aussage', 'kennung-1', JETZT);

    expect(kommentarEntwurfHolen('Andere Aussage', 'kennung-1', JETZT)).toBeNull();
    expect(kommentarEntwurfHolen('Aussage', 'kennung-1', JETZT)).toEqual(WERTE);
  });

  it('sichert ohne Anmeldung oder ohne Inhalt nichts', () => {
    kommentarEntwurfSichern(WERTE, 'Aussage', null, JETZT);
    expect(sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)).toBeNull();

    kommentarEntwurfSichern(WERTE, 'Aussage', 'kennung-1', JETZT);
    kommentarEntwurfSichern({ ...WERTE, title: '', text: ' ' }, 'Aussage', 'kennung-1', JETZT);
    expect(sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)).toBeNull();
  });

  it('löscht auf Zuruf', () => {
    kommentarEntwurfSichern(WERTE, 'Aussage', 'kennung-1', JETZT);
    kommentarEntwurfLoeschen();
    expect(sessionStorage.getItem(KOMMENTAR_ENTWURF_SCHLUESSEL)).toBeNull();
  });
});
