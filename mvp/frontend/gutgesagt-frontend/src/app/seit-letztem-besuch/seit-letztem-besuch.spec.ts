import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { MAX_KACHELN, SeitLetztemBesuchComponent, ZEITRAUM, neuesListe } from './seit-letztem-besuch.component';
import { SeitLetztemBesuchService, alteBesuchMerkerEntfernen } from './seit-letztem-besuch.service';
import { AuthService, UserInfo } from '../auth/auth.service';
import { BesuchResponse, UsageTrackingService } from '../services/usage-tracking.service';

describe('Seit deinem letzten Besuch (Nutzerfuehrung 13.11.)', () => {
  describe('neuesListe', () => {
    /** Kurzform fuer die alten drei Zahlen. */
    const drei = (nutzung: number | null, einwuerfe: number, aussagen: number, mehr = false) =>
      neuesListe({
        nutzung_seit_letztem_besuch: nutzung as number,
        neue_einwuerfe: einwuerfe,
        unbeantwortete_aussagen: aussagen,
        unbeantwortete_aussagen_mehr: mehr,
      });

    it('nennt nur Kacheln mit Neuem, ohne „neu“ bei den Aussagen', () => {
      expect(drei(12, 3, 4).map((e) => [e.zahl, e.wort, e.ziel])).toEqual([
        ['12', 'Nutzungen deiner Beiträge', '/contributions'],
        ['3', 'neue Einwürfe im Fangkorb', '/fangkorb'],
        ['4', 'Aussagen ohne Antwort', '/hier-fehlt-eine-antwort'],
      ]);
      expect(drei(1, 1, 1).map((e) => e.wort)).toEqual(['Nutzung deiner Beiträge', 'neuer Einwurf im Fangkorb', 'Aussage ohne Antwort']);
    });

    it('reiht alle fuenf Arten, die eigenen zuerst, die neuen Beitraege zuletzt (20.11.)', () => {
      const liste = neuesListe({
        nutzung_seit_letztem_besuch: 12,
        ausformulierte_einwuerfe: 2,
        neue_einwuerfe: 3,
        unbeantwortete_aussagen: 4,
        neue_beitraege: 5,
      });
      expect(liste.map((e) => e.art)).toEqual(['nutzung', 'ausformuliert', 'einwuerfe', 'aussagen', 'beitraege']);
    });

    it('fuehrt ausformulierte Einwuerfe auf „Meine Einwürfe“, neue Beitraege auf „Frisch aus der Community“', () => {
      const [ausformuliert, beitraege] = neuesListe({ nutzung_seit_letztem_besuch: 0, ausformulierte_einwuerfe: 2, neue_beitraege: 5 });
      expect([ausformuliert.ziel, ausformuliert.queryParams, ausformuliert.fragment]).toEqual(['/contributions', { tab: 'einwuerfe' }, undefined]);
      expect([beitraege.ziel, beitraege.queryParams, beitraege.fragment]).toEqual(['/', undefined, 'recent-content']);
    });

    it('nennt den Zeitraum, wo die Zahl nicht seit dem letzten Besuch zaehlt', () => {
      const liste = neuesListe({ nutzung_seit_letztem_besuch: 2, ausformulierte_einwuerfe: 1, neue_beitraege: 1 });
      expect(liste.map((e) => [e.wort, e.zeitraum])).toEqual([
        ['Nutzungen deiner Beiträge', undefined],
        ['Einwurf von dir ausformuliert', ZEITRAUM],
        ['neuer Beitrag', ZEITRAUM],
      ]);
      expect(ZEITRAUM).toBe('letzte 7 Tage');
    });

    it('gibt jeder Kachel einen ganzen Satz, der den sichtbaren Text woertlich enthaelt (WCAG 2.5.3)', () => {
      const liste = drei(12, 1, 4);
      expect(liste.map((e) => e.satz)).toEqual([
        '12 Nutzungen deiner Beiträge',
        '1 neuer Einwurf im Fangkorb',
        '4 Aussagen ohne Antwort: Lücken in „Hier fehlt eine Antwort“',
      ]);
      expect(drei(1, 0, 0)[0].satz).toBe('1 Nutzung deiner Beiträge');
      expect(drei(0, 0, 1)[0].satz).toBe('1 Aussage ohne Antwort: Lücke in „Hier fehlt eine Antwort“');
      liste.forEach((e) => expect(e.satz).toContain(`${e.zahl} ${e.wort}`));

      const mitZeitraum = neuesListe({ nutzung_seit_letztem_besuch: 0, ausformulierte_einwuerfe: 2, neue_beitraege: 5 });
      expect(mitZeitraum.map((e) => e.satz)).toEqual([
        '2 Einwürfe von dir ausformuliert, letzte 7 Tage',
        '5 neue Beiträge, letzte 7 Tage',
      ]);
    });

    it('hat fuer die breite Zeile einen Satz, der nach der Zahl weiterliest, und einen Knopf', () => {
      const liste = neuesListe({
        nutzung_seit_letztem_besuch: 1,
        ausformulierte_einwuerfe: 2,
        neue_einwuerfe: 1,
        unbeantwortete_aussagen: 12,
        neue_beitraege: 5,
      });
      expect(liste.map((e) => [`${e.zahl} ${e.zeile}`, e.knopf])).toEqual([
        ['1 Nutzung deiner Beiträge. Sieh nach, welche gebraucht werden.', 'Meine Beiträge'],
        ['2 Einwürfe von dir haben andere in den letzten 7 Tagen ausformuliert.', 'Meine Einwürfe'],
        ['1 neuer Einwurf wartet im Fangkorb.', 'Zum Fangkorb'],
        ['12 Aussagen warten auf eine Antwort.', 'Hier fehlt eine Antwort'],
        ['5 neue Beiträge aus der Community in den letzten 7 Tagen.', 'Frisch aus der Community'],
      ]);
    });

    it('zeigt an der Grenze der Liste „50+“', () => {
      expect(drei(0, 0, 50, true).map((e) => [e.zahl, e.satz, e.zeile])).toEqual([
        ['50+', '50+ Aussagen ohne Antwort: Lücken in „Hier fehlt eine Antwort“', 'Aussagen warten auf eine Antwort.'],
      ]);
    });

    it('zeigt nie eine negative oder leere Zahl', () => {
      expect(drei(null, 0, 0)).toEqual([]);
      expect(drei(-1, -3, -2)).toEqual([]);
      expect(neuesListe({ nutzung_seit_letztem_besuch: 0, ausformulierte_einwuerfe: -1, neue_beitraege: -2 })).toEqual([]);
    });
  });

  describe('alte Browser-Merker', () => {
    it('entfernt nur die alten Eintraege, liest nichts', () => {
      localStorage.setItem('gutgesagt-letzter-besuch', '{}');
      localStorage.setItem('gutgesagt-letzter-besuch-1a2b3c4d', '{}');
      localStorage.setItem('gutgesagt-anderes', 'bleibt');

      alteBesuchMerkerEntfernen();

      expect(localStorage.getItem('gutgesagt-letzter-besuch')).toBeNull();
      expect(localStorage.getItem('gutgesagt-letzter-besuch-1a2b3c4d')).toBeNull();
      expect(localStorage.getItem('gutgesagt-anderes')).toBe('bleibt');
      localStorage.removeItem('gutgesagt-anderes');
    });
  });

  describe('SeitLetztemBesuchComponent', () => {
    let info: BehaviorSubject<UserInfo | null>;
    let besuch: BehaviorSubject<BesuchResponse | null>;

    function erstellen() {
      info = new BehaviorSubject<UserInfo | null>(null);
      besuch = new BehaviorSubject<BesuchResponse | null>(null);
      TestBed.configureTestingModule({
        imports: [SeitLetztemBesuchComponent],
        providers: [
          provideRouter([]),
          { provide: AuthService, useValue: { userInfo$: info } },
          { provide: UsageTrackingService, useValue: { besuchStand$: besuch } },
        ],
      });
      const fixture = TestBed.createComponent(SeitLetztemBesuchComponent);
      fixture.detectChanges();
      return fixture;
    }

    /** Was ein Screenreader je Kachel vorliest: der Satz aus aria-label. */
    const links = (fixture: any): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll('a')).map((a: any) => a.getAttribute('aria-label'));

    it('zeigt Besuchern nichts', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: false } as UserInfo);
      besuch.next({ nutzung_seit_letztem_besuch: 2, neue_einwuerfe: 3, unbeantwortete_aussagen: 1 });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
    });

    it('zeigt Angemeldeten die Zahlen aus der Antwort des Besuchs, ohne eigenen Abruf oder Browser-Speicher', () => {
      spyOn(Storage.prototype, 'setItem').and.callThrough();
      spyOn(Storage.prototype, 'getItem').and.callThrough();
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('nav')).toBeNull();

      besuch.next({ nutzung_seit_letztem_besuch: 2, neue_einwuerfe: 3, unbeantwortete_aussagen: 4 });
      fixture.detectChanges();

      const nav: HTMLElement = fixture.nativeElement.querySelector('nav');
      expect(nav.getAttribute('aria-labelledby')).toBe('seit-besuch-titel');
      expect(nav.querySelector('h2#seit-besuch-titel')!.textContent).toBe('Seit deinem letzten Besuch');
      expect(links(fixture)).toEqual([
        '2 Nutzungen deiner Beiträge',
        '3 neue Einwürfe im Fangkorb',
        '4 Aussagen ohne Antwort: Lücken in „Hier fehlt eine Antwort“',
      ]);
      // Sichtbar: grosse Zahl und kurzer Text, das Icon ist fuer Screenreader versteckt
      const kachel: HTMLElement = nav.querySelector('a.nutzung')!;
      expect(kachel.querySelector('.seit-besuch-zahl')!.textContent).toBe('2');
      expect(kachel.querySelector('.seit-besuch-wort')!.textContent).toBe('Nutzungen deiner Beiträge');
      expect(kachel.querySelector('mat-icon')!.getAttribute('aria-hidden')).toBe('true');
      expect(Storage.prototype.setItem).not.toHaveBeenCalled();
      expect(Storage.prototype.getItem).not.toHaveBeenCalled();
    });

    it('blendet einen Link nach dem Klick aus, bis zum Kontowechsel', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      besuch.next({ nutzung_seit_letztem_besuch: 1, neue_einwuerfe: 3, unbeantwortete_aussagen: 2 });
      fixture.detectChanges();

      (fixture.nativeElement.querySelector('a.einwuerfe') as HTMLAnchorElement).click();
      fixture.detectChanges();
      expect(links(fixture)).toEqual(['1 Nutzung deiner Beiträge', '2 Aussagen ohne Antwort: Lücken in „Hier fehlt eine Antwort“']);

      info.next({ isAuthenticated: true, userId: 'bo-2' } as UserInfo);
      fixture.detectChanges();
      expect(links(fixture)).toContain('3 neue Einwürfe im Fangkorb');
      expect(TestBed.inject(SeitLetztemBesuchService).erledigt$.value.size).toBe(0);
    });

    it('zeigt hoechstens vier Kacheln nebeneinander, die neuen Beitraege fallen zuerst weg (20.11.)', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      besuch.next({
        nutzung_seit_letztem_besuch: 2,
        ausformulierte_einwuerfe: 1,
        neue_einwuerfe: 3,
        unbeantwortete_aussagen: 4,
        neue_beitraege: 5,
      });
      fixture.detectChanges();

      const liste: HTMLElement = fixture.nativeElement.querySelector('ul.seit-besuch-kacheln');
      expect(MAX_KACHELN).toBe(4);
      expect(liste.classList).toContain('vier');
      expect(liste.style.getPropertyValue('--seit-besuch-spalten')).toBe('4');
      expect(links(fixture)).toEqual([
        '2 Nutzungen deiner Beiträge',
        '1 Einwurf von dir ausformuliert, letzte 7 Tage',
        '3 neue Einwürfe im Fangkorb',
        '4 Aussagen ohne Antwort: Lücken in „Hier fehlt eine Antwort“',
      ]);
      const ausformuliert: HTMLAnchorElement = liste.querySelector('a.ausformuliert')!;
      expect(ausformuliert.getAttribute('href')).toBe('/contributions?tab=einwuerfe');
      expect(ausformuliert.querySelector('.seit-besuch-zeitraum')!.textContent).toBe('letzte 7 Tage');
      expect(liste.querySelector('a.nutzung .seit-besuch-zeitraum')).toBeNull();

      // Nach dem Klick auf eine Kachel rueckt die fuenfte nach
      (liste.querySelector('a.nutzung') as HTMLAnchorElement).click();
      fixture.detectChanges();
      expect(links(fixture)).toContain('5 neue Beiträge, letzte 7 Tage');
      expect(fixture.nativeElement.querySelector('a.beitraege').getAttribute('href')).toBe('/#recent-content');
    });

    it('macht aus einer einzelnen Kachel eine breite Zeile mit Satz und Knopf zum Ziel', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      besuch.next({ nutzung_seit_letztem_besuch: 0, unbeantwortete_aussagen: 12 });
      fixture.detectChanges();

      const nav: HTMLElement = fixture.nativeElement.querySelector('nav');
      expect(nav.querySelector('ul')).toBeNull();
      const zeile: HTMLElement = nav.querySelector('.seit-besuch-zeile.aussagen')!;
      const satz: HTMLElement = zeile.querySelector('p.seit-besuch-satz')!;
      expect(satz.textContent!.replace(/\s+/g, ' ').trim()).toBe('12 Aussagen warten auf eine Antwort.');
      expect(satz.querySelector('.seit-besuch-zahl')!.textContent).toBe('12');
      const knopf: HTMLAnchorElement = zeile.querySelector('a.seit-besuch-knopf')!;
      expect(knopf.textContent).toContain('Hier fehlt eine Antwort');
      expect(knopf.getAttribute('href')).toBe('/hier-fehlt-eine-antwort');
      // Der Knopf nennt das Ziel, der Satz daneben beschreibt ihn fuer Screenreader
      expect(knopf.getAttribute('aria-describedby')).toBe(satz.id);
      zeile.querySelectorAll('mat-icon').forEach((icon) => expect(icon.getAttribute('aria-hidden')).toBe('true'));

      knopf.click();
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
    });

    it('wird zur Zeile, wenn nach einem Klick nur eine Kachel bleibt', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      besuch.next({ nutzung_seit_letztem_besuch: 0, neue_einwuerfe: 3, neue_beitraege: 2 });
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll('ul a').length).toBe(2);

      (fixture.nativeElement.querySelector('a.einwuerfe') as HTMLAnchorElement).click();
      fixture.detectChanges();

      const knopf: HTMLAnchorElement = fixture.nativeElement.querySelector('.seit-besuch-zeile.beitraege a.seit-besuch-knopf');
      expect(knopf.getAttribute('href')).toBe('/#recent-content');
      expect(knopf.textContent).toContain('Frisch aus der Community');
    });

    it('zeigt ohne Neues nichts, auch bei aelteren Antworten ohne die neuen Felder', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      besuch.next({ nutzung_seit_letztem_besuch: 0 });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('nav')).toBeNull();
    });
  });
});
