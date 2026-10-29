import { TestBed } from '@angular/core/testing';
import { UserInfo } from '../auth/auth.service';
import {
  ALTE_PROFILBILD_SCHLUESSEL,
  ANONYMES_PROFILBILD,
  PROFILBILDER,
  ProfilbildService,
} from './profilbild.service';

describe('ProfilbildService', () => {
  const MITWIRKENDE: UserInfo = { isAuthenticated: true, userId: 'user-001', userName: 'Test User', claims: {} };
  const BESUCHER: UserInfo = { isAuthenticated: false, userId: null, userName: null, claims: null };

  function erzeugen(): ProfilbildService {
    return TestBed.inject(ProfilbildService);
  }

  function gespeicherteSchluessel(): string[] {
    return Object.keys(sessionStorage);
  }

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({});
  });

  afterEach(() => ALTE_PROFILBILD_SCHLUESSEL.forEach((s: string) => sessionStorage.removeItem(s)));

  it('zeigt Besuchern das anonyme Profilbild, auch solange der Anmeldestand offen ist', () => {
    expect(erzeugen().fuer(BESUCHER)).toBe(ANONYMES_PROFILBILD);
    expect(erzeugen().fuer(null)).toBe(ANONYMES_PROFILBILD);
  });

  it('lost Mitwirkenden einmal ein Profilbild aus und behaelt es fuer die Seite', () => {
    const zufall = spyOn(Math, 'random').and.returnValues(0.5, 0.9);
    const service = erzeugen();

    const erstes = service.fuer(MITWIRKENDE);
    service.fuer(BESUCHER);

    expect(erstes).toBe(PROFILBILDER[6]);
    expect(service.fuer(MITWIRKENDE)).toBe(erstes);
    expect(zufall).toHaveBeenCalledTimes(1);
  });

  it('legt nichts im sessionStorage ab, weder fuer Besucher noch fuer Mitwirkende', () => {
    const vorher = gespeicherteSchluessel();
    const service = erzeugen();

    service.fuer(BESUCHER);
    service.fuer(MITWIRKENDE);

    expect(gespeicherteSchluessel()).toEqual(vorher);
  });

  it('loescht beim Start die alten Eintraege aus dem sessionStorage', () => {
    sessionStorage.setItem('profilePicture', '/avatars/female1.svg');
    sessionStorage.setItem('anonymousAvatar', '/avatars/anon-question.svg');
    sessionStorage.setItem('userAvatar', '/avatars/male2.svg');

    erzeugen();

    ALTE_PROFILBILD_SCHLUESSEL.forEach((s: string) => expect(sessionStorage.getItem(s)).toBeNull());
  });

  it('uebernimmt kein altes Bild aus dem sessionStorage', () => {
    spyOn(Math, 'random').and.returnValue(0);
    sessionStorage.setItem('profilePicture', '/avatars/male6.svg');

    expect(erzeugen().fuer(MITWIRKENDE)).toBe(PROFILBILDER[0]);
  });

  it('startet auch, wenn der Browser den sessionStorage sperrt', () => {
    const loeschen = spyOn(Storage.prototype, 'removeItem').and.throwError('SecurityError');

    expect(() => erzeugen()).not.toThrow();
    // Der Spy gilt noch im afterEach, das selbst removeItem aufruft.
    loeschen.and.callThrough();
  });
});
