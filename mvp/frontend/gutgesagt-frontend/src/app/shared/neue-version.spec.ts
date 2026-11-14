import { APP_BASE_HREF } from '@angular/common';
import { ErrorHandler } from '@angular/core';
import { TestBed, fakeAsync, flush, flushMicrotasks, tick } from '@angular/core/testing';
import { MatSnackBar, MatSnackBarDismiss, MatSnackBarRef, TextOnlySnackBar } from '@angular/material/snack-bar';
import { NavigationError, Router, provideRouter, withNavigationErrorHandler } from '@angular/router';
import { inject } from '@angular/core';
import { Subject } from 'rxjs';

import {
  BROWSER,
  Browser,
  HINWEIS_KNOPF,
  HINWEIS_TEXT,
  NETZFEHLER_TEXT,
  NeueVersionService,
  OFFLINE_TEXT,
  Ort,
  PRUEFUNG_MS,
  SPERRE_MS,
  SPERRE_SCHLUESSEL,
  Verlauf,
  WECHSEL_FRIST_MS,
  chunkAdresse,
  hartWechseln,
  istLadefehler,
  ladefehlerKern,
} from './neue-version';
import { GlobalErrorHandler } from '../services/error-handler.service';

const URSPRUNG = 'https://gutgesagt.example';
const CHUNK = `${URSPRUNG}/chunk-ABC123.js`;
const STARTSEITE = `${URSPRUNG}/index.html`;
const HEAD = jasmine.objectContaining({ method: 'HEAD', cache: 'no-store' });
const chrome = (adresse = CHUNK) => new TypeError(`Failed to fetch dynamically imported module: ${adresse}`);
const safari = () => new TypeError('Importing a module script failed.');

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
      ['Chrome', chrome()],
      ['Firefox', new TypeError(`error loading dynamically imported module: ${CHUNK}`)],
      ['Safari', safari()],
      ['@defer (Code)', Object.assign(new Error('NG0750'), { code: -750 })],
      ['@defer (Meldung, Produktion)', new Error('NG0750')],
      ['@defer (Meldung, Entwicklung)', new Error('NG0750: Loading dependencies for `@defer` block failed, but no `@error` block was configured.')],
      ['unbehandelte Promise-Ablehnung', { rejection: safari() }],
      ['NavigationError', new NavigationError(1, '/impressum', chrome())],
      ['Text', `Failed to fetch dynamically imported module: ${CHUNK}`],
    ];
    for (const [browser, fehler] of meldungen) {
      it(`erkennt ${browser}`, () => {
        expect(istLadefehler(fehler)).toBeTrue();
      });
    }

    const andere: Array<[string, unknown]> = [
      ['HTTP-Fehler', { status: 404, message: 'Http failure response for /api/x: 404 Not Found' }],
      ['Netzfehler beim fetch', new TypeError('Failed to fetch')],
      ['anderer Angular-Fehler', Object.assign(new Error('NG07500'), { code: -7500 })],
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

    it('nimmt bei einer zone.js-Huelle den inneren Fehler als Kern', () => {
      const fehler = safari();
      const huelle = Object.assign(new Error(`Uncaught (in promise): ${fehler.message}`), { rejection: fehler });
      expect(ladefehlerKern(huelle)).toBe(fehler);
    });

    it('haengt bei einem Fehler, der auf sich selbst zeigt, nicht', () => {
      const fehler: { message: string; error?: unknown; rejection?: unknown } = { message: 'x' };
      fehler.error = fehler;
      fehler.rejection = fehler;
      expect(istLadefehler(fehler)).toBeFalse();
    });
  });

  describe('chunkAdresse', () => {
    it('liest die Adresse aus der Meldung von Chrome und Firefox', () => {
      expect(chunkAdresse(chrome(), `${URSPRUNG}/search`)).toBe(CHUNK);
      expect(chunkAdresse({ rejection: new TypeError(`error loading dynamically imported module: ${CHUNK}`) }, URSPRUNG)).toBe(CHUNK);
    });

    it('nennt keine fremde Adresse und keine, wenn die Meldung keine hat (Safari, @defer)', () => {
      expect(chunkAdresse(chrome('https://fremd.example/chunk-X.js'), URSPRUNG)).toBeNull();
      expect(chunkAdresse(safari(), URSPRUNG)).toBeNull();
      expect(chunkAdresse(new Error('NG0750'), URSPRUNG)).toBeNull();
    });
  });

  describe('hartWechseln', () => {
    function ort(href: string): jasmine.SpyObj<Ort> {
      const url = new URL(href);
      return Object.assign(jasmine.createSpyObj<Ort>('Ort', ['assign', 'reload']), {
        href,
        pathname: url.pathname,
        search: url.search,
      });
    }
    const verlauf = () => Object.assign(jasmine.createSpyObj<Verlauf>('Verlauf', ['replaceState']), { state: { navigationId: 3 } });

    it('wechselt auf einen anderen Pfad mit assign', () => {
      const o = ort(`${URSPRUNG}/search`);
      const v = verlauf();
      hartWechseln('/impressum', o, v);
      expect(o.assign).toHaveBeenCalledOnceWith(`${URSPRUNG}/impressum`);
      expect(o.reload).not.toHaveBeenCalled();
    });

    it('wechselt bei anderer Query mit assign', () => {
      const o = ort(`${URSPRUNG}/result?q=a`);
      hartWechseln('/result?q=b', o, verlauf());
      expect(o.assign).toHaveBeenCalledOnceWith(`${URSPRUNG}/result?q=b`);
    });

    it('laedt bei gleichem Pfad und gleicher Query neu, auch mit Fragment (assign waere nur ein Sprung)', () => {
      const o = ort(`${URSPRUNG}/datenschutz`);
      const v = verlauf();
      hartWechseln('/datenschutz#suchanfragen', o, v);
      expect(v.replaceState).toHaveBeenCalledOnceWith({ navigationId: 3 }, '', `${URSPRUNG}/datenschutz#suchanfragen`);
      expect(o.reload).toHaveBeenCalledTimes(1);
      expect(o.assign).not.toHaveBeenCalled();
    });
  });

  describe('NeueVersionService', () => {
    let browser: jasmine.SpyObj<Browser>;
    let speicher: Storage | null;
    let online: boolean;
    let snackBar: jasmine.SpyObj<MatSnackBar> & { _openedSnackBarRef: MatSnackBarRef<unknown> | null };
    let refs: Array<{ aktion: Subject<void>; geschlossen: Subject<MatSnackBarDismiss> }>;

    function dienst(): NeueVersionService {
      TestBed.configureTestingModule({
        providers: [
          { provide: BROWSER, useValue: browser },
          { provide: MatSnackBar, useValue: snackBar },
        ],
      });
      return TestBed.inject(NeueVersionService);
    }

    function antwort(status: number): Promise<Response> {
      return Promise.resolve(new Response(null, { status }));
    }

    beforeEach(() => {
      speicher = speicherAttrappe();
      online = true;
      browser = jasmine.createSpyObj<Browser>('Browser', ['wechseln', 'speicher', 'online', 'abrufen', 'adresse', 'startseite']);
      browser.speicher.and.callFake(() => speicher);
      browser.online.and.callFake(() => online);
      browser.adresse.and.returnValue(`${URSPRUNG}/search`);
      browser.startseite.and.returnValue(STARTSEITE);
      // Nach dem Deploy: alte Chunks fehlen, die index.html ist da.
      browser.abrufen.and.callFake((url: string) => antwort(url === STARTSEITE ? 200 : 404));
      refs = [];
      snackBar = Object.assign(jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']), { _openedSnackBarRef: null });
      snackBar.open.and.callFake(() => {
        const r = { aktion: new Subject<void>(), geschlossen: new Subject<MatSnackBarDismiss>() };
        refs.push(r);
        return { onAction: () => r.aktion, afterDismissed: () => r.geschlossen } as unknown as MatSnackBarRef<TextOnlySnackBar>;
      });
    });

    const hinweise = () => snackBar.open.calls.allArgs().filter(([text]) => text === HINWEIS_TEXT);

    it('laedt das Ziel hart, wenn der Chunk auf dem Server fehlt (HEAD 404), und setzt den Merker', async () => {
      const ausgang = await dienst().neueVersionLaden('/impressum', chrome());

      expect(ausgang).toBe('neu-geladen');
      expect(browser.abrufen).toHaveBeenCalledOnceWith(CHUNK, HEAD);
      expect(browser.wechseln).toHaveBeenCalledOnceWith('/impressum');
      expect(speicher!.getItem(SPERRE_SCHLUESSEL)).not.toBeNull();
      expect(snackBar.open).not.toHaveBeenCalled();
    });

    for (const [fall, fehler] of [
      ['Safari', safari()],
      ['@defer', Object.assign(new Error('NG0750'), { code: -750 })],
    ] as const) {
      it(`prueft ohne Adresse in der Meldung (${fall}) die eigene index.html und laedt bei 2xx`, async () => {
        expect(await dienst().neueVersionLaden('/impressum', fehler)).toBe('neu-geladen');
        expect(browser.abrufen).toHaveBeenCalledOnceWith(STARTSEITE, HEAD);
        expect(browser.wechseln).toHaveBeenCalledOnceWith('/impressum');
      });
    }

    for (const [fall, abruf] of [
      ['die index.html antwortet mit 503', () => antwort(503)],
      ['die index.html antwortet mit 404', () => antwort(404)],
      ['die Pruefung der index.html scheitert am Netz', () => Promise.reject(new TypeError('Load failed'))],
    ] as const) {
      it(`ohne Adresse in der Meldung kein Wechsel, wenn ${fall}`, async () => {
        browser.abrufen.and.callFake(abruf);

        expect(await dienst().neueVersionLaden('/impressum', safari())).toBe('netzfehler');

        expect(browser.wechseln).not.toHaveBeenCalled();
        expect(snackBar.open).toHaveBeenCalledOnceWith(NETZFEHLER_TEXT, 'Schließen', jasmine.any(Object));
      });
    }

    it('bricht eine Pruefung, die nie antwortet, nach der Frist ab und wechselt nicht', fakeAsync(() => {
      let signal: AbortSignal | undefined;
      browser.abrufen.and.callFake((_url: string, init: RequestInit) => {
        signal = init.signal ?? undefined;
        return new Promise<Response>(() => undefined);
      });
      let ausgang = '';

      void dienst().neueVersionLaden('/impressum', chrome()).then((a) => (ausgang = a));
      tick(PRUEFUNG_MS - 1);
      expect(ausgang).toBe('');
      tick(1);
      flushMicrotasks();

      expect(ausgang).toBe('netzfehler');
      expect(signal?.aborted).toBeTrue();
      expect(browser.wechseln).not.toHaveBeenCalled();
    }));

    it('offline: kein Wechsel, keine Pruefung, die Meldung „Keine Internetverbindung“', async () => {
      online = false;

      expect(await dienst().neueVersionLaden('/impressum', chrome())).toBe('netzfehler');

      expect(browser.wechseln).not.toHaveBeenCalled();
      expect(browser.abrufen).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledOnceWith(OFFLINE_TEXT, 'Schließen', jasmine.any(Object));
      expect(speicher!.getItem(SPERRE_SCHLUESSEL)).toBeNull();
    });

    for (const [fall, abruf] of [
      ['der Chunk ist da (200): Netzabbruch, kein Deploy', () => antwort(200)],
      ['der Server antwortet auf den Chunk mit 503', () => antwort(503)],
      ['die Pruefung des Chunks scheitert am Netz', () => Promise.reject(new TypeError('Failed to fetch'))],
    ] as const) {
      it(`kein Wechsel, wenn ${fall}`, async () => {
        browser.abrufen.and.callFake(abruf);

        expect(await dienst().neueVersionLaden('/impressum', chrome())).toBe('netzfehler');

        expect(browser.wechseln).not.toHaveBeenCalled();
        expect(snackBar.open).toHaveBeenCalledOnceWith(NETZFEHLER_TEXT, 'Schließen', jasmine.any(Object));
      });
    }

    it('behandelt denselben Fehler nur einmal (Router und ErrorHandler melden ihn beide)', async () => {
      const neueVersion = dienst();
      const fehler = chrome();

      const erst = neueVersion.neueVersionLaden('/impressum', fehler);
      expect(await neueVersion.neueVersionLaden(window.location.href, { rejection: fehler })).toBe('schon-behandelt');
      await erst;

      expect(browser.abrufen).toHaveBeenCalledTimes(1);
      expect(browser.wechseln).toHaveBeenCalledTimes(1);
    });

    it('wechselt waehrend eines laufenden Wechsels nicht noch einmal, danach nur mit Hinweis', fakeAsync(() => {
      const neueVersion = dienst();
      let ausgang = '';

      void neueVersion.neueVersionLaden('/impressum', safari());
      flushMicrotasks();
      void neueVersion.neueVersionLaden('/impressum', safari()).then((a) => (ausgang = a));
      flushMicrotasks();
      expect(ausgang).toBe('laeuft-schon');

      // Die Seite blieb stehen (Wechsel abgebrochen): Der Merker steht noch, also nur der Hinweis.
      tick(WECHSEL_FRIST_MS - 1);
      void neueVersion.neueVersionLaden('/impressum', safari()).then((a) => (ausgang = a));
      flushMicrotasks();
      expect(ausgang).toBe('laeuft-schon');

      tick(1);
      void neueVersion.neueVersionLaden('/impressum', safari()).then((a) => (ausgang = a));
      flushMicrotasks();
      expect(ausgang).toBe('hinweis');
      expect(browser.wechseln).toHaveBeenCalledTimes(1);
      flush();
    }));

    it('laedt nicht noch einmal, solange der Merker steht und juenger als zehn Minuten ist (langsamer Start)', async () => {
      speicher!.setItem(SPERRE_SCHLUESSEL, String(Date.now() - SPERRE_MS + 60_000));

      expect(await dienst().neueVersionLaden('/impressum', chrome())).toBe('hinweis');

      expect(browser.wechseln).not.toHaveBeenCalled();
      expect(hinweise()).toEqual([[HINWEIS_TEXT, HINWEIS_KNOPF, jasmine.any(Object)]]);
    });

    for (const [fall, wert] of [
      ['aelter als zehn Minuten', () => String(Date.now() - SPERRE_MS)],
      ['aus der Zukunft', () => String(Date.now() + 60_000)],
      ['unlesbar', () => 'kaputt'],
    ] as const) {
      it(`ein Merker ${fall} zaehlt als abgelaufen: wieder automatisch neu laden`, async () => {
        speicher!.setItem(SPERRE_SCHLUESSEL, wert());

        expect(await dienst().neueVersionLaden('/impressum', chrome())).toBe('neu-geladen');

        expect(Number(speicher!.getItem(SPERRE_SCHLUESSEL))).toBeCloseTo(Date.now(), -3);
      });
    }

    it('dauerhaft kaputter @defer-Chunk: hoechstens ein automatisches Neuladen je zehn Minuten', fakeAsync(() => {
      const neueVersion = dienst();
      const defer = () => Object.assign(new Error('NG0750'), { code: -750 });
      const ausgaenge: string[] = [];
      const fehlerNach = (ms: number) => {
        tick(ms);
        void neueVersion.beiFehler(defer());
        flushMicrotasks();
        ausgaenge.push(browser.wechseln.calls.count() + ':' + hinweise().length);
      };

      fehlerNach(0); // neu geladen
      // Die neu geladene Seite laeuft eine Weile, dann scheitert der @defer-Block wieder: jede Minute.
      for (let minute = 1; minute < 10; minute++) {
        fehlerNach(60_000);
      }
      expect(browser.wechseln).toHaveBeenCalledTimes(1);

      fehlerNach(60_000); // zehn Minuten nach dem ersten: wieder automatisch
      expect(browser.wechseln).toHaveBeenCalledTimes(2);
      flush();
    }));

    it('raeumt einen stehenden Merker beim Start ab, sobald er zehn Minuten alt ist', fakeAsync(() => {
      const merker = String(Date.now() - SPERRE_MS + 60_000);
      speicher!.setItem(SPERRE_SCHLUESSEL, merker);
      dienst().aufraeumen();

      tick(59_999);
      expect(speicher!.getItem(SPERRE_SCHLUESSEL)).toBe(merker);
      tick(1);
      expect(speicher!.getItem(SPERRE_SCHLUESSEL)).toBeNull();
    }));

    it('raeumt einen abgelaufenen Merker beim Start gleich ab', () => {
      speicher!.setItem(SPERRE_SCHLUESSEL, String(Date.now() - SPERRE_MS - 1));
      dienst().aufraeumen();

      expect(speicher!.getItem(SPERRE_SCHLUESSEL)).toBeNull();
    });

    it('der Merker bleibt nach einem Netzfehler stehen, wie er war', async () => {
      const merker = String(Date.now());
      speicher!.setItem(SPERRE_SCHLUESSEL, merker);
      online = false;

      await dienst().neueVersionLaden('/impressum', chrome());

      expect(speicher!.getItem(SPERRE_SCHLUESSEL)).toBe(merker);
    });

    it('zeigt ohne Speicher den Hinweis; erst der Knopf laedt neu', async () => {
      speicher = null;

      expect(await dienst().neueVersionLaden('/impressum', chrome())).toBe('hinweis');
      expect(browser.wechseln).not.toHaveBeenCalled();
      // Unaufdringlich, aber bleibt stehen: keine Dauer
      expect(snackBar.open.calls.mostRecent().args[2]?.duration).toBeUndefined();

      refs[0].aktion.next();
      expect(browser.wechseln).toHaveBeenCalledOnceWith('/impressum');
    });

    it('zeigt den Hinweis nur einmal und laedt auf das zuletzt gewollte Ziel', async () => {
      speicher = null;
      const neueVersion = dienst();

      await neueVersion.neueVersionLaden('/impressum', chrome());
      await neueVersion.neueVersionLaden('/datenschutz', chrome(`${URSPRUNG}/chunk-DEF.js`));
      expect(hinweise().length).toBe(1);

      refs[0].aktion.next();
      expect(browser.wechseln).toHaveBeenCalledOnceWith('/datenschutz');
    });

    it('zeigt den Hinweis wieder, wenn eine andere Snackbar ihn verdraengt hat und geschlossen ist', async () => {
      speicher = null;
      await dienst().neueVersionLaden('/impressum', chrome());
      const andere = new Subject<MatSnackBarDismiss>();
      snackBar._openedSnackBarRef = { afterDismissed: () => andere } as unknown as MatSnackBarRef<unknown>;

      refs[0].geschlossen.next({ dismissedByAction: false });
      expect(hinweise().length).toBe(1);
      // Material setzt die offene Snackbar beim Schliessen zurueck, bevor andere davon hoeren.
      snackBar._openedSnackBarRef = null;
      andere.next({ dismissedByAction: false });

      expect(hinweise().length).toBe(2);
    });

    it('wartet auch eine zweite fremde Snackbar ab, bevor der Hinweis zurueckkommt', async () => {
      speicher = null;
      await dienst().neueVersionLaden('/impressum', chrome());
      const erste = new Subject<MatSnackBarDismiss>();
      const zweite = new Subject<MatSnackBarDismiss>();
      snackBar._openedSnackBarRef = { afterDismissed: () => erste } as unknown as MatSnackBarRef<unknown>;
      refs[0].geschlossen.next({ dismissedByAction: false });

      snackBar._openedSnackBarRef = { afterDismissed: () => zweite } as unknown as MatSnackBarRef<unknown>;
      erste.next({ dismissedByAction: false });
      expect(hinweise().length).toBe(1);

      snackBar._openedSnackBarRef = null;
      zweite.next({ dismissedByAction: false });
      expect(hinweise().length).toBe(2);
    });

    for (const [fall, ohne] of [
      ['den Getter gibt es nicht mehr', (sb: object) => delete (sb as { _openedSnackBarRef?: unknown })._openedSnackBarRef],
      ['der Getter wirft', (sb: object) => Object.defineProperty(sb, '_openedSnackBarRef', { get: () => { throw new Error('weg'); } })],
      ['er liefert etwas ohne afterDismissed', (sb: object) => ((sb as { _openedSnackBarRef: unknown })._openedSnackBarRef = {})],
    ] as const) {
      it(`degradiert still, wenn ${fall}: kein Fehler, der Hinweis kommt nicht zurueck`, async () => {
        speicher = null;
        await dienst().neueVersionLaden('/impressum', chrome());
        ohne(snackBar);

        expect(() => refs[0].geschlossen.next({ dismissedByAction: false })).not.toThrow();

        expect(hinweise().length).toBe(1);
      });
    }

    it('zeigt den Hinweis gleich wieder, wenn er ohne andere Snackbar geschlossen wurde', async () => {
      speicher = null;
      await dienst().neueVersionLaden('/impressum', chrome());

      refs[0].geschlossen.next({ dismissedByAction: false });

      expect(hinweise().length).toBe(2);
    });

    it('zeigt den Hinweis nach „Neu laden“ nicht wieder', async () => {
      speicher = null;
      await dienst().neueVersionLaden('/impressum', chrome());

      refs[0].geschlossen.next({ dismissedByAction: true });

      expect(hinweise().length).toBe(1);
    });

    for (const [fall, kaputt] of [
      ['beim Lesen wirft', (s: Storage) => spyOn(s, 'getItem').and.throwError(new DOMException('gesperrt', 'SecurityError'))],
      ['beim Schreiben wirft (voll)', (s: Storage) => spyOn(s, 'setItem').and.throwError(new DOMException('voll', 'QuotaExceededError'))],
      ['Schreiben still schluckt', (s: Storage) => spyOn(s, 'setItem').and.stub()],
    ] as const) {
      it(`zeigt den Hinweis, wenn der Speicher ${fall}`, async () => {
        kaputt(speicher!);
        expect(await dienst().neueVersionLaden('/impressum', chrome())).toBe('hinweis');
        expect(browser.wechseln).not.toHaveBeenCalled();
      });
    }

    it('laesst andere Navigationsfehler in Ruhe', () => {
      dienst().beiNavigationsfehler(new NavigationError(1, '/beitrag/7', new Error('Guard kaputt')));

      expect(browser.wechseln).not.toHaveBeenCalled();
      expect(snackBar.open).not.toHaveBeenCalled();
    });
  });

  describe('mit echtem Router und globalem ErrorHandler', () => {
    let browser: jasmine.SpyObj<Browser>;
    let speicher: Storage;
    let snackBar: jasmine.SpyObj<MatSnackBar>;
    let aktion: Subject<void>;

    beforeEach(() => {
      browser = jasmine.createSpyObj<Browser>('Browser', ['wechseln', 'speicher', 'online', 'abrufen', 'adresse', 'startseite']);
      speicher = speicherAttrappe();
      browser.speicher.and.returnValue(speicher);
      browser.online.and.returnValue(true);
      browser.adresse.and.returnValue(`${URSPRUNG}/search`);
      browser.startseite.and.returnValue(STARTSEITE);
      browser.abrufen.and.callFake((url: string) => Promise.resolve(new Response(null, { status: url === STARTSEITE ? 200 : 404 })));
      aktion = new Subject<void>();
      snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
      snackBar.open.and.returnValue({
        onAction: () => aktion,
        afterDismissed: () => new Subject<MatSnackBarDismiss>(),
      } as unknown as MatSnackBarRef<TextOnlySnackBar>);
    });

    /** Navigiert auf ``ziel``, dessen Chunk mit ``fehler`` scheitert; die Ablehnung kommt wie bei zone.js beim ErrorHandler an. */
    async function navigieren(ziel: string, fehler: Error): Promise<void> {
      TestBed.configureTestingModule({
        providers: [
          { provide: APP_BASE_HREF, useValue: '/' },
          provideRouter(
            [{ path: 'x', loadComponent: () => Promise.reject(fehler) }],
            withNavigationErrorHandler((e) => inject(NeueVersionService).beiNavigationsfehler(e)),
          ),
          { provide: ErrorHandler, useClass: GlobalErrorHandler },
          { provide: BROWSER, useValue: browser },
          { provide: MatSnackBar, useValue: snackBar },
        ],
      });
      const router = TestBed.inject(Router);
      const errorHandler = TestBed.inject(ErrorHandler);

      // Die abgelehnte Navigation landet wie bei einem routerLink im globalen ErrorHandler, in der Huelle von zone.js.
      await router
        .navigateByUrl(ziel)
        .catch(
          (e: Error) =>
            // Erst nach dem Router: Der ErrorHandler darf auch spaet nichts ueberschreiben oder doppelt melden.
            new Promise<void>((fertig) =>
              setTimeout(() => {
                errorHandler.handleError(Object.assign(new Error(`Uncaught (in promise): ${e.message}`), { rejection: e }));
                fertig();
              }, 10),
            ),
        );
      await new Promise((fertig) => setTimeout(fertig, 10));
    }

    it('ein fehlender Chunk fuehrt zu genau einem Seitenwechsel aufs Ziel, ohne Fehlermeldung', async () => {
      await navigieren('/x?a=1#f', chrome());

      expect(browser.wechseln).toHaveBeenCalledOnceWith('/x?a=1#f');
      expect(browser.abrufen).toHaveBeenCalledTimes(1);
      expect(snackBar.open).not.toHaveBeenCalled();
    });

    it('Safari bei stehendem Merker: ein Hinweis, und „Neu laden“ fuehrt aufs Ziel, nicht auf die aktuelle Seite', async () => {
      speicher.setItem(SPERRE_SCHLUESSEL, String(Date.now()));

      await navigieren('/x?a=1#f', safari());

      expect(snackBar.open).toHaveBeenCalledOnceWith(HINWEIS_TEXT, HINWEIS_KNOPF, jasmine.any(Object));
      aktion.next();
      expect(browser.wechseln).toHaveBeenCalledOnceWith('/x?a=1#f');
    });

    it('offline: nur die Meldung „Keine Internetverbindung“, keine zweite aus dem ErrorHandler', async () => {
      browser.online.and.returnValue(false);

      await navigieren('/x?a=1#f', safari());

      expect(snackBar.open).toHaveBeenCalledOnceWith(OFFLINE_TEXT, 'Schließen', jasmine.any(Object));
      expect(browser.wechseln).not.toHaveBeenCalled();
    });
  });
});
