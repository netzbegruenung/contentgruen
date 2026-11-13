import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { SeitLetztemBesuchComponent, neuesListe } from './seit-letztem-besuch.component';
import {
  LETZTER_BESUCH_SCHLUESSEL,
  SeitLetztemBesuchService,
  merkerLesen,
  neueAussagen,
  neueEinwuerfe,
} from './seit-letztem-besuch.service';
import { AuthService, UserInfo } from '../auth/auth.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { StatementService } from '../services/statement.service';
import { UnbeantworteteAussage } from '../services/dtos/statementDtos';

const einwurf = (felder: Partial<Einwurf>): Einwurf =>
  ({ id: 'e', status: 'open', created_at: '2026-11-12T10:00:00Z', ist_eigener_einwurf: false, ...felder }) as Einwurf;
const aussage = (id: string): UnbeantworteteAussage =>
  ({ statement_id: id, statement_text: id, personen_ohne_treffer: 0, themen: [] }) as UnbeantworteteAussage;

describe('Seit deinem letzten Besuch (Nutzerfuehrung 13.11.)', () => {
  afterEach(() => localStorage.removeItem(LETZTER_BESUCH_SCHLUESSEL));

  describe('neuesListe', () => {
    it('nennt hoechstens drei Links, nur mit Neuem', () => {
      expect(neuesListe(2, 3, 1).map((e) => [e.text, e.ziel])).toEqual([
        ['2 neue Nutzungen deiner Beiträge', '/contributions'],
        ['3 neue Einwürfe im Fangkorb', '/fangkorb'],
        ['1 neue Lücke', '/hier-fehlt-eine-antwort'],
      ]);
      expect(neuesListe(1, 1, 2).map((e) => e.text)).toEqual([
        '1 neue Nutzung deiner Beiträge',
        '1 neuer Einwurf im Fangkorb',
        '2 neue Lücken',
      ]);
      expect(neuesListe(null, 0, 0)).toEqual([]);
      expect(neuesListe(0, 0, 4).map((e) => e.art)).toEqual(['aussagen']);
    });
  });

  describe('Zaehlen', () => {
    it('zaehlt nur neue, offene Einwuerfe anderer', () => {
      const seit = '2026-11-11T00:00:00Z';
      expect(
        neueEinwuerfe(
          [
            einwurf({ id: 'neu' }),
            einwurf({ id: 'neu-destilliert', status: 'in_progress' }),
            einwurf({ id: 'alt', created_at: '2026-11-10T10:00:00Z' }),
            einwurf({ id: 'eigen', ist_eigener_einwurf: true }),
            einwurf({ id: 'verworfen', status: 'discarded' }),
            einwurf({ id: 'fertig', status: 'processed' }),
          ],
          seit,
        ),
      ).toBe(2);
    });

    it('zaehlt Aussagen, die beim letzten Besuch nicht da waren', () => {
      expect(neueAussagen([aussage('a'), aussage('b'), aussage('c')], ['a'])).toBe(2);
    });

    it('liest einen kaputten Merker als keinen', () => {
      localStorage.setItem(LETZTER_BESUCH_SCHLUESSEL, '{kaputt');
      expect(merkerLesen()).toBeNull();
      localStorage.setItem(LETZTER_BESUCH_SCHLUESSEL, JSON.stringify({ zeit: 'gestern', aussagen: [] }));
      expect(merkerLesen()).toBeNull();
    });
  });

  describe('SeitLetztemBesuchService', () => {
    let fangkorb: jasmine.Spy;
    let unbeantwortet: jasmine.Spy;

    function dienst(): SeitLetztemBesuchService {
      fangkorb = jasmine.createSpy('fangkorbLaden').and.returnValue(
        of({ results: [einwurf({ id: 'neu' })], results_count: 1, total_records_count: 1 }),
      );
      unbeantwortet = jasmine.createSpy('unbeantworteteAussagen').and.returnValue(of([aussage('a'), aussage('b')]));
      TestBed.configureTestingModule({
        providers: [
          { provide: EinwurfService, useValue: { fangkorbLaden: fangkorb } },
          { provide: StatementService, useValue: { unbeantworteteAussagen: unbeantwortet } },
        ],
      });
      return TestBed.inject(SeitLetztemBesuchService);
    }

    it('meldet beim ersten Besuch nichts als neu und merkt sich den Stand im Browser', () => {
      let stand: unknown;
      dienst().stand().subscribe((s) => (stand = s));

      expect(stand).toEqual({ einwuerfe: 0, aussagen: 0 });
      expect(merkerLesen()!.aussagen).toEqual(['a', 'b']);
    });

    it('vergleicht mit dem letzten Besuch und rechnet je App-Start nur einmal', () => {
      localStorage.setItem(LETZTER_BESUCH_SCHLUESSEL, JSON.stringify({ zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] }));
      const service = dienst();
      let stand: unknown;
      service.stand().subscribe((s) => (stand = s));
      service.stand().subscribe();

      expect(stand).toEqual({ einwuerfe: 1, aussagen: 1 });
      expect(fangkorb).toHaveBeenCalledTimes(1);
      expect(unbeantwortet).toHaveBeenCalledTimes(1);
    });

    it('behaelt bei einem Ladefehler den alten Stand der Aussagen', () => {
      localStorage.setItem(LETZTER_BESUCH_SCHLUESSEL, JSON.stringify({ zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] }));
      const service = dienst();
      unbeantwortet.and.returnValue(throwError(() => new Error('502')));
      fangkorb.and.returnValue(throwError(() => new Error('403')));
      let stand: unknown;
      service.stand().subscribe((s) => (stand = s));

      expect(stand).toEqual({ einwuerfe: 0, aussagen: 0 });
      expect(merkerLesen()!.aussagen).toEqual(['a']);
    });
  });

  describe('SeitLetztemBesuchComponent', () => {
    let info: BehaviorSubject<UserInfo | null>;
    let nutzung: BehaviorSubject<number | null>;
    let stand: jasmine.Spy;

    function erstellen(neues = { einwuerfe: 0, aussagen: 0 }) {
      info = new BehaviorSubject<UserInfo | null>(null);
      nutzung = new BehaviorSubject<number | null>(null);
      stand = jasmine.createSpy('stand').and.returnValue(of(neues));
      TestBed.configureTestingModule({
        imports: [SeitLetztemBesuchComponent],
        providers: [
          provideRouter([]),
          { provide: AuthService, useValue: { userInfo$: info } },
          { provide: UsageTrackingService, useValue: { nutzungSeitLetztemBesuch$: nutzung } },
          { provide: SeitLetztemBesuchService, useValue: { stand } },
        ],
      });
      const fixture = TestBed.createComponent(SeitLetztemBesuchComponent);
      fixture.detectChanges();
      return fixture;
    }

    it('zeigt Besuchern nichts und fragt nichts ab', () => {
      const fixture = erstellen({ einwuerfe: 3, aussagen: 1 });
      info.next({ isAuthenticated: false } as UserInfo);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
      expect(stand).not.toHaveBeenCalled();
    });

    it('zeigt Angemeldeten die Links, sobald die Nutzung aus der Rueckmeldung da ist', () => {
      const fixture = erstellen({ einwuerfe: 3, aussagen: 0 });
      info.next({ isAuthenticated: true, userId: 'p' } as UserInfo);
      fixture.detectChanges();
      const links = () => Array.from(fixture.nativeElement.querySelectorAll('a')).map((a: any) => a.textContent.trim());

      expect(fixture.nativeElement.querySelector('h2').textContent).toBe('Seit deinem letzten Besuch');
      expect(links()).toEqual(['3 neue Einwürfe im Fangkorb']);

      nutzung.next(2);
      fixture.detectChanges();
      expect(links()).toEqual(['2 neue Nutzungen deiner Beiträge', '3 neue Einwürfe im Fangkorb']);
      expect(fixture.nativeElement.querySelector('a').getAttribute('href')).toBe('/contributions');
    });

    it('zeigt ohne Neues nichts', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'p' } as UserInfo);
      nutzung.next(0);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
    });
  });
});
