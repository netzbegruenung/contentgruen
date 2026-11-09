import { DestroyRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router } from '@angular/router';
import { BehaviorSubject, Subject } from 'rxjs';
import { AuthService, UserInfo } from '../auth/auth.service';
import { Art9EinwilligungService } from '../services/art9-einwilligung.service';
import { RundgangService } from './rundgang.service';
import { MITMACHEN_ANGEBOT, RUNDGAENGE, WILLKOMMEN } from './rundgang-daten';
import { STARTBEISPIEL } from '../shared/startbeispiel';
import { MITMACHEN_SCHLUESSEL, WILLKOMMEN_SCHLUESSEL } from './rundgang-merker';

describe('RundgangService', () => {
  let service: RundgangService;
  let events: Subject<unknown>;
  let router: jasmine.SpyObj<Router> & { url: string };
  let userInfo: BehaviorSubject<UserInfo | null>;
  let geklaert: BehaviorSubject<string | null>;
  let zerstoert: () => void;

  const angemeldet: UserInfo = { isAuthenticated: true, userId: 'u1', userName: 'Test', claims: null };
  const besucher: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  beforeEach(() => {
    localStorage.removeItem(WILLKOMMEN_SCHLUESSEL);
    localStorage.removeItem(MITMACHEN_SCHLUESSEL);
    events = new Subject();
    userInfo = new BehaviorSubject<UserInfo | null>(besucher);
    geklaert = new BehaviorSubject<string | null>(null);
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

    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        {
          provide: AuthService,
          useValue: { userInfo$: userInfo, getUserInfo: () => userInfo.value },
        },
        {
          provide: Art9EinwilligungService,
          useValue: { geklaert$: geklaert, geklaert: () => geklaert.value },
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

  /** Ein neuer Besuch: eine frische Instanz, wie nach dem Neuladen der App. */
  function neuerBesuch(): RundgangService {
    const neu = TestBed.runInInjectionContext(() => new RundgangService());
    neu.beobachten({ onDestroy: () => undefined } as unknown as DestroyRef);
    return neu;
  }

  function navigiert(url: string): void {
    router.url = url;
    events.next(new NavigationEnd(1, url, url));
  }


  describe('Erstbesuch', () => {
    it('zeigt beim ersten Besuch der Startseite das Willkommen als Band', () => {
      expect(service.band()).toBeNull();
      navigiert('/search');
      expect(service.band()).toBe(WILLKOMMEN);
    });

    it('zeigt es nach „Ausblenden“ nicht mehr, auch nicht beim nächsten Besuch', () => {
      navigiert('/search');
      service.bandBeantworten(false);
      expect(service.band()).toBeNull();
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBe('1');

      const zweiter = neuerBesuch();
      navigiert('/search');
      expect(zweiter.band()).toBeNull();
    });

    it('merkt sich nichts, solange niemand reagiert: Das Band kommt beim nächsten Besuch wieder', () => {
      navigiert('/search');
      const zweiter = neuerBesuch();
      navigiert('/search');
      expect(zweiter.band()).toBe(WILLKOMMEN);
    });

    it('steht nur auf der Startseite, nicht über Treffern, Formularen, Einwilligung oder Rechtstexten (#599)', () => {
      for (const seite of ['/result?searchQuery=x', '/einladung/abc', '/login', '/einwilligung?returnUrl=%2Fsearch', '/datenschutz', '/contribute']) {
        navigiert(seite);
        expect(service.band()).withContext(seite).toBeNull();
      }
      navigiert('/search');
      expect(service.band()).toBe(WILLKOMMEN);
    });

    it('verschwindet auf einer Seite ohne Angebot und kommt auf der Startseite wieder', () => {
      navigiert('/search');
      navigiert('/impressum');
      expect(service.band()).toBeNull();
      navigiert('/search');
      expect(service.band()).toBe(WILLKOMMEN);
    });

    it('geht ohne Speicher (privates Fenster) ohne Fehler und blendet sich für diesen Besuch aus', () => {
      spyOn(Storage.prototype, 'getItem').and.throwError('gesperrt');
      spyOn(Storage.prototype, 'setItem').and.throwError('gesperrt');
      navigiert('/search');
      expect(() => service.bandBeantworten(false)).not.toThrow();
      expect(service.band()).toBeNull();
      navigiert('/result?searchQuery=x');
      expect(service.band()).toBeNull();
    });

    it('zeigt nichts, solange offen ist, ob jemand angemeldet ist (#587)', () => {
      userInfo.next(null);
      navigiert('/search');
      expect(service.band()).toBeNull();
      userInfo.next(besucher);
      expect(service.band()).toBe(WILLKOMMEN);
    });

    it('gilt als beantwortet, wenn derselbe Rundgang über Hilfe oder Menü startet', async () => {
      navigiert('/search');
      await service.starten('antwort-finden');
      service.beenden();
      expect(service.band()).toBeNull();
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBe('1');
    });

    it('zeigt kein Willkommen, wer Mitmachen schon hatte (Merker aus der Zeit vor #587)', () => {
      localStorage.setItem(MITMACHEN_SCHLUESSEL, '1');
      navigiert('/search');
      expect(service.band()).toBeNull();
    });

    it('startet mit „Rundgang starten“ den Rundgang Antwort finden und blendet sich aus', () => {
      navigiert('/search');
      service.bandBeantworten(true);
      const stand = service.aktiv();
      expect(stand?.rundgang.id).toBe('antwort-finden');
      expect(stand?.index).toBe(0);
      expect(router.navigateByUrl).not.toHaveBeenCalled(); // schon auf /search
      expect(service.band()).toBeNull();
    });

    it('steht nicht neben einem Rundgang, auch nicht, solange dessen erster Schritt lädt (#585)', async () => {
      navigiert('/search?von=teilen'); // Startseite, aber nicht genau die Adresse des ersten Schritts
      expect(service.band()).toBe(WILLKOMMEN);
      router.navigateByUrl.and.returnValue(new Promise(() => undefined));
      void service.starten('antwort-finden'); // erster Schritt auf /search, lädt noch
      expect(service.aktiv()).toBeNull();
      expect(service.band()).toBeNull();
    });

    it('bleibt nach einem Rundgang für diesen Besuch weg, ohne als beantwortet zu gelten (#585)', async () => {
      navigiert('/search');
      await service.starten('mitmachen');
      service.beenden();
      navigiert('/search');
      expect(service.band()).toBeNull();
      expect(localStorage.getItem(WILLKOMMEN_SCHLUESSEL)).toBeNull();
      const naechster = neuerBesuch();
      navigiert('/search');
      expect(naechster.band()).toBe(WILLKOMMEN);
    });
  });

  describe('Rundgang', () => {
    it('führt für die Treffer-Schritte über die Beispielsuche, Schritt erst nach dem Laden', async () => {
      await service.starten('antwort-finden');
      const weiter = service.weiter();
      expect(service.aktiv()?.index).toBe(0);
      await weiter;
      expect(router.navigateByUrl).toHaveBeenCalledWith(
        jasmine.objectContaining({ pfad: '/result', query: { searchQuery: STARTBEISPIEL } }) as never,
      );
      expect(service.aktiv()?.index).toBe(1);
    });

    it('füllt in Schritt 1 das Startbeispiel vor, das die Treffer-Schritte suchen (#601)', () => {
      const schritte = RUNDGAENGE['antwort-finden'].schritte;
      expect(schritte[0].vorbelegen).toBe(STARTBEISPIEL);
      for (const schritt of schritte.slice(1, 4)) {
        expect(schritt.seite?.query).toEqual({ searchQuery: STARTBEISPIEL });
      }
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

  describe('Mitmachen beim ersten Beitragen (#587)', () => {
    /** Angemeldet, und die App führt nicht (mehr) auf die Einwilligung. */
    function angemeldetGeklaert(): void {
      userInfo.next(angemeldet);
      geklaert.next('u1');
    }

    it('bietet nach der Anmeldung auf der Startseite kein Mitmachen an, nur den Neu-Punkt', () => {
      localStorage.setItem(WILLKOMMEN_SCHLUESSEL, '1');
      navigiert('/search');
      angemeldetGeklaert();
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeTrue();
    });

    it('bietet Mitmachen auf Beitragen und Fangkorb an, bis die Person reagiert', () => {
      angemeldetGeklaert();
      for (const seite of ['/contribute', '/fangkorb']) {
        navigiert(seite);
        expect(service.band()).withContext(seite).toBe(MITMACHEN_ANGEBOT);
      }
      service.bandBeantworten(false);
      expect(localStorage.getItem(MITMACHEN_SCHLUESSEL)).toBe('1');
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeFalse();
    });

    it('startet mit „Zeig mir’s“ den Rundgang Mitmachen ohne den Schritt „Beitragen“', async () => {
      angemeldetGeklaert();
      navigiert('/contribute');
      service.bandBeantworten(true);
      await Promise.resolve();
      expect(service.aktiv()?.rundgang.id).toBe('mitmachen');
      expect(service.aktiv()?.rundgang.schritte[service.aktiv()!.index].titel).toBe('Einwerfen');
      expect(service.beitragenNeu()).toBeFalse();
    });

    it('steht nicht über dem Einwerfen: „Zeig mir’s“ würde den Einwurf verwerfen', () => {
      angemeldetGeklaert();
      navigiert('/einwerfen');
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeTrue();
    });

    it('startet „Zeig mir’s“ auch vom Fangkorb aus beim Einwerfen', async () => {
      angemeldetGeklaert();
      navigiert('/fangkorb');
      service.bandBeantworten(true);
      await new Promise((fertig) => setTimeout(fertig)); // erst die Seite, dann der Schritt
      expect(router.navigateByUrl).toHaveBeenCalled();
      expect(service.aktiv()?.rundgang.schritte[service.aktiv()!.index].titel).toBe('Einwerfen');
    });

    it('nimmt Band und Neu-Punkt nach dem Widerruf der Einwilligung weg', () => {
      angemeldetGeklaert();
      navigiert('/contribute');
      expect(service.band()).toBe(MITMACHEN_ANGEBOT);
      geklaert.next(null);
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeFalse();
    });

    it('wertet eine Anmeldung ohne Kennung nie als eingewilligt', () => {
      userInfo.next({ ...angemeldet, userId: null });
      navigiert('/contribute');
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeFalse();
    });

    it('nimmt den Neu-Punkt weg, wenn Mitmachen über Hilfe oder Menü startet', async () => {
      angemeldetGeklaert();
      navigiert('/search');
      await service.starten('mitmachen');
      expect(service.beitragenNeu()).toBeFalse();
      expect(localStorage.getItem(MITMACHEN_SCHLUESSEL)).toBe('1');
    });

    it('zeigt angemeldet weiter das Willkommen auf der Startseite, wenn es noch offen ist', () => {
      navigiert('/search');
      angemeldetGeklaert();
      expect(service.band()).toBe(WILLKOMMEN);
    });

    it('wartet auf die Einwilligung, auch mit dem Neu-Punkt (#587)', () => {
      userInfo.next(angemeldet);
      navigiert('/contribute');
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeFalse();
      geklaert.next('u1');
      expect(service.band()).toBe(MITMACHEN_ANGEBOT);
      expect(service.beitragenNeu()).toBeTrue();
    });

    it('steht nicht auf der Einwilligung (#587)', () => {
      userInfo.next(angemeldet);
      navigiert('/einwilligung?returnUrl=%2Fcontribute');
      geklaert.next('u1');
      expect(service.band()).toBeNull();
      navigiert('/contribute');
      expect(service.band()).toBe(MITMACHEN_ANGEBOT);
    });

    it('steht nicht über einem Formular, das die Person gerade begonnen hat', () => {
      angemeldetGeklaert();
      navigiert('/workflow/add-commentary');
      expect(service.band()).toBeNull();
    });

    it('bietet ohne Einwilligung nichts an und zeigt keinen Neu-Punkt (#587)', () => {
      userInfo.next(angemeldet);
      navigiert('/contribute');
      expect(service.band()).toBeNull();
      expect(service.beitragenNeu()).toBeFalse();
    });

    it('zeigt Besuchern keinen Neu-Punkt', () => {
      userInfo.next(besucher);
      navigiert('/search');
      expect(service.beitragenNeu()).toBeFalse();
    });
  });
});
