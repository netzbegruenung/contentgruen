import { TestBed } from '@angular/core/testing';
import { ActivatedRouteSnapshot, Router, convertToParamMap } from '@angular/router';
import {
  SHARE_EINWURF_SCHLUESSEL,
  ShareTargetGuard,
  einwurfAusShareDaten,
} from './share-target.guard';

/** Baut einen Snapshot mit genau diesen Query-Parametern. */
function snapshotMit(params: Record<string, string>): ActivatedRouteSnapshot {
  return { queryParamMap: convertToParamMap(params) } as ActivatedRouteSnapshot;
}

describe('einwurfAusShareDaten', () => {
  it('nimmt die Adresse aus text und entfernt das Instagram-Tracking', () => {
    // Der Instagram-Fall aus dem Geraete-Test: nur text, kein title, kein url.
    expect(
      einwurfAusShareDaten({
        text: 'https://www.instagram.com/reel/DdGvZ__grj9/?stkn=MWxkZmRocDVzZXpubg==',
      }),
    ).toEqual({ url: 'https://www.instagram.com/reel/DdGvZ__grj9/', titel: null, text: null });
  });

  it('trennt den Seitentitel vom Link', () => {
    // Der Chrome-Fall aus dem Geraete-Test: title + text.
    expect(
      einwurfAusShareDaten({
        title: 'AfD klar vor SPD | tagesschau.de',
        text: 'https://www.tagesschau.de/inland/x-100.html',
      }),
    ).toEqual({
      url: 'https://www.tagesschau.de/inland/x-100.html',
      titel: 'AfD klar vor SPD | tagesschau.de',
      text: null,
    });
  });

  it('behaelt Text neben der Adresse, ohne die Adresse', () => {
    expect(
      einwurfAusShareDaten({ text: 'Schau mal https://example.org/a?utm_source=x hier' }),
    ).toEqual({ url: 'https://example.org/a', titel: null, text: 'Schau mal hier' });
  });

  it('wiederholt den Titel nicht, wenn text dasselbe sagt', () => {
    expect(
      einwurfAusShareDaten({ title: 'Ein Titel', text: 'Ein Titel https://example.org/a' }),
    ).toEqual({ url: 'https://example.org/a', titel: 'Ein Titel', text: null });
  });

  it('nimmt den url-Parameter, falls eine App ihn doch benutzt', () => {
    expect(einwurfAusShareDaten({ url: 'https://example.org/a?utm_source=x' })).toEqual({
      url: 'https://example.org/a',
      titel: null,
      text: null,
    });
  });

  it('nimmt dieselbe Adresse in text und url nur einmal', () => {
    expect(
      einwurfAusShareDaten({ text: 'Schau https://example.org/a', url: 'https://example.org/a' }),
    ).toEqual({ url: 'https://example.org/a', titel: null, text: 'Schau' });
  });

  it('nimmt eine abweichende Adresse aus url als Link und laesst die aus text im Hinweis', () => {
    expect(
      einwurfAusShareDaten({
        text: 'Siehe https://example.org/text?utm_source=x',
        url: 'https://example.org/param?utm_source=y',
      }),
    ).toEqual({
      url: 'https://example.org/param',
      titel: null,
      text: 'Siehe https://example.org/text',
    });
  });

  it('liefert lauter null, wenn nichts brauchbares dabei ist', () => {
    const leer = { url: null, titel: null, text: null };
    expect(einwurfAusShareDaten({})).toEqual(leer);
    expect(einwurfAusShareDaten({ title: '  ', text: null, url: undefined })).toEqual(leer);
  });
});

describe('ShareTargetGuard', () => {
  let guard: ShareTargetGuard;
  let router: Router;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    guard = TestBed.inject(ShareTargetGuard);
    router = TestBed.inject(Router);
    sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL);
  });

  afterEach(() => {
    sessionStorage.removeItem(SHARE_EINWURF_SCHLUESSEL);
  });

  it('leitet auf das Einwurf-Formular weiter und legt den getrennten Einwurf ab', () => {
    const ergebnis = guard.canActivate(
      snapshotMit({ title: 'Ein Titel', text: 'https://www.instagram.com/reel/ABC/?stkn=xy' }),
    );

    expect(router.serializeUrl(ergebnis as never)).toBe('/einwerfen');
    expect(JSON.parse(sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL)!)).toEqual({
      url: 'https://www.instagram.com/reel/ABC/',
      titel: 'Ein Titel',
      text: null,
    });
  });

  it('leitet auch dann weiter, wenn gar nichts geteilt wurde -- dann ohne Ablage', () => {
    const ergebnis = guard.canActivate(snapshotMit({}));

    expect(router.serializeUrl(ergebnis as never)).toBe('/einwerfen');
    expect(sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL)).toBeNull();
  });

  it('laesst die Diagnose-Ansicht zu, wenn debug in der Adresse steht', () => {
    const ergebnis = guard.canActivate(snapshotMit({ debug: '1', text: 'https://example.org/a' }));

    expect(ergebnis).toBeTrue();
    // Im Diagnose-Fall wird nichts abgelegt: die Ansicht soll zeigen, was ankam,
    // und nicht nebenbei das Formular befuellen.
    expect(sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL)).toBeNull();
  });
});
