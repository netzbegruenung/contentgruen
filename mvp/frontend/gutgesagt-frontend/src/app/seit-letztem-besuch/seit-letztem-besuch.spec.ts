import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { SeitLetztemBesuchComponent, neuesListe } from './seit-letztem-besuch.component';
import { SeitLetztemBesuchService, alteBesuchMerkerEntfernen } from './seit-letztem-besuch.service';
import { AuthService, UserInfo } from '../auth/auth.service';
import { BesuchResponse, UsageTrackingService } from '../services/usage-tracking.service';

describe('Seit deinem letzten Besuch (Nutzerfuehrung 13.11.)', () => {
  describe('neuesListe', () => {
    it('nennt hoechstens drei Kacheln, nur mit Neuem, ohne „neu“ bei den Aussagen', () => {
      expect(neuesListe(12, 3, 4).map((e) => [e.zahl, e.wort, e.ziel])).toEqual([
        ['12', 'Mal genutzt', '/contributions'],
        ['3', 'neue Einwürfe', '/fangkorb'],
        ['4', 'warten auf Antwort', '/hier-fehlt-eine-antwort'],
      ]);
      expect(neuesListe(1, 1, 1).map((e) => e.wort)).toEqual(['Mal genutzt', 'neuer Einwurf', 'wartet auf Antwort']);
    });

    it('gibt jeder Kachel einen ganzen Satz, der Zahl und sichtbaren Text enthaelt', () => {
      const liste = neuesListe(12, 1, 4);
      expect(liste.map((e) => e.satz)).toEqual([
        'Deine Beiträge wurden 12 Mal genutzt',
        '1 neuer Einwurf im Fangkorb',
        '4 Lücken warten auf Antwort',
      ]);
      expect(neuesListe(0, 0, 1)[0].satz).toBe('1 Lücke wartet auf Antwort');
      liste.forEach((e) => expect(e.satz.replace('Lücken ', '')).toContain(`${e.zahl} ${e.wort}`));
    });

    it('zeigt an der Grenze der Liste „50+“', () => {
      expect(neuesListe(0, 0, 50, true).map((e) => [e.zahl, e.satz])).toEqual([['50+', '50+ Lücken warten auf Antwort']]);
    });

    it('zeigt nie eine negative oder leere Zahl', () => {
      expect(neuesListe(null, 0, 0)).toEqual([]);
      expect(neuesListe(-1, -3, -2)).toEqual([]);
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
        'Deine Beiträge wurden 2 Mal genutzt',
        '3 neue Einwürfe im Fangkorb',
        '4 Lücken warten auf Antwort',
      ]);
      // Sichtbar: grosse Zahl und kurzer Text, das Icon ist fuer Screenreader versteckt
      const kachel: HTMLElement = nav.querySelector('a.nutzung')!;
      expect(kachel.querySelector('.seit-besuch-zahl')!.textContent).toBe('2');
      expect(kachel.querySelector('.seit-besuch-wort')!.textContent).toBe('Mal genutzt');
      expect(kachel.querySelector('mat-icon')!.getAttribute('aria-hidden')).toBe('true');
      expect(Storage.prototype.setItem).not.toHaveBeenCalled();
      expect(Storage.prototype.getItem).not.toHaveBeenCalled();
    });

    it('blendet einen Link nach dem Klick aus, bis zum Kontowechsel', () => {
      const fixture = erstellen();
      info.next({ isAuthenticated: true, userId: 'kim-1' } as UserInfo);
      besuch.next({ nutzung_seit_letztem_besuch: 0, neue_einwuerfe: 3, unbeantwortete_aussagen: 2 });
      fixture.detectChanges();

      (fixture.nativeElement.querySelector('a.einwuerfe') as HTMLAnchorElement).click();
      fixture.detectChanges();
      expect(links(fixture)).toEqual(['2 Lücken warten auf Antwort']);

      info.next({ isAuthenticated: true, userId: 'bo-2' } as UserInfo);
      fixture.detectChanges();
      expect(links(fixture)).toContain('3 neue Einwürfe im Fangkorb');
      expect(TestBed.inject(SeitLetztemBesuchService).erledigt$.value.size).toBe(0);
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
