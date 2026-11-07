import { DestroyRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router } from '@angular/router';
import { MatDialog, MatDialogState } from '@angular/material/dialog';
import { BehaviorSubject, Subject } from 'rxjs';
import { take } from 'rxjs/operators';
import { AuthService, UserInfo } from '../auth/auth.service';
import { RundgangService } from './rundgang.service';
import { BEISPIEL_AUSSAGE, MITMACHEN_ANGEBOT, WILLKOMMEN } from './rundgang-daten';
import { MITMACHEN_SCHLUESSEL, WILLKOMMEN_SCHLUESSEL } from './rundgang-merker';

describe('RundgangService', () => {
  let service: RundgangService;
  let events: Subject<unknown>;
  let router: jasmine.SpyObj<Router> & { url: string };
  let dialog: jasmine.SpyObj<MatDialog>;
  let geschlossen: Subject<string | undefined>;
  let userInfo: BehaviorSubject<UserInfo | null>;
  let zerstoert: () => void;

  const angemeldet: UserInfo = { isAuthenticated: true, userId: 'u1', userName: 'Test', claims: null };

  beforeEach(() => {
    localStorage.removeItem(WILLKOMMEN_SCHLUESSEL);
    localStorage.removeItem(MITMACHEN_SCHLUESSEL);
    events = new Subject();
    geschlossen = new Subject();
    userInfo = new BehaviorSubject<UserInfo | null>(null);
    router = Object.assign(
      jasmine.createSpyObj<Router>('Router', ['navigateByUrl', 'createUrlTree', 'serializeUrl']),
      { url: '/search', events },
    );
    router.createUrlTree.and.callFake(((befehle: unknown[], extras?: { queryParams?: Record<string, string> }) => ({
      pfad: befehle[0],
      query: extras?.queryParams,
    })) as never);
    router.serializeUrl.and.callFake(((baum: { pfad: string; query?: Record<string, string> }) => {
      const q = new URLSearchParams(baum.query ?? {}).toString();
      return q ? `${baum.pfad}?${q}` : baum.pfad;
    }) as never);
    router.navigateByUrl.and.resolveTo(true);
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    // Wie Material: close() startet nur die Animation, afterClosed kommt danach (geschlossen.next).
    dialog.open.and.callFake((() => {
      let zustand = MatDialogState.OPEN;
      geschlossen.pipe(take(1)).subscribe(() => (zustand = MatDialogState.CLOSED));
      return {
        afterClosed: () => geschlossen.pipe(take(1)),
        close: () => (zustand = MatDialogState.CLOSING),
        getState: () => zustand,
      };
    }) as never);

    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        { provide: MatDialog, useValue: dialog },
        {
          provide: AuthService,
          useValue: { userInfo$: userInfo, getUserInfo: () => userInfo.value },
        },
      ],
    });
    service = TestBed.inject(RundgangService);
    const hooks: Array<() => void> = [];
    zerstoert = () => hooks.forEach((h) => h());
    service.beobachten({ onDestroy: (h: () => void) => hooks.push(h) } as unknown as DestroyRef);
  });

  afterEach(() => {
    zerstoert();
    localStorage.removeItem(WILLKOMMEN_SCHLUESSEL);
    localStorage.removeItem(MITMACHEN_SCHLUESSEL);
  });

  function navigiert(url: string): void {
    router.url = url;
    events.next(new NavigationEnd(1, url, url));
  }

  function angebotDaten(aufruf = 0): unknown {
    return (dialog.open.calls.argsFor(aufruf)[1] as { data: unknown }).data;
  }

  describe('Erstbesuch', () => {
    it('zeigt beim ersten Besuch der Startseite das Willkommen', () => {
      navigiert('/search');
      expect(dialog.open).toHaveBeenCalledTimes(1);
      expect(angebotDaten()).toBe(WILLKOMMEN);
    });

    it('zeigt es beim zweiten Besuch nicht mehr, auch nach „Später“ oder Escape', () => {
      navigiert('/search');
      geschlossen.next(undefined); // Escape
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBe('1');

      dialog.open.calls.reset();
      const zweiter = TestBed.inject(RundgangService);
      zweiter.beobachten({ onDestroy: () => undefined } as unknown as DestroyRef);
      navigiert('/search');
      expect(dialog.open).not.toHaveBeenCalled();
    });

    it('legt sich nicht über Einladung, Anmeldung oder Rechtstexte', () => {
      navigiert('/einladung/abc');
      navigiert('/login');
      navigiert('/datenschutz');
      expect(dialog.open).not.toHaveBeenCalled();
    });

    it('erscheint ohne Speicher (privates Fenster) eben wieder, ohne Fehler', () => {
      spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');
      spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');
      navigiert('/search');
      expect(() => geschlossen.next('spaeter')).not.toThrow();
      expect(dialog.open).toHaveBeenCalledTimes(1);
    });

    it('startet mit „Rundgang starten“ den Rundgang Antwort finden auf der Startseite', () => {
      navigiert('/search');
      geschlossen.next('starten');
      const stand = service.aktiv();
      expect(stand?.rundgang.id).toBe('antwort-finden');
      expect(stand?.index).toBe(0);
      expect(router.navigateByUrl).not.toHaveBeenCalled(); // schon auf /search
    });

    it('startet mit „Später“ keinen Rundgang', () => {
      navigiert('/search');
      geschlossen.next('spaeter');
      expect(service.aktiv()).toBeNull();
    });
  });

  describe('Rundgang', () => {
    it('führt für die Treffer-Schritte über die Beispielsuche, Schritt erst nach dem Laden', async () => {
      await service.starten('antwort-finden');
      const weiter = service.weiter();
      expect(service.aktiv()?.index).toBe(0);
      await weiter;
      expect(router.navigateByUrl).toHaveBeenCalledWith(
        jasmine.objectContaining({ pfad: '/result', query: { searchQuery: BEISPIEL_AUSSAGE } }) as never,
      );
      expect(service.aktiv()?.index).toBe(1);
    });

    it('blättert zurück, aber nicht vor den ersten Schritt', async () => {
      await service.starten('antwort-finden');
      await service.zurueck();
      expect(service.aktiv()?.index).toBe(0);
      await service.weiter();
      await service.zurueck();
      expect(service.aktiv()?.index).toBe(0);
    });

    it('endet nach dem letzten Schritt mit Weiter', async () => {
      await service.starten('mitmachen');
      for (let i = 0; i < 4; i++) await service.weiter();
      expect(service.aktiv()).toBeNull();
    });

    it('lässt sich jederzeit beenden', async () => {
      await service.starten('antwort-finden');
      await service.weiter();
      service.beenden();
      expect(service.aktiv()).toBeNull();
    });

    it('zeigt einen Schritt nicht mehr, wenn während des Ladens beendet wurde', async () => {
      await service.starten('antwort-finden');
      const weiter = service.weiter();
      service.beenden();
      await weiter;
      expect(service.aktiv()).toBeNull();
    });

    it('lässt sich wieder aufrufen, auch wenn das Willkommen schon gesehen ist', async () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      await service.starten('antwort-finden');
      expect(service.aktiv()?.rundgang.id).toBe('antwort-finden');
    });
  });

  describe('Mitmachen nach der ersten Anmeldung', () => {
    it('bietet den Rundgang Mitmachen einmal an', () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      navigiert('/search');
      userInfo.next(angemeldet);
      expect(dialog.open).toHaveBeenCalledTimes(1);
      expect(angebotDaten()).toBe(MITMACHEN_ANGEBOT);
      geschlossen.next('spaeter');
      expect(localStorage.getItem(MITMACHEN_SCHLUESSEL)).toBe('1');

      userInfo.next(angemeldet);
      expect(dialog.open).toHaveBeenCalledTimes(1);
    });

    it('bietet ihn nach einer Einladung auch ohne Willkommen an, wenn die erste Seite keine Startseite ist', () => {
      userInfo.next(angemeldet);
      expect(dialog.open).not.toHaveBeenCalled(); // erste Seite steht noch nicht fest
      navigiert('/contribute');
      expect(dialog.open).toHaveBeenCalledTimes(1);
      expect(angebotDaten()).toBe(MITMACHEN_ANGEBOT);
    });

    it('legt sich nicht über Anmeldung, Einladung oder Rechtstexte, sondern kommt mit der nächsten Seite', () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      navigiert('/einladung/abc');
      userInfo.next(angemeldet);
      navigiert('/datenschutz');
      expect(dialog.open).not.toHaveBeenCalled();
      navigiert('/contribute');
      expect(dialog.open).toHaveBeenCalledTimes(1);
      expect(angebotDaten()).toBe(MITMACHEN_ANGEBOT);
    });

    it('bietet nichts an, solange niemand angemeldet ist', () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      userInfo.next({ isAuthenticated: false, userId: null, userName: null, claims: null });
      expect(dialog.open).not.toHaveBeenCalled();
    });

    it('wartet, bis Willkommen und Rundgang vorbei sind', () => {
      userInfo.next(angemeldet);
      navigiert('/search');
      expect(dialog.open).toHaveBeenCalledTimes(1);
      expect(angebotDaten()).toBe(WILLKOMMEN);

      geschlossen.next('starten');
      expect(dialog.open).toHaveBeenCalledTimes(1);
      service.beenden();
      expect(dialog.open).toHaveBeenCalledTimes(2);
      expect(angebotDaten(1)).toBe(MITMACHEN_ANGEBOT);
    });

    it('legt sich nicht über einen Rundgang, der noch zu seinem ersten Schritt lädt (#585)', async () => {
      userInfo.next(angemeldet);
      navigiert('/search?code=abc'); // etwa nach der Rückkehr von der Anmeldung
      geschlossen.next('starten'); // Willkommen: Rundgang Antwort finden
      expect(router.navigateByUrl).toHaveBeenCalled();
      navigiert('/search'); // die Navigation des ersten Schritts endet
      expect(dialog.open).toHaveBeenCalledTimes(1);

      await new Promise((fertig) => setTimeout(fertig));
      expect(service.aktiv()?.index).toBe(0);
      await service.weiter(); // Schritt 2 auf den Treffern
      navigiert(`/result?searchQuery=${BEISPIEL_AUSSAGE}`);
      expect(dialog.open).toHaveBeenCalledTimes(1);

      service.beenden();
      expect(dialog.open).toHaveBeenCalledTimes(2);
      expect(angebotDaten(1)).toBe(MITMACHEN_ANGEBOT);
    });

    it('kommt auch nach, wenn der Rundgang schon beim Laden des ersten Schritts beendet wird', async () => {
      userInfo.next(angemeldet);
      navigiert('/search?code=abc');
      geschlossen.next('starten');
      service.beenden();
      await new Promise((fertig) => setTimeout(fertig));
      expect(service.aktiv()).toBeNull();
      expect(dialog.open).toHaveBeenCalledTimes(2);
      expect(angebotDaten(1)).toBe(MITMACHEN_ANGEBOT);
    });

    it('schließt ein offenes Angebot, wenn ein Rundgang startet, und bietet es danach wieder an (#585)', async () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      navigiert('/search');
      userInfo.next(angemeldet);
      expect(angebotDaten()).toBe(MITMACHEN_ANGEBOT);
      const fenster = dialog.open.calls.mostRecent().returnValue;

      await service.starten('antwort-finden'); // etwa über Hilfe
      expect(fenster.getState()).toBe(MatDialogState.CLOSING);
      expect(service.aktiv()?.rundgang.id).toBe('antwort-finden');
      service.beenden(); // noch während der Animation: kein zweites Fenster daneben
      expect(dialog.open).toHaveBeenCalledTimes(1);

      geschlossen.next(undefined); // Animation vorbei
      expect(localStorage.getItem(MITMACHEN_SCHLUESSEL)).toBeNull();
      expect(dialog.open).toHaveBeenCalledTimes(2);
      expect(angebotDaten(1)).toBe(MITMACHEN_ANGEBOT);
    });

    it('lässt die Wahl eines Fensters, das schon schließt, stehen', async () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      navigiert('/search');
      userInfo.next(angemeldet);
      const fenster = dialog.open.calls.mostRecent().returnValue;
      fenster.close('starten'); // Klick auf „Rundgang starten“, Animation läuft
      const schliessen = spyOn(fenster, 'close');

      await service.starten('antwort-finden');
      expect(schliessen).not.toHaveBeenCalled();
    });

    it('zeigt das Willkommen nicht, während ein Rundgang zur Startseite führt, und auch nicht danach (#585)', async () => {
      navigiert('/einladung/abc');
      await service.starten('antwort-finden');
      navigiert('/search');
      expect(dialog.open).not.toHaveBeenCalled();

      service.beenden();
      navigiert(`/result?searchQuery=${BEISPIEL_AUSSAGE}`);
      expect(dialog.open).not.toHaveBeenCalled();
      // Entfällt nur für diesen Besuch
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBeNull();
    });

    it('merkt ein Willkommen, das ein anderer Rundgang ablöst, nicht als gesehen (#585)', async () => {
      navigiert('/search');
      expect(angebotDaten()).toBe(WILLKOMMEN);

      await service.starten('mitmachen');
      geschlossen.next(undefined);
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBeNull();
      expect(service.aktiv()?.rundgang.id).toBe('mitmachen');
      expect(dialog.open).toHaveBeenCalledTimes(1);
    });

    it('merkt ein Willkommen als gesehen, wenn dessen eigener Rundgang startet', async () => {
      navigiert('/search');
      await service.starten('antwort-finden');
      geschlossen.next(undefined);
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBe('1');
    });

    it('startet mit „Rundgang starten“ den Rundgang Mitmachen', () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      navigiert('/search');
      userInfo.next(angemeldet);
      geschlossen.next('starten');
      expect(service.aktiv()?.rundgang.id).toBe('mitmachen');
    });
  });
});
