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
    ).toBe('https://www.instagram.com/reel/DdGvZ__grj9/');
  });

  it('stellt den Titel in die erste Zeile, wenn einer dabei ist', () => {
    // Der Chrome-Fall aus dem Geraete-Test: title + text.
    expect(
      einwurfAusShareDaten({
        title: 'AfD klar vor SPD | tagesschau.de',
        text: 'https://www.tagesschau.de/inland/x-100.html',
      }),
    ).toBe('AfD klar vor SPD | tagesschau.de\nhttps://www.tagesschau.de/inland/x-100.html');
  });

  it('nimmt den url-Parameter mit, falls eine App ihn doch benutzt', () => {
    expect(einwurfAusShareDaten({ url: 'https://example.org/a' })).toBe('https://example.org/a');
  });

  it('schreibt die Adresse nicht zweimal hin, wenn text und url dasselbe liefern', () => {
    expect(
      einwurfAusShareDaten({
        text: 'https://example.org/a',
        url: 'https://example.org/a',
      }),
    ).toBe('https://example.org/a');
  });

  it('bereinigt auch den url-Parameter', () => {
    expect(einwurfAusShareDaten({ url: 'https://example.org/a?utm_source=x' })).toBe(
      'https://example.org/a',
    );
  });

  it('ergibt eine leere Zeichenkette, wenn nichts brauchbares dabei ist', () => {
    expect(einwurfAusShareDaten({})).toBe('');
    expect(einwurfAusShareDaten({ title: '  ', text: null, url: undefined })).toBe('');
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

  it('leitet auf das Einwurf-Formular weiter und legt den Einwurf ab', () => {
    const ergebnis = guard.canActivate(
      snapshotMit({ text: 'https://www.instagram.com/reel/ABC/?stkn=xy' }),
    );

    expect(router.serializeUrl(ergebnis as never)).toBe('/einwerfen');
    expect(sessionStorage.getItem(SHARE_EINWURF_SCHLUESSEL)).toBe(
      'https://www.instagram.com/reel/ABC/',
    );
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
