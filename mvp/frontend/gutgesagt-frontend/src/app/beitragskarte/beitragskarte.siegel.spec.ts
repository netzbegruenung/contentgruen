import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { BeitragskarteComponent } from './beitragskarte.component';
import { KartenAktionenComponent } from './karten-aktionen/karten-aktionen.component';
import { ausBeitrag, ausSuchergebnis, gueteAus } from './karten-daten';
import { AuthService, UserInfo } from '../auth/auth.service';
import { ContentService } from '../services/content.service';
import { LoggingService } from '../services/logging.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { VotingService } from '../services/voting.service';
import { SiegelComponent } from '../shared/components/siegel/siegel.component';
import { siegelErklaerung } from '../shared/components/siegel/siegel-erklaerung';

/** Das Siegel auf echten Karten und die Zaehler an den Stimm-Knoepfen (#427). */
describe('Beitragskarte: Siegel und Stimmen (#427)', () => {
  const ID = '123e4567-e89b-12d3-a456-426614174427';

  let fixture: ComponentFixture<BeitragskarteComponent>;
  let votingService: jasmine.SpyObj<VotingService>;
  let contentService: jasmine.SpyObj<ContentService>;

  function paket(felder: Record<string, unknown> = {}, rest: Record<string, unknown> = {}): any {
    return {
      score: 0.9,
      statement_text: null,
      statement_similarity_score: null,
      reply_relevance: null,
      user_vote: null,
      commentary_result: {
        id: ID,
        text: 'Wärmepumpen laufen mit Strom.',
        content_type: 'commentary',
        created: new Date().toISOString(),
        title: 'Wärmepumpen sparen Geld',
        references: [],
        usage_count: 0,
        guete: 6,
        guete_erfuellt: ['verneinung', 'satzlaenge'],
        guete_stimmen_zaehlen: false,
        // Unter der Mindestzahl liefert der Server keine Zähler (M5).
        stimmen_hilfreich: null,
        stimmen_nicht_hilfreich: null,
        ...felder,
      },
      ...rest,
    };
  }

  function zeigen(daten = ausSuchergebnis(paket())): void {
    fixture = TestBed.createComponent(BeitragskarteComponent);
    fixture.componentRef.setInput('daten', daten);
    fixture.detectChanges();
  }

  function siegel(): SiegelComponent | null {
    return fixture.debugElement.query(By.directive(SiegelComponent))?.componentInstance ?? null;
  }

  function aktionen(): KartenAktionenComponent {
    return fixture.debugElement.query(By.directive(KartenAktionenComponent)).componentInstance;
  }

  function zahlen(): string[] {
    return Array.from(fixture.nativeElement.querySelectorAll('.stimm-zahl') as NodeListOf<HTMLElement>).map((e) =>
      e.textContent!.trim(),
    );
  }

  beforeEach(async () => {
    votingService = jasmine.createSpyObj('VotingService', ['setLike', 'removeLike', 'setDislike', 'removeDislike']);
    contentService = jasmine.createSpyObj('ContentService', ['beitragLaden']);
    const auth = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);
    auth.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' });
    auth.userInfo$ = new BehaviorSubject<UserInfo | null>({ isAuthenticated: true, userId: 'test-user' } as UserInfo);

    await TestBed.configureTestingModule({
      imports: [BeitragskarteComponent, NoopAnimationsModule],
      providers: [
        { provide: VotingService, useValue: votingService },
        { provide: ContentService, useValue: contentService },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj('MatSnackBar', ['open']) },
        { provide: AuthService, useValue: auth },
        { provide: Clipboard, useValue: jasmine.createSpyObj('Clipboard', ['copy']) },
        { provide: UsageTrackingService, useValue: jasmine.createSpyObj('UsageTrackingService', ['trackContentUsage']) },
        { provide: LoggingService, useValue: jasmine.createSpyObj('LoggingService', ['error', 'debug', 'info', 'warn']) },
        { provide: MatDialog, useValue: jasmine.createSpyObj('MatDialog', ['open']) },
        provideRouter([]),
      ],
    }).compileComponents();
  });

  describe('Daten', () => {
    it('liest Güte, erfüllte Kriterien und Zähler aus dem Beitrag', () => {
      expect(ausSuchergebnis(paket()).guete).toEqual({
        wert: 6,
        erfuellt: ['verneinung', 'satzlaenge'],
        stimmenZaehlen: false,
        hilfreich: null,
        nichtHilfreich: null,
      });
    });

    it('„neu“ als null, eine ältere Antwort ohne Feld als unbekannt', () => {
      expect(gueteAus({ guete: null })?.wert).toBeNull();
      expect(gueteAus({})).toBeUndefined();
    });

    it('auch in Meine Beiträge', () => {
      const eintrag: any = { id: ID, content_type: 'commentary', text: 'x', created: '', usage_count: 0, guete: 9 };
      expect(ausBeitrag(eintrag).guete?.wert).toBe(9);
    });
  });

  describe('Siegel', () => {
    it('steht im Kopf der vollen Karte und zeigt die Güte', () => {
      zeigen();
      const knopf: HTMLButtonElement = fixture.nativeElement.querySelector('.karte-badges .siegel-knopf');
      expect(knopf).not.toBeNull();
      expect(siegel()!.guete).toBe(6);
      expect(knopf.getAttribute('aria-label')).toBe('Siegel: Güte 6 von 10. Erklärung öffnen');
    });

    it('grau und waagrecht für einen neuen Beitrag ohne Daten', () => {
      zeigen(ausSuchergebnis(paket({ guete: null, guete_erfuellt: [] })));
      expect(siegel()!.guete).toBeNull();
      expect(siegel()!.winkel).toBe(90);
    });

    it('fehlt, wenn die Antwort keine Güte kennt (Formular-Vorschau, alte Antwort)', () => {
      const ohne = paket();
      delete ohne.commentary_result.guete;
      zeigen(ausSuchergebnis(ohne));
      expect(siegel()).toBeNull();
    });

    it('Antippen öffnet die Erklärung und nicht die Karte', () => {
      zeigen();
      const angetippt = spyOn(fixture.componentInstance.angetippt, 'emit');
      fixture.nativeElement.querySelector('.siegel-knopf').click();
      fixture.detectChanges();

      const erklaerung: HTMLElement = document.querySelector('.siegel-erklaerung')!;
      expect(erklaerung).not.toBeNull();
      expect(erklaerung.textContent).toContain('Güte 6 von 10');
      expect(erklaerung.textContent).toContain('Beginnt ohne Verneinung');
      expect(erklaerung.textContent).toContain('Kurze Sätze');
      expect(erklaerung.textContent).toContain('zählen, sobald genug zusammenkommen');
      expect(angetippt).not.toHaveBeenCalled();
      // Kein leeres Menü für Screenreader: die Erklärung ist der eine Menüpunkt.
      expect(erklaerung.getAttribute('role')).toBe('menuitem');
    });

    it('steigt nach einer Stimme, wenn der Server eine höhere Güte meldet', fakeAsync(() => {
      zeigen();
      votingService.setLike.and.returnValue(of({} as any));
      contentService.beitragLaden.and.returnValue(
        of(paket({ guete: 7, guete_stimmen_zaehlen: true, stimmen_hilfreich: 3, stimmen_nicht_hilfreich: 0 }).commentary_result),
      );

      aktionen().toggleLike();
      tick(50);
      fixture.detectChanges();

      expect(contentService.beitragLaden).toHaveBeenCalledWith(ID);
      expect(siegel()!.guete).toBe(7);
      expect(zahlen()).toEqual(['3', '0']);
      tick(1000);
    }));

    it('behält die alte Güte, wenn das Nachladen scheitert', fakeAsync(() => {
      zeigen();
      votingService.setLike.and.returnValue(of({} as any));
      contentService.beitragLaden.and.returnValue(throwError(() => ({ status: 500 })));

      aktionen().toggleLike();
      tick(50);
      fixture.detectChanges();

      expect(siegel()!.guete).toBe(6);
    }));
  });

  describe('Stimm-Zähler', () => {
    const AB_SCHWELLE = { guete_stimmen_zaehlen: true, stimmen_hilfreich: 3, stimmen_nicht_hilfreich: 1 };

    it('stehen ab der Mindestzahl neben den Knöpfen und im unsichtbaren Namen', () => {
      zeigen(ausSuchergebnis(paket(AB_SCHWELLE)));
      expect(zahlen()).toEqual(['3', '1']);
      const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('.stimme-knopf') as NodeListOf<HTMLElement>);
      expect(knoepfe.map((k) => k.getAttribute('aria-label'))).toEqual([
        'Hilfreich, 3 Stimmen',
        'Nicht hilfreich, 1 Stimme',
      ]);
    });

    it('unter der Mindestzahl ohne Zahl, auch nach der eigenen Stimme', fakeAsync(() => {
      zeigen();
      expect(zahlen()).toEqual([]);
      votingService.setLike.and.returnValue(of({} as any));
      contentService.beitragLaden.and.returnValue(throwError(() => ({ status: 500 })));

      aktionen().toggleLike();
      fixture.detectChanges();

      expect(zahlen()).toEqual([]);
      const knoepfe = Array.from(fixture.nativeElement.querySelectorAll('.stimme-knopf') as NodeListOf<HTMLElement>);
      expect(knoepfe.map((k) => k.getAttribute('aria-label'))).toEqual(['Hilfreich', 'Nicht hilfreich']);
      tick(50);
    }));

    it('rechnen die eigene Stimme sofort ein und nehmen sie beim Wechsel wieder heraus', fakeAsync(() => {
      zeigen(ausSuchergebnis(paket(AB_SCHWELLE, { user_vote: 'like' })));
      expect(zahlen()).toEqual(['3', '1']);
      votingService.setDislike.and.returnValue(of({} as any));
      contentService.beitragLaden.and.returnValue(throwError(() => ({ status: 500 })));

      aktionen().toggleDislike();
      fixture.detectChanges();

      expect(zahlen()).toEqual(['2', '2']);
      tick(50);
    }));

    it('am eigenen Beitrag ohne die eigene Stimme, wie der Server zählt', fakeAsync(() => {
      zeigen(ausSuchergebnis(paket({ ...AB_SCHWELLE, ist_eigener_beitrag: true })));
      votingService.setLike.and.returnValue(of({} as any));
      contentService.beitragLaden.and.returnValue(throwError(() => ({ status: 500 })));

      aktionen().toggleLike();
      fixture.detectChanges();

      expect(zahlen()).toEqual(['3', '1']);
      tick(50);
    }));
  });

  describe('Erklärung', () => {
    it('nennt nur erfüllte, bekannte Kriterien', () => {
      const e = siegelErklaerung(8, ['passiv', 'unbekannt'], true);
      expect(e.kriterien).toEqual(['Aktiv formuliert']);
      expect(e.stimmen).toBe('Die Stimmen anderer sind eingerechnet.');
      expect(siegelErklaerung(null, [], false).ueberschrift).toBe('Neu: noch keine Güte');
    });
  });
});
