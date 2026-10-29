import { TestBed } from '@angular/core/testing';
import { UserInfo } from '../auth/auth.service';
import {
  ALTE_PROFILBILD_SCHLUESSEL,
  ANONYMES_PROFILBILD,
  PROFILBILD_SCHLUESSEL,
  ProfilbildService,
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

    it('leitet aus allen 40 Bildern ab, nie das anonyme Profilbild', () => {
      const service = erzeugen();
      const bilder = service.auswahl.map((o) => o.url);
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
    it('bietet 20 Menschen und 20 Motive an, ohne Geschlecht in Kennung oder Text', () => {
      const auswahl = erzeugen().auswahl;

      expect(auswahl.length).toBe(40);
      expect(auswahl[0].id).toBe('mensch-01');
      expect(auswahl.every((o) => o.url.startsWith('/avatars/') && o.url.endsWith('.png'))).toBeTrue();
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

    it('bietet keine Initialen mehr an (Entscheidung 29.10.2026)', () => {
      const auswahl = erzeugen().auswahl;

      expect(auswahl.some((o) => o.id === 'initialen' || o.url.startsWith('data:'))).toBeFalse();
    });

    it('verteilt die Hauttoene: 10 hell oder mittelhell, 5 mittel, 5 mitteldunkel oder dunkel', () => {
      const menschen = erzeugen().auswahl.filter((o) => o.id.startsWith('mensch-')).map((o) => o.alt);
      const zaehlen = (...toene: string[]) =>
        menschen.filter((alt) => toene.some((ton) => alt.endsWith(`, ${ton} Hautton`))).length;

      expect(zaehlen('heller', 'mittelheller')).toBe(10);
      expect(zaehlen('mittlerer')).toBe(5);
      expect(zaehlen('mitteldunkler', 'dunkler')).toBe(5);
      expect(menschen.filter((alt) => alt.includes('roten Haaren')).length).toBe(3);
      expect(menschen.filter((alt) => alt.includes('weißem Haar')).length).toBe(2);
      for (const merkmal of ['Kopftuch', 'Rollstuhl', 'Blindenstock', 'Gehörlose', 'Bart', 'Locken', 'Ältere']) {
        expect(menschen.some((alt) => alt.includes(merkmal))).withContext(merkmal).toBeTrue();
      }
    });
  });

  describe('Wahl', () => {
    it('zeigt das gewaehlte Bild und merkt es sich erst dann im localStorage', () => {
      const service = erzeugen();
      const option = service.auswahl[3];

      service.waehlen(option.id);

      expect(service.bild()).toBe(option.url);
      expect(service.gewaehlt()).toBe(option.id);
      expect(localStorage.getItem(PROFILBILD_SCHLUESSEL)).toBe(option.id);
    });

    it('liest die Wahl beim naechsten Start wieder', () => {
      const option = erzeugen().auswahl[5];
      TestBed.resetTestingModule();
      localStorage.setItem(PROFILBILD_SCHLUESSEL, option.id);

      expect(erzeugen().bild()).toBe(option.url);
    });

    it('Zuruecksetzen loescht die Wahl und fuehrt zum abgeleiteten Bild zurueck', () => {
      const service = erzeugen();
      const abgeleitet = service.bild();
      service.waehlen('igel');

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
      localStorage.setItem(PROFILBILD_SCHLUESSEL, 'igel');

      expect(erzeugen(BESUCHER).bild()).toBe(ANONYMES_PROFILBILD);
    });

    it('waehlt auch ohne Storage, dann nur fuer die laufende Seite', () => {
      const service = erzeugen();
      const schreiben = spyOn(Storage.prototype, 'setItem').and.throwError('QuotaExceededError');

      expect(() => service.waehlen('igel')).not.toThrow();
      expect(service.gewaehlt()).toBe('igel');
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
});
