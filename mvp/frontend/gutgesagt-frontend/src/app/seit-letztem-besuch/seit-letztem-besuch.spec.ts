import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { SeitLetztemBesuchComponent, neuesListe } from './seit-letztem-besuch.component';
import { EINWUERFE_HOECHSTENS, SeitLetztemBesuchService, aussageDazu, neueEinwuerfe } from './seit-letztem-besuch.service';
import {
  LETZTER_BESUCH_PRAEFIX,
  besuchMerkerEntfernen,
  besuchMerkerLesen,
  besuchSchluessel,
} from './besuch-merker';
import { AuthService, UserInfo } from '../auth/auth.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { Einwurf, EinwurfService } from '../services/einwurf.service';
import { StatementService } from '../services/statement.service';
import { UnbeantworteteAussage } from '../services/dtos/statementDtos';

const einwurf = (felder: Partial<Einwurf>): Einwurf =>
  ({ id: 'e', status: 'open', created_at: '2026-11-12T10:00:00Z', ist_eigener_einwurf: false, ...felder }) as Einwurf;
const aussage = (id: string): UnbeantworteteAussage =>
  ({ statement_id: id, statement_text: id, personen_ohne_treffer: 0, themen: [] }) as UnbeantworteteAussage;
const merkerSetzen = (kennung: string, wert: unknown) => localStorage.setItem(besuchSchluessel(kennung), JSON.stringify(wert));

describe('Seit deinem letzten Besuch (Nutzerfuehrung 13.11.)', () => {
  afterEach(() => {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(LETZTER_BESUCH_PRAEFIX))
      .forEach((k) => localStorage.removeItem(k));
  });

  describe('neuesListe', () => {
    it('nennt hoechstens drei Links, nur mit Neuem, ohne „neu“ bei den Aussagen', () => {
      expect(neuesListe(2, 3, 4).map((e) => [e.text, e.ziel])).toEqual([
        ['2 neue Nutzungen deiner Beiträge', '/contributions'],
        ['3 neue Einwürfe im Fangkorb', '/fangkorb'],
        ['4 Lücken warten auf eine Antwort', '/hier-fehlt-eine-antwort'],
      ]);
      expect(neuesListe(1, 1, 1).map((e) => e.text)).toEqual([
        '1 neue Nutzung deiner Beiträge',
        '1 neuer Einwurf im Fangkorb',
        '1 Lücke wartet auf eine Antwort',
      ]);
      expect(neuesListe(null, 0, 0)).toEqual([]);
    });
  });

  describe('Merker je Konto', () => {
    it('trennt Konten ueber einen Pruefwert, ohne die Kennung im Schluessel', () => {
      expect(besuchSchluessel('kim-1')).toMatch(/^gutgesagt-letzter-besuch-[0-9a-f]{8}$/);
      expect(besuchSchluessel('kim-1')).not.toBe(besuchSchluessel('kim-2'));
      expect(besuchSchluessel('kim-1')).not.toContain('kim');
    });

    it('liest einen kaputten Merker als keinen und entfernt ihn beim Abmelden', () => {
      localStorage.setItem(besuchSchluessel('kim-1'), '{kaputt');
      expect(besuchMerkerLesen('kim-1')).toBeNull();
      merkerSetzen('kim-1', { zeit: 'gestern', aussagen: [] });
      expect(besuchMerkerLesen('kim-1')).toBeNull();
      merkerSetzen('kim-1', { zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] });
      besuchMerkerEntfernen('kim-1');
      expect(localStorage.getItem(besuchSchluessel('kim-1'))).toBeNull();
    });
  });

  describe('Zaehlen', () => {
    it('zaehlt nur neue, offene Einwuerfe anderer', () => {
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
          '2026-11-11T00:00:00Z',
        ),
      ).toBe(2);
    });

    it('erkennt, ob eine Aussage dazugekommen ist', () => {
      expect(aussageDazu([aussage('a'), aussage('b')], ['a'])).toBeTrue();
      expect(aussageDazu([aussage('a')], ['a', 'b'])).toBeFalse();
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

    it('meldet beim ersten Besuch nichts und merkt sich den Stand je Konto', () => {
      let stand: unknown;
      dienst().stand('kim-1').subscribe((s) => (stand = s));

      expect(stand).toEqual({ einwuerfe: 0, aussagen: 0 });
      expect(besuchMerkerLesen('kim-1')!.aussagen).toEqual(['a', 'b']);
      expect(besuchMerkerLesen('kim-2')).toBeNull();
      expect(fangkorb).toHaveBeenCalledOnceWith(1, EINWUERFE_HOECHSTENS);
      expect(EINWUERFE_HOECHSTENS).toBe(25);
    });

    it('vergleicht mit dem letzten Besuch, nennt die wartenden Aussagen und rechnet je Konto nur einmal', () => {
      merkerSetzen('kim-1', { zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] });
      const service = dienst();
      let stand: unknown;
      service.stand('kim-1').subscribe((s) => (stand = s));
      service.stand('kim-1').subscribe();

      expect(stand).toEqual({ einwuerfe: 1, aussagen: 2 });
      expect(fangkorb).toHaveBeenCalledTimes(1);
    });

    it('nennt keine Aussagen, wenn keine dazugekommen ist', () => {
      merkerSetzen('kim-1', { zeit: '2026-11-11T00:00:00Z', aussagen: ['a', 'b'] });
      let stand: unknown;
      dienst().stand('kim-1').subscribe((s) => (stand = s));

      expect(stand).toEqual({ einwuerfe: 1, aussagen: 0 });
    });

    it('rechnet beim Kontowechsel neu und vergisst die Klicks', () => {
      const service = dienst();
      service.stand('kim-1').subscribe();
      service.erledigen('einwuerfe');
      service.stand('kim-2').subscribe();

      expect(fangkorb).toHaveBeenCalledTimes(2);
      expect(service.erledigt$.value.size).toBe(0);
    });

    it('behaelt bei Ladefehlern den alten Zeitpunkt und die alten Aussagen', () => {
      merkerSetzen('kim-1', { zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] });
      const service = dienst();
      unbeantwortet.and.returnValue(throwError(() => new Error('502')));
      fangkorb.and.returnValue(throwError(() => new Error('403')));
      let stand: unknown;
      service.stand('kim-1').subscribe((s) => (stand = s));

      expect(stand).toEqual({ einwuerfe: 0, aussagen: 0 });
      expect(besuchMerkerLesen('kim-1')).toEqual({ zeit: '2026-11-11T00:00:00Z', aussagen: ['a'] });
    });
  });

  describe('SeitLetztemBesuchComponent', () => {
    let info: BehaviorSubject<UserInfo | null>;
    let nutzung: BehaviorSubject<number | null>;
    let stand: jasmine.Spy;
    let erledigt: BehaviorSubject<ReadonlySet<string>>;
    let erledigen: jasmine.Spy;

    function erstellen(neues = { einwuerfe: 0, aussagen: 0 }) {
      info = new BehaviorSubject<UserInfo | null>(null);
      nutzung = new BehaviorSubject<number | null>(null);
      erledigt = new BehaviorSubject<ReadonlySet<string>>(new Set());
      stand = jasmine.createSpy('stand').and.returnValue(of(neues));
      erledigen = jasmine.createSpy('erledigen').and.callFake((art: string) => erledigt.next(new Set([...erledigt.value, art])));
      TestBed.configureTestingModule({
        imports: [SeitLetztemBesuchComponent],
        providers: [
          provideRouter([]),
          { provide: AuthService, useValue: { userInfo$: info } },
          { provide: UsageTrackingService, useValue: { nutzungSeitLetztemBesuch$: nutzung } },
          { provide: SeitLetztemBesuchService, useValue: { stand, erledigt$: erledigt, erledigen } },
        ],
      });
      const fixture = TestBed.createComponent(SeitLetztemBesuchComponent);
      fixture.detectChanges();
      return fixture;
    }

    const links = (fixture: any): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll('a')).map((a: any) => a.textContent.trim());

    it('zeigt Besuchern nichts und fragt nichts ab', () => {
      const fixture = erstellen({ einwuerfe: 3, aussagen: 1 });
      info.next({ isAuthenticated: false } as UserInfo);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
      expect(stand).not.toHaveBeenCalled();
    });

    it('zeigt Angemeldeten die Links je Konto, sobald die Nutzung da ist', () => {
      const fixture = erstellen({ einwuerfe: 3, aussagen: 0 });
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      fixture.detectChanges();

      expect(stand).toHaveBeenCalledWith('kim-1');
      expect(fixture.nativeElement.querySelector('h2').textContent).toBe('Seit deinem letzten Besuch');
      expect(links(fixture)).toEqual(['3 neue Einwürfe im Fangkorb']);

      nutzung.next(2);
      fixture.detectChanges();
      expect(links(fixture)).toEqual(['2 neue Nutzungen deiner Beiträge', '3 neue Einwürfe im Fangkorb']);
    });

    it('blendet einen Link nach dem Klick aus', () => {
      const fixture = erstellen({ einwuerfe: 3, aussagen: 2 });
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      fixture.detectChanges();

      (fixture.nativeElement.querySelector('a.einwuerfe') as HTMLAnchorElement).click();
      fixture.detectChanges();

      expect(erledigen).toHaveBeenCalledOnceWith('einwuerfe');
      expect(links(fixture)).toEqual(['2 Lücken warten auf eine Antwort']);
    });

    it('zeigt ohne Neues nichts', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      nutzung.next(0);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
    });
  });
});
