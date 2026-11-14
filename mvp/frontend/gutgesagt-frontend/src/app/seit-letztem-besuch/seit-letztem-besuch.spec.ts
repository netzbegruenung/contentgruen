import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';

import { SeitLetztemBesuchComponent, neuesListe } from './seit-letztem-besuch.component';
import { SeitLetztemBesuchService, alteBesuchMerkerEntfernen } from './seit-letztem-besuch.service';
import { AuthService, UserInfo } from '../auth/auth.service';
import { BesuchResponse, UsageTrackingService } from '../services/usage-tracking.service';

describe('Seit deinem letzten Besuch (Nutzerfuehrung 13.11.)', () => {
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
    });

    it('zeigt an der Grenze der Liste „50+“', () => {
      expect(neuesListe(0, 0, 50, true).map((e) => e.text)).toEqual(['50+ Lücken warten auf eine Antwort']);
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

    const links = (fixture: any): string[] =>
      Array.from(fixture.nativeElement.querySelectorAll('a')).map((a: any) => a.textContent.trim());

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

      expect(fixture.nativeElement.querySelector('h2').textContent).toBe('Seit deinem letzten Besuch');
      expect(links(fixture)).toEqual([
        '2 neue Nutzungen deiner Beiträge',
        '3 neue Einwürfe im Fangkorb',
        '4 Lücken warten auf eine Antwort',
      ]);
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
      expect(links(fixture)).toEqual(['2 Lücken warten auf eine Antwort']);

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
