import { TestBed } from '@angular/core/testing';
import { MatSnackBar, MatSnackBarRef, TextOnlySnackBar } from '@angular/material/snack-bar';
import { NavigationError } from '@angular/router';
import { Subject } from 'rxjs';

import {
  HINWEIS_KNOPF,
  HINWEIS_TEXT,
  NeueVersionService,
  SEITENWECHSEL,
  SITZUNGSSPEICHER,
  SPERRE_MS,
  SPERRE_SCHLUESSEL,
  istLadefehler,
} from './neue-version';
import { GlobalErrorHandler } from '../services/error-handler.service';

/** Ein Speicher im Arbeitsspeicher, damit der echte sessionStorage unberuehrt bleibt. */
function speicherAttrappe(): Storage {
  const daten = new Map<string, string>();
  return {
    get length() {
      return daten.size;
    },
    clear: () => daten.clear(),
    getItem: (k: string) => daten.get(k) ?? null,
    key: (i: number) => Array.from(daten.keys())[i] ?? null,
    removeItem: (k: string) => void daten.delete(k),
    setItem: (k: string, v: string) => void daten.set(k, v),
  };
}

describe('neue Version laden', () => {
  describe('istLadefehler', () => {
    const meldungen: Array<[string, unknown]> = [
      ['Chrome', new TypeError('Failed to fetch dynamically imported module: https://gutgesagt.example/chunk-ABC123.js')],
      ['Firefox', new TypeError('error loading dynamically imported module: https://gutgesagt.example/chunk-ABC123.js')],
      ['Safari', new TypeError('Importing a module script failed.')],
      ['webpack', Object.assign(new Error('Loading chunk 123 failed.\n(error: /123.js)'), { name: 'ChunkLoadError' })],
      ['webpack mit Namen', new Error('Loading chunk src_app_impressum_impressum_component_ts failed.')],
      ['Name allein', Object.assign(new Error('irgendwas'), { name: 'ChunkLoadError' })],
      ['unbehandelte Promise-Ablehnung', { rejection: new TypeError('Importing a module script failed.') }],
      ['NavigationError', new NavigationError(1, '/impressum', new TypeError('Failed to fetch dynamically imported module: x'))],
      ['Text', 'Failed to fetch dynamically imported module: x'],
    ];
    for (const [browser, fehler] of meldungen) {
      it(`erkennt ${browser}`, () => {
        expect(istLadefehler(fehler)).toBeTrue();
      });
    }

    const andere: Array<[string, unknown]> = [
      ['HTTP-Fehler', { status: 404, message: 'Http failure response for /api/x: 404 Not Found' }],
      ['Netzfehler beim fetch', new TypeError('Failed to fetch')],
      ['gewoehnlicher Fehler', new Error('Cannot read properties of undefined')],
      ['null', null],
      ['undefined', undefined],
      ['Zahl', 42],
    ];
    for (const [art, fehler] of andere) {
      it(`laesst ${art} durch`, () => {
        expect(istLadefehler(fehler)).toBeFalse();
      });
    }

    it('haengt bei einem Fehler, der auf sich selbst zeigt, nicht', () => {
      const fehler: { message: string; error?: unknown; rejection?: unknown } = { message: 'x' };
      fehler.error = fehler;
      fehler.rejection = fehler;
      expect(istLadefehler(fehler)).toBeFalse();
    });
  });

  describe('NeueVersionService', () => {
    let seitenwechsel: jasmine.Spy<(url: string) => void>;
    let snackBar: jasmine.SpyObj<MatSnackBar>;
    let aktion: Subject<void>;
    let geschlossen: Subject<void>;

    function dienst(speicher: Storage | null): NeueVersionService {
      TestBed.configureTestingModule({
        providers: [
          { provide: SEITENWECHSEL, useValue: seitenwechsel },
          { provide: SITZUNGSSPEICHER, useValue: speicher },
          { provide: MatSnackBar, useValue: snackBar },
        ],
      });
      return TestBed.inject(NeueVersionService);
    }

    beforeEach(() => {
      seitenwechsel = jasmine.createSpy('seitenwechsel');
      aktion = new Subject<void>();
      geschlossen = new Subject<void>();
      snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
      snackBar.open.and.returnValue({
        onAction: () => aktion,
        afterDismissed: () => geschlossen,
      } as unknown as MatSnackBarRef<TextOnlySnackBar>);
    });

    it('laedt das Ziel hart und merkt sich den Zeitpunkt', () => {
      const speicher = speicherAttrappe();
      const ausgang = dienst(speicher).neueVersionLaden('/impressum');

      expect(ausgang).toBe('neu-geladen');
      expect(seitenwechsel).toHaveBeenCalledOnceWith('/impressum');
      expect(Number(speicher.getItem(SPERRE_SCHLUESSEL))).toBeCloseTo(Date.now(), -3);
      expect(snackBar.open).not.toHaveBeenCalled();
    });

    it('wechselt auf derselben Seite nur einmal, auch wenn der Fehler zweimal ankommt', () => {
      const neueVersion = dienst(speicherAttrappe());

      neueVersion.neueVersionLaden('/impressum');
      expect(neueVersion.neueVersionLaden('/impressum')).toBe('laeuft-schon');

      expect(seitenwechsel).toHaveBeenCalledTimes(1);
      expect(snackBar.open).not.toHaveBeenCalled();
    });

    it('laedt innerhalb der Sperre nicht noch einmal, sondern zeigt den Hinweis', () => {
      const speicher = speicherAttrappe();
      speicher.setItem(SPERRE_SCHLUESSEL, String(Date.now() - SPERRE_MS + 1000));

      const ausgang = dienst(speicher).neueVersionLaden('/impressum');

      expect(ausgang).toBe('hinweis');
      expect(seitenwechsel).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledOnceWith(HINWEIS_TEXT, HINWEIS_KNOPF, jasmine.any(Object));
    });

    it('laedt nach Ablauf der Sperre wieder automatisch', () => {
      const speicher = speicherAttrappe();
      speicher.setItem(SPERRE_SCHLUESSEL, String(Date.now() - SPERRE_MS - 1));

      expect(dienst(speicher).neueVersionLaden('/impressum')).toBe('neu-geladen');
      expect(seitenwechsel).toHaveBeenCalledOnceWith('/impressum');
    });

    it('zeigt ohne Speicher den Hinweis; erst der Knopf laedt neu', () => {
      const neueVersion = dienst(null);

      expect(neueVersion.neueVersionLaden('/impressum')).toBe('hinweis');
      expect(seitenwechsel).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledOnceWith(HINWEIS_TEXT, HINWEIS_KNOPF, jasmine.any(Object));
      // Unaufdringlich, aber bleibt stehen: keine Dauer
      expect(snackBar.open.calls.mostRecent().args[2]?.duration).toBeUndefined();

      aktion.next();
      expect(seitenwechsel).toHaveBeenCalledOnceWith('/impressum');
    });

    it('zeigt den Hinweis nur einmal, solange er offen ist', () => {
      const neueVersion = dienst(null);

      neueVersion.neueVersionLaden('/impressum');
      neueVersion.neueVersionLaden('/datenschutz');
      expect(snackBar.open).toHaveBeenCalledTimes(1);

      geschlossen.next();
      neueVersion.neueVersionLaden('/datenschutz');
      expect(snackBar.open).toHaveBeenCalledTimes(2);
    });

    it('zeigt den Hinweis, wenn der Speicher beim Lesen wirft', () => {
      const speicher = speicherAttrappe();
      spyOn(speicher, 'getItem').and.throwError(new DOMException('gesperrt', 'SecurityError'));

      expect(dienst(speicher).neueVersionLaden('/impressum')).toBe('hinweis');
      expect(seitenwechsel).not.toHaveBeenCalled();
    });

    it('zeigt den Hinweis, wenn der Speicher beim Schreiben wirft (voll)', () => {
      const speicher = speicherAttrappe();
      spyOn(speicher, 'setItem').and.throwError(new DOMException('voll', 'QuotaExceededError'));

      expect(dienst(speicher).neueVersionLaden('/impressum')).toBe('hinweis');
      expect(seitenwechsel).not.toHaveBeenCalled();
    });

    it('zeigt den Hinweis, wenn der Speicher Schreiben still schluckt', () => {
      const speicher = speicherAttrappe();
      spyOn(speicher, 'setItem').and.stub();

      expect(dienst(speicher).neueVersionLaden('/impressum')).toBe('hinweis');
      expect(seitenwechsel).not.toHaveBeenCalled();
    });

    it('nimmt bei einem Navigationsfehler das Ziel der Navigation', () => {
      const neueVersion = dienst(speicherAttrappe());

      neueVersion.beiNavigationsfehler(
        new NavigationError(1, '/beitrag/7?von=suche', new TypeError('Importing a module script failed.')),
      );

      expect(seitenwechsel).toHaveBeenCalledOnceWith('/beitrag/7?von=suche');
    });

    it('laesst andere Navigationsfehler in Ruhe', () => {
      const neueVersion = dienst(speicherAttrappe());

      neueVersion.beiNavigationsfehler(new NavigationError(1, '/beitrag/7', new Error('Guard kaputt')));

      expect(seitenwechsel).not.toHaveBeenCalled();
      expect(snackBar.open).not.toHaveBeenCalled();
    });

    it('der globale ErrorHandler laedt bei einem Ladefehler neu, statt eine Fehlermeldung zu zeigen', () => {
      dienst(speicherAttrappe());
      const handler = TestBed.runInInjectionContext(() => new GlobalErrorHandler(snackBar, TestBed.inject(NeueVersionService)));

      handler.handleError({ rejection: new TypeError('Failed to fetch dynamically imported module: x') } as unknown as Error);

      expect(seitenwechsel).toHaveBeenCalledOnceWith(window.location.href);
      expect(snackBar.open).not.toHaveBeenCalled();
    });
  });
});
