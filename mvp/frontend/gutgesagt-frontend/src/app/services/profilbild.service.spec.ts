import { TestBed } from '@angular/core/testing';
import { UserInfo } from '../auth/auth.service';
import {
  ALTE_PROFILBILD_SCHLUESSEL,
  ANONYMES_PROFILBILD,
  INITIALEN,
  PROFILBILD_SCHLUESSEL,
  ProfilbildService,
  initialen,
} from './profilbild.service';

describe('ProfilbildService', () => {
  const ANNA: UserInfo = { isAuthenticated: true, userId: 'user-anna', userName: 'Anna B.', claims: {} };
  const BEN: UserInfo = { isAuthenticated: true, userId: 'user-ben', userName: 'Ben', claims: {} };
  const BESUCHER: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  function erzeugen(person: UserInfo | null = ANNA): ProfilbildService {
    const service = TestBed.inject(ProfilbildService);
    service.setzePerson(person);
    return service;
  }

  function aufraeumen(): void {
    ALTE_PROFILBILD_SCHLUESSEL.forEach((s: string) => sessionStorage.removeItem(s));
    localStorage.removeItem(PROFILBILD_SCHLUESSEL);
  }

  beforeEach(() => {
    aufraeumen();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
  });

  afterEach(aufraeumen);

  describe('ohne Wahl', () => {
    it('zeigt Besuchern und bei offenem Anmeldestand den anonymen Avatar', () => {
      expect(erzeugen(BESUCHER).bild()).toBe(ANONYMES_PROFILBILD);
      TestBed.resetTestingModule();
      expect(erzeugen(null).bild()).toBe(ANONYMES_PROFILBILD);
    });

    it('leitet das Bild fest aus der Kennung ab: gleiche Person, gleiches Bild', () => {
      const erstes = erzeugen(ANNA).bild();
      TestBed.resetTestingModule();

      expect(erzeugen(ANNA).bild()).toBe(erstes);
    });

    it('leitet aus allen 40 Bildern ab, nie die Initialen oder das anonyme Profilbild', () => {
      const service = erzeugen();
      const bilder = service.auswahl().filter((o) => o.id !== INITIALEN).map((o) => o.url);
      const getroffen = new Set<string>();
      for (let i = 0; i < 2000; i++) {
        service.setzePerson({ ...ANNA, userId: `user-${i}` });
        expect(bilder).toContain(service.bild());
        getroffen.add(service.bild());
      }
      expect(getroffen.size).toBe(40);
    });

    it('speichert nichts im Browser', () => {
      const vorher = [Object.keys(localStorage), Object.keys(sessionStorage)];
      const service = erzeugen();
      service.bild();
      service.setzePerson(BEN);
      service.bild();

      expect([Object.keys(localStorage), Object.keys(sessionStorage)]).toEqual(vorher);
      expect(service.gewaehlt()).toBeNull();
    });
  });

  describe('Auswahl', () => {
    it('bietet 20 Menschen und 20 Motive an, dazu die Initialen, ohne Geschlecht in Kennung oder Text', () => {
      const auswahl = erzeugen().auswahl();

      expect(auswahl.length).toBe(41);
      expect(auswahl[0].id).toBe(INITIALEN);
      expect(auswahl.filter((o) => o.id.startsWith('mensch-')).length).toBe(20);
      expect(auswahl.map((o) => o.url)).toContain('/avatars/igel.png');
      expect(auswahl.map((o) => o.url)).not.toContain(ANONYMES_PROFILBILD);
      expect(new Set(auswahl.map((o) => o.id)).size).toBe(auswahl.length);
      for (const option of auswahl) {
        expect(option.id).not.toMatch(/female|male/);
        expect(option.alt).not.toMatch(/female|male|weiblich|männlich|Frau|Mann/i);
        expect(option.alt.length).toBeGreaterThan(2);
      }
    });

    it('zeichnet die Initialen weiss auf Tanne', () => {
      const svg = decodeURIComponent(erzeugen().auswahl()[0].url);

      expect(svg).toContain('#005437');
      expect(svg).toContain('#ffffff');
      expect(svg).toContain('>AB<');
    });
  });

  describe('Wahl', () => {
    it('zeigt das gewaehlte Bild und merkt es sich erst dann im localStorage', () => {
      const service = erzeugen();
      const option = service.auswahl()[3];

      service.waehlen(option.id);

      expect(service.bild()).toBe(option.url);
      expect(service.gewaehlt()).toBe(option.id);
      expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBe(option.id);
    });

    it('liest die Wahl beim naechsten Start wieder', () => {
      const option = erzeugen().auswahl()[5];
      TestBed.resetTestingModule();
      localStorage.setItem(PROFILBILD_SCHLUESSEL, option.id);

      expect(erzeugen().bild()).toBe(option.url);
    });

    it('zeigt gewaehlte Initialen mit dem Namen der angemeldeten Person', () => {
      const service = erzeugen();
      service.waehlen(INITIALEN);
      service.setzePerson(BEN);

      expect(decodeURIComponent(service.bild())).toContain('>B<');
    });

    it('Zuruecksetzen loescht die Wahl und fuehrt zum abgeleiteten Bild zurueck', () => {
      const service = erzeugen();
      const abgeleitet = service.bild();
      service.waehlen(INITIALEN);

      service.zuruecksetzen();

      expect(service.bild()).toBe(abgeleitet);
      expect(service.gewaehlt()).toBeNull();
      expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();
    });

    it('ignoriert und entfernt eine unbekannte gespeicherte Wahl', () => {
      localStorage.setItem(PROFILBILD_SCHLUESSEL, 'https://example.org/fremd.svg');

      const service = erzeugen();

      expect(service.gewaehlt()).toBeNull();
      expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();
    });

    it('lehnt eine unbekannte Wahl ab, ohne etwas zu speichern', () => {
      const service = erzeugen();

      service.waehlen('fremd');

      expect(service.gewaehlt()).toBeNull();
      expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBeNull();
    });

    it('zeigt Besuchern trotz gespeicherter Wahl den anonymen Avatar', () => {
      localStorage.setItem(PROFILBILD_SCHLUESSEL, INITIALEN);

      expect(erzeugen(BESUCHER).bild()).toBe(ANONYMES_PROFILBILD);
    });

    it('waehlt auch ohne Storage, dann nur fuer die laufende Seite', () => {
      const service = erzeugen();
      const schreiben = spyOn(Storage.prototype, 'setItem').and.throwError('QuotaExceededError');

      expect(() => service.waehlen(INITIALEN)).not.toThrow();
      expect(service.gewaehlt()).toBe(INITIALEN);
      schreiben.and.callThrough();
    });
  });

  describe('Start', () => {
    it('loescht die sessionStorage-Eintraege frueherer Versionen', () => {
      sessionStorage.setItem('profilePicture', '/avatars/female1.svg');
      sessionStorage.setItem('anonymousAvatar', '/avatars/anon-question.svg');
      sessionStorage.setItem('userAvatar', '/avatars/male2.svg');

      erzeugen();

      ALTE_PROFILBILD_SCHLUESSEL.forEach((s: string) => expect(sessionStorage.getItem(s)).toBeNull());
    });

    it('startet auch, wenn der Browser den Storage sperrt', () => {
      const lesen = spyOn(Storage.prototype, 'getItem').and.throwError('SecurityError');
      const loeschen = spyOn(Storage.prototype, 'removeItem').and.throwError('SecurityError');

      expect(() => erzeugen().bild()).not.toThrow();
      lesen.and.callThrough();
      loeschen.and.callThrough();
    });
  });

  describe('initialen', () => {
    it('nimmt die ersten Buchstaben von hoechstens zwei Namensteilen', () => {
      expect(initialen('Anna B.')).toBe('AB');
      expect(initialen('Ben')).toBe('B');
      expect(initialen('  maria von der leyen ')).toBe('MV');
      expect(initialen('Özlem-Jana Ünal')).toBe('ÖÜ');
    });

    it('faellt ohne Buchstaben auf ein Fragezeichen zurueck', () => {
      expect(initialen(null)).toBe('?');
      expect(initialen('<script> 123')).toBe('S');
      expect(initialen('1 2')).toBe('?');
    });
  });
});
