import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA, SimpleChange } from '@angular/core';
import { Clipboard } from '@angular/cdk/clipboard';
import { By } from '@angular/platform-browser';
import { MatTooltip } from '@angular/material/tooltip';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { Subject, of, throwError } from 'rxjs';

import { KartenAktionenComponent } from './karten-aktionen.component';
import { AuthService } from '../../auth/auth.service';
import { LoggingService } from '../../services/logging.service';
import { UsageTrackingService } from '../../services/usage-tracking.service';
import { VotingService } from '../../services/voting.service';
import { TEILEN_LINK_KOPIERT, TEILEN_NAVIGATOR, TeilenNavigator } from '../../shared/teilen.service';

/**
 * Portiert aus commentary-result-item.component.voting.spec.ts; statt eines
 * Suchpakets mit user_vote bekommt die Leiste nur noch die ID und die Stimme.
 * Seit dem Abgleich gegen den Ausgangszustand kommen die Folgen Like/Dislike/Like
 * hinzu, bei denen frueher eine Stimme verloren ging.
 */
describe('KartenAktionenComponent - Abstimmen', () => {
  const INHALT_ID = '123e4567-e89b-12d3-a456-426614174000';

  let component: KartenAktionenComponent;
  let fixture: ComponentFixture<KartenAktionenComponent>;
  let votingService: jasmine.SpyObj<VotingService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;
  /** Das Teilen-Menue des Geraets; ohne share wie am Desktop ohne Web Share API. */
  let nav: TeilenNavigator;

  function stimmeAendern(stimme: 'like' | 'dislike' | undefined, vorher?: 'like' | 'dislike'): void {
    component.stimme = stimme;
    component.ngOnChanges({ stimme: new SimpleChange(vorher, stimme, false) });
  }

  beforeEach(async () => {
    const votingSpy = jasmine.createSpyObj('VotingService', ['setLike', 'removeLike', 'setDislike', 'removeDislike']);
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['logInteraction', 'logError', 'error', 'debug', 'info', 'warn']);
    const snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);
    const clipboardSpy = jasmine.createSpyObj('Clipboard', ['copy']);
    const usageTrackingSpy = jasmine.createSpyObj('UsageTrackingService', [
      'trackContentUsage',
      'gepostetAngeboten',
      'gepostetBekannt',
      'gepostetMelden',
    ]);
    usageTrackingSpy.gepostetAngeboten.and.returnValue(of(false));
    usageTrackingSpy.gepostetBekannt.and.returnValue(null);
    nav = {};
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);
    authServiceSpy.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' });

    await TestBed.configureTestingModule({
      imports: [KartenAktionenComponent],
      providers: [
        { provide: VotingService, useValue: votingSpy },
        { provide: LoggingService, useValue: loggingSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: Clipboard, useValue: clipboardSpy },
        { provide: UsageTrackingService, useValue: usageTrackingSpy },
        { provide: AuthService, useValue: authServiceSpy },
        { provide: MatDialog, useValue: jasmine.createSpyObj('MatDialog', ['open']) },
        { provide: Router, useValue: jasmine.createSpyObj('Router', ['navigate']) },
        { provide: TEILEN_NAVIGATOR, useFactory: () => nav },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(KartenAktionenComponent);
    component = fixture.componentInstance;
    votingService = TestBed.inject(VotingService) as jasmine.SpyObj<VotingService>;
    snackBar = TestBed.inject(MatSnackBar) as jasmine.SpyObj<MatSnackBar>;

    component.inhaltId = INHALT_ID;
    component.typ = 'commentary';
    component.kopierText = 'Test text';
    component.ngOnInit();
  });

  describe('Vote Initialization', () => {
    it('should initialize with no votes', () => {
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    });

    it('should initialize with like from search results', () => {
      component.stimme = 'like';
      component.ngOnInit();
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    });

    it('should initialize with dislike from search results', () => {
      component.stimme = 'dislike';
      component.ngOnInit();
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    });
  });

  describe('Like Functionality', () => {
    it('should set like when not voted', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({ content_id: INHALT_ID, vote_type: 'like', message: '' } as any));

      component.toggleLike();
      tick(50);

      expect(votingService.setLike).toHaveBeenCalledWith(INHALT_ID);
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should remove like when already liked', fakeAsync(() => {
      component.isLiked = true;
      votingService.removeLike.and.returnValue(of({ content_id: INHALT_ID, vote_type: null, message: '' } as any));

      component.toggleLike();
      tick(50);

      expect(votingService.removeLike).toHaveBeenCalledWith(INHALT_ID);
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should change from dislike to like', fakeAsync(() => {
      component.isDisliked = true;
      votingService.setLike.and.returnValue(of({ content_id: INHALT_ID, vote_type: 'like', message: '' } as any));

      component.toggleLike();
      tick(50);

      expect(votingService.setLike).toHaveBeenCalledWith(INHALT_ID);
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should handle error when setting like', fakeAsync(() => {
      votingService.setLike.and.returnValue(throwError(() => ({ status: 500, message: 'Server error' })));

      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();

      component.toggleLike();
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();

      tick(50);

      expect(snackBar.open).toHaveBeenCalledWith('Fehler beim Abstimmen', 'Schließen', { duration: 3000 });
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));
  });

  describe('Vote Button State Management', () => {
    it('should prevent multiple simultaneous vote requests', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));
      component.isVoting = true;
      const initialLikedState = component.isLiked;
      const initialDislikedState = component.isDisliked;

      component.toggleLike();
      tick(50);

      expect(votingService.setLike.calls.count()).toBe(0);
      expect(component.isLiked).toBe(initialLikedState);
      expect(component.isDisliked).toBe(initialDislikedState);
    }));

    it('should maintain correct button states after rapid toggling', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));
      votingService.removeLike.and.returnValue(of({} as any));

      component.toggleLike();
      component.toggleLike();
      component.toggleLike();

      tick(50);

      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
      expect(votingService.setLike.calls.count()).toBe(1);
    }));

    it('schickt bei Like, Dislike, Like jede Stimme ab (keine geht verloren)', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));
      votingService.setDislike.and.returnValue(of({} as any));

      component.toggleLike();
      tick(50);
      component.toggleDislike();
      tick(50);
      component.toggleLike();
      tick(50);

      expect(votingService.setLike.calls.count()).toBe(2);
      expect(votingService.setDislike.calls.count()).toBe(1);
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('schickt bei Dislike, Like, Dislike jede Stimme ab', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));
      votingService.setDislike.and.returnValue(of({} as any));

      component.toggleDislike();
      tick(50);
      component.toggleLike();
      tick(50);
      component.toggleDislike();
      tick(50);

      expect(votingService.setDislike.calls.count()).toBe(2);
      expect(votingService.setLike.calls.count()).toBe(1);
      expect(component.isDisliked).toBeTrue();
    }));

    it('nimmt nach Like, Dislike das Dislike wieder zurueck', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));
      votingService.setDislike.and.returnValue(of({} as any));
      votingService.removeDislike.and.returnValue(of({} as any));

      component.toggleLike();
      tick(50);
      component.toggleDislike();
      tick(50);
      component.toggleDislike();
      tick(50);

      expect(votingService.removeDislike).toHaveBeenCalledWith(INHALT_ID);
      expect(votingService.removeLike).not.toHaveBeenCalled();
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));

    it('schickt bei Like und Dislike innerhalb der Entprellung nur den Endstand', fakeAsync(() => {
      votingService.setDislike.and.returnValue(of({} as any));

      component.toggleLike();
      component.toggleDislike();
      tick(50);

      expect(votingService.setLike).not.toHaveBeenCalled();
      expect(votingService.setDislike.calls.count()).toBe(1);
      expect(component.isDisliked).toBeTrue();
    }));

    it('schickt nichts, wenn der Endstand dem Ausgang entspricht', fakeAsync(() => {
      stimmeAendern('like');

      component.toggleDislike();
      component.toggleLike();
      tick(50);

      expect(votingService.setLike).not.toHaveBeenCalled();
      expect(votingService.setDislike).not.toHaveBeenCalled();
      expect(component.isLiked).toBeTrue();
    }));

    it('nimmt bei einem Fehler auf den gespeicherten Stand zurueck, nicht auf leer', fakeAsync(() => {
      stimmeAendern('like');
      votingService.setDislike.and.returnValue(throwError(() => ({ status: 500 })));

      component.toggleDislike();
      tick(50);

      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should reset vote states for non-authenticated users', fakeAsync(() => {
      const authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      authService.getUserInfo.and.returnValue(null);
      snackBar.open.and.returnValue({ onAction: jasmine.createSpy('onAction').and.returnValue(of()) } as any);

      component.isLiked = false;
      component.isDisliked = false;

      component.toggleLike();
      tick(50);

      expect(component.isLiked).toBeFalsy();
      expect(component.isDisliked).toBeFalsy();
      expect(snackBar.open).toHaveBeenCalledWith('Bitte melde dich an, um abzustimmen', 'Anmelden', {
        duration: 5000,
      });
    }));
  });

  describe('Dislike Functionality', () => {
    it('should set dislike when not voted', fakeAsync(() => {
      votingService.setDislike.and.returnValue(of({} as any));

      component.toggleDislike();
      tick(50);

      expect(votingService.setDislike).toHaveBeenCalledWith(INHALT_ID);
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    }));

    it('should remove dislike when already disliked', fakeAsync(() => {
      component.isDisliked = true;
      votingService.removeDislike.and.returnValue(of({} as any));

      component.toggleDislike();
      tick(50);

      expect(votingService.removeDislike).toHaveBeenCalledWith(INHALT_ID);
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should change from like to dislike', fakeAsync(() => {
      component.isLiked = true;
      votingService.setDislike.and.returnValue(of({} as any));

      component.toggleDislike();
      tick(50);

      expect(votingService.setDislike).toHaveBeenCalledWith(INHALT_ID);
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    }));

    it('should handle error when setting dislike', fakeAsync(() => {
      votingService.setDislike.and.returnValue(throwError(() => ({ status: 500, message: 'Server error' })));

      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();

      component.toggleDislike();
      expect(component.isDisliked).toBeTrue();
      expect(component.isLiked).toBeFalse();

      tick(50);

      expect(snackBar.open).toHaveBeenCalledWith('Fehler beim Abstimmen', 'Schließen', { duration: 3000 });
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));
  });

  describe('Vote State Management', () => {
    it('should update vote state when input changes with like', () => {
      stimmeAendern('like');

      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    });

    it('should update vote state when input changes with dislike', () => {
      stimmeAendern('dislike');

      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    });

    it('should reset vote state when input changes to no vote', () => {
      component.isLiked = true;
      component.isDisliked = false;

      stimmeAendern(undefined, 'like');

      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    });
  });

  describe('Vote Button State', () => {
    beforeEach(() => {
      fixture.detectChanges();
    });

    function stimmKnoepfe(): HTMLButtonElement[] {
      return Array.from(fixture.nativeElement.querySelectorAll('.stimme-knopf'));
    }

    it('should apply active-button class when liked', () => {
      fixture.componentRef.setInput('stimme', 'like');
      fixture.detectChanges();

      expect(stimmKnoepfe()[0].classList.contains('active-button')).toBeTrue();
    });

    it('should apply active-button class when disliked', () => {
      fixture.componentRef.setInput('stimme', 'dislike');
      fixture.detectChanges();

      expect(stimmKnoepfe()[1].classList.contains('active-button')).toBeTrue();
    });

    it('should not apply active-button class when not voted', () => {
      stimmKnoepfe().forEach((knopf) => {
        expect(knopf.classList.contains('active-button')).toBeFalse();
      });
    });
  });

  describe('Rate Limiting', () => {
    const zuViele = { status: 429, headers: { get: (header: string) => (header === 'Retry-After' ? '30' : null) } };

    it('should handle rate limit error gracefully for like', fakeAsync(() => {
      votingService.setLike.and.returnValue(throwError(() => zuViele));

      component.toggleLike();
      tick(50);

      expect(snackBar.open).toHaveBeenCalledWith('Zu viele Anfragen. Bitte warte 30 Sekunden.', 'OK', {
        duration: 5000,
      });
    }));

    it('should handle rate limit error gracefully for dislike', fakeAsync(() => {
      votingService.setDislike.and.returnValue(throwError(() => zuViele));

      component.toggleDislike();
      tick(50);

      expect(snackBar.open).toHaveBeenCalledWith('Zu viele Anfragen. Bitte warte 30 Sekunden.', 'OK', {
        duration: 5000,
      });
    }));

    it('fordert ohne Art.-9-Einwilligung nicht zum Anmelden auf; den Hinweis zeigt der Interceptor (#489)', fakeAsync(() => {
      votingService.setLike.and.returnValue(
        throwError(() => ({ status: 403, error: { detail: 'art9_einwilligung_fehlt' } })),
      );

      component.toggleLike();
      tick(50);

      expect(snackBar.open).not.toHaveBeenCalled();
    }));
  });

  describe('Kopieren', () => {
    it('kopiert den Text, zaehlt die Nutzung und meldet es der Karte', () => {
      const clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      const usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      const kopiert = jasmine.createSpy('kopiert');
      component.kopiert.subscribe(kopiert);

      component.kopieren();

      expect(clipboard.copy).toHaveBeenCalledWith('Test text');
      expect(usage.trackContentUsage).toHaveBeenCalledWith(INHALT_ID, undefined);
      expect(kopiert).toHaveBeenCalled();
    });

    it('hat keinen Pfeil neben Kopieren, ohne zweite Variante auch keinen Menueeintrag (#641)', () => {
      fixture.detectChanges();
      fixture.nativeElement.querySelector('.menue-knopf').click();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelectorAll('.kopieren button').length).toBe(1);
      expect(document.querySelector('.zweite-kopie')).toBeNull();
    });

    it('zeigt die zweite Variante ganz oben im ⋮-Menue (#641; "Link kopieren" ist im Teilen aufgegangen)', () => {
      fixture.componentRef.setInput('zweiteKopie', { text: 'Test text\n\nHerkunft: https://example.org', wort: 'Mit Herkunft kopieren' });
      fixture.detectChanges();

      fixture.nativeElement.querySelector('.menue-knopf').click();
      fixture.detectChanges();

      const eintraege = Array.from(document.querySelectorAll('.mat-mdc-menu-item-text')).map((eintrag) => eintrag.textContent!.trim());
      expect(eintraege[0]).toBe('Mit Herkunft kopieren');
      expect(eintraege).not.toContain('Link kopieren');
      expect(fixture.nativeElement.querySelectorAll('.kopieren button').length).toBe(1);
    });

    it('sagt im Tooltip, was der Knopf kopiert (#641)', () => {
      fixture.componentRef.setInput('kopierHinweis', 'Kopiert Text und Herkunft');
      fixture.detectChanges();

      const tooltip = fixture.debugElement.query(By.css('.kopieren-knopf')).injector.get(MatTooltip);
      expect(tooltip.message).toBe('Kopiert Text und Herkunft');
    });

    it('kopiert die zweite Variante und zaehlt auch das als Nutzung', () => {
      const clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      const usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      const kopiert = jasmine.createSpy('kopiert');
      component.kopiert.subscribe(kopiert);
      component.zweiteKopie = { text: 'Test text\n\nHerkunft: https://example.org', wort: 'Mit Herkunft kopieren' };

      component.zweiteKopieren();

      expect(clipboard.copy).toHaveBeenCalledWith('Test text\n\nHerkunft: https://example.org');
      expect(usage.trackContentUsage).toHaveBeenCalledWith(INHALT_ID, undefined);
      expect(kopiert).toHaveBeenCalled();
    });

    it('kopiert ueber den Knopf den Standardtext, auch wenn es eine zweite Variante gibt', () => {
      const clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      const usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      component.zweiteKopie = { text: 'Test text\n\nHerkunft: https://example.org', wort: 'Mit Herkunft kopieren' };

      component.kopieren();

      expect(clipboard.copy).toHaveBeenCalledWith('Test text');
      expect(usage.trackContentUsage).toHaveBeenCalledTimes(1);
    });

    it('meldet "Erfolgreich kopiert!" ohne Luecke', () => {
      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledWith('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });
    });

    it('erinnert mit Platzhalter ans Ausfuellen der Luecke (#640, R38)', () => {
      component.kopierText = 'Gut. [Hier ein eigenes Erlebnis: …] Ende.';

      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledWith('Kopiert – füll noch die Lücke in [ ] aus.', 'OK', { duration: 6000 });
    });

    it('oeffnet den Melde-Dialog mit ID und Typ', () => {
      const dialog = TestBed.inject(MatDialog) as jasmine.SpyObj<MatDialog>;

      component.openReportDialog();

      expect(dialog.open.calls.mostRecent().args[1]!.data).toEqual({ contentId: INHALT_ID, contentType: 'commentary' });
    });
  });

  describe('Rückmeldung „Gepostet?“ (#643)', () => {
    let usage: jasmine.SpyObj<UsageTrackingService>;
    let aktion: Subject<void>;

    beforeEach(() => {
      usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      aktion = new Subject<void>();
      snackBar.open.and.returnValue({ onAction: () => aktion.asObservable() } as any);
    });

    it('bestätigt sofort und fragt, sobald der Server die Rückmeldung anbietet', () => {
      const antwort = new Subject<boolean>();
      usage.gepostetAngeboten.and.returnValue(antwort.asObservable());

      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledWith('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });
      expect(usage.gepostetAngeboten).toHaveBeenCalledWith('test-user');
      antwort.next(true);
      expect(snackBar.open).toHaveBeenCalledWith('Kopiert. Gepostet?', 'Ja, gepostet', { duration: 8000 });
      expect(usage.gepostetMelden).not.toHaveBeenCalled();
    });

    it('fragt sofort, wenn das Angebot schon bekannt ist', () => {
      usage.gepostetBekannt.and.returnValue(true);

      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledOnceWith('Kopiert. Gepostet?', 'Ja, gepostet', { duration: 8000 });
      expect(usage.gepostetAngeboten).not.toHaveBeenCalled();
    });

    it('fragt den Server nicht, wenn schon feststeht, dass nichts angeboten wird', () => {
      usage.gepostetBekannt.and.returnValue(false);

      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledOnceWith('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });
      expect(usage.gepostetAngeboten).not.toHaveBeenCalled();
    });

    it('dankt nicht, wenn der Server die Rückmeldung inzwischen nicht mehr anbietet', () => {
      usage.gepostetBekannt.and.returnValue(true);
      usage.gepostetMelden.and.returnValue(of('nicht_angeboten' as const));
      component.kopieren();
      snackBar.open.calls.reset();

      aktion.next();

      expect(usage.gepostetMelden).toHaveBeenCalledWith('test-user');
      expect(snackBar.open).not.toHaveBeenCalled();
    });

    it('dankt ohne Zahl, wenn das Zählen scheitert', () => {
      usage.gepostetBekannt.and.returnValue(true);
      usage.gepostetMelden.and.returnValue(of(null));
      component.kopieren();

      aktion.next();

      expect(snackBar.open).toHaveBeenCalledWith('Danke! Zählen hat gerade nicht geklappt.', 'Schließen', { duration: 5000 });
    });

    it('zählt erst mit „Ja, gepostet“ und dankt mit der echten Zahl der Woche', () => {
      usage.gepostetAngeboten.and.returnValue(of(true));
      usage.gepostetMelden.and.returnValue(of(7));
      component.kopieren();

      aktion.next();

      expect(usage.gepostetMelden).toHaveBeenCalledTimes(1);
      expect(snackBar.open).toHaveBeenCalledWith(
        'Danke! Diese Woche haben 7 Menschen gemeldet, dass sie öffentlich gekontert haben. Du bist dabei.',
        'Schließen',
        { duration: 5000 },
      );
    });

    it('bleibt ohne Angebot bei „Erfolgreich kopiert!“', () => {
      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledWith('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });
      expect(usage.gepostetMelden).not.toHaveBeenCalled();
    });

    it('bleibt bei einer Lücke beim Hinweis aufs Ausfüllen und fragt nicht (#640)', () => {
      usage.gepostetBekannt.and.returnValue(true);
      component.kopierText = 'Gut. [Hier ein eigenes Erlebnis: …] Ende.';

      component.kopieren();

      expect(snackBar.open).toHaveBeenCalledOnceWith('Kopiert – füll noch die Lücke in [ ] aus.', 'OK', { duration: 6000 });
      expect(usage.gepostetAngeboten).not.toHaveBeenCalled();
    });

    it('fragt Besucher nicht und fragt auch den Server nicht', () => {
      (TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>).getUserInfo.and.returnValue(null);

      component.kopieren();

      expect(usage.gepostetAngeboten).not.toHaveBeenCalled();
      expect(snackBar.open).toHaveBeenCalledWith('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });
    });
  });

  describe('Beitrag öffnen (#300)', () => {
    function menueEintrag(): HTMLElement | null {
      fixture.detectChanges();
      fixture.nativeElement.querySelector('.menue-knopf').click();
      fixture.detectChanges();
      return document.querySelector('.beitrag-oeffnen');
    }

    it('fuehrt aus dem Menue auf die eigene Adresse des Beitrags', () => {
      const router = TestBed.inject(Router) as jasmine.SpyObj<Router>;

      menueEintrag()!.click();

      expect(router.navigate).toHaveBeenCalledWith(['/beitrag', INHALT_ID]);
    });

    it('fehlt auf der eigenen Adresse selbst', () => {
      fixture.componentRef.setInput('ansichtVerlinkt', false);

      expect(menueEintrag()).toBeNull();
    });

    it('fuehrt in der Vorschau nirgendwohin', () => {
      const router = TestBed.inject(Router) as jasmine.SpyObj<Router>;
      fixture.componentRef.setInput('vorschau', true);

      component.beitragOeffnen();

      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('Teilen (B7)', () => {
    const LINK = `${window.location.origin}/beitrag/${INHALT_ID}`;
    let clipboard: jasmine.SpyObj<Clipboard>;
    let usage: jasmine.SpyObj<UsageTrackingService>;

    function knopf(): HTMLButtonElement {
      fixture.detectChanges();
      return fixture.nativeElement.querySelector('button.teilen-knopf');
    }

    beforeEach(() => {
      clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      fixture.componentRef.setInput('titel', 'Wärmepumpe lohnt sich auch im Altbau');
    });

    it('ist ein echter Knopf neben dem Menue, mit dem Titel im Namen', () => {
      const teilen = knopf();
      expect(teilen).not.toBeNull();
      expect(teilen.getAttribute('aria-label')).toBe('Beitrag teilen: „Wärmepumpe lohnt sich auch im Altbau“');
      expect(teilen.parentElement!.querySelector('.menue-knopf')).not.toBeNull();
      // Der Kopieren-Knopf bleibt der Hauptknopf in der Mitte
      expect(fixture.nativeElement.querySelector('.kopieren .kopieren-knopf')).not.toBeNull();
    });

    it('oeffnet mobil das Teilen-Menue mit Text und Link und zaehlt als Nutzung', async () => {
      nav.share = jasmine.createSpy('share').and.resolveTo(undefined);
      const kopiert = jasmine.createSpy('kopiert');
      component.kopiert.subscribe(kopiert);

      await component.teilen();

      expect(nav.share).toHaveBeenCalledWith({
        url: LINK,
        text: 'Test text',
        title: 'Wärmepumpe lohnt sich auch im Altbau',
      });
      expect(clipboard.copy).not.toHaveBeenCalled();
      expect(snackBar.open).not.toHaveBeenCalled();
      expect(usage.trackContentUsage).toHaveBeenCalledOnceWith(INHALT_ID, undefined);
      expect(kopiert).toHaveBeenCalledTimes(1);
    });

    it('zaehlt die angezeigte Fassung eines Kommentars', async () => {
      nav.share = jasmine.createSpy('share').and.resolveTo(undefined);
      fixture.componentRef.setInput('fassung', 'lang');

      await component.teilen();

      expect(usage.trackContentUsage).toHaveBeenCalledOnceWith(INHALT_ID, 'lang');
    });

    it('kopiert ohne Teilen-Menue den Link, meldet das und zaehlt als Nutzung', async () => {
      clipboard.copy.and.returnValue(true);

      knopf().click();
      await fixture.whenStable();

      expect(clipboard.copy).toHaveBeenCalledWith(LINK);
      expect(snackBar.open).toHaveBeenCalledWith(TEILEN_LINK_KOPIERT, 'OK', { duration: 4000 });
      expect(usage.trackContentUsage).toHaveBeenCalledOnceWith(INHALT_ID, undefined);
    });

    it('bricht still ab: keine Meldung, keine Nutzung (AbortError)', async () => {
      nav.share = jasmine.createSpy('share').and.rejectWith(new DOMException('abgebrochen', 'AbortError'));

      await component.teilen();

      expect(snackBar.open).not.toHaveBeenCalled();
      expect(clipboard.copy).not.toHaveBeenCalled();
      expect(usage.trackContentUsage).not.toHaveBeenCalled();
    });

    it('faellt bei einem anderen Fehler des Teilen-Menues aufs Kopieren zurueck', async () => {
      nav.share = jasmine.createSpy('share').and.rejectWith(new DOMException('nein', 'NotAllowedError'));
      clipboard.copy.and.returnValue(true);

      await component.teilen();

      expect(clipboard.copy).toHaveBeenCalledWith(LINK);
      expect(usage.trackContentUsage).toHaveBeenCalledTimes(1);
    });

    it('zaehlt nicht, wenn auch Kopieren scheitert', async () => {
      clipboard.copy.and.returnValue(false);

      await component.teilen();

      expect(snackBar.open).toHaveBeenCalledWith('Kopieren hat nicht geklappt.', 'OK', { duration: 4000 });
      expect(usage.trackContentUsage).not.toHaveBeenCalled();
    });

    it('fehlt auf der Beitragsseite selbst, dort steht der Knopf unter der Karte', () => {
      fixture.componentRef.setInput('ansichtVerlinkt', false);

      expect(knopf()).toBeNull();
    });

    it('tut in der Vorschau nichts', async () => {
      nav.share = jasmine.createSpy('share').and.resolveTo(undefined);
      fixture.componentRef.setInput('vorschau', true);

      expect(knopf().getAttribute('aria-disabled')).toBe('true');
      await component.teilen();

      expect(nav.share).not.toHaveBeenCalled();
      expect(clipboard.copy).not.toHaveBeenCalled();
    });

    it('hat im Menue kein "Link kopieren" mehr', () => {
      fixture.detectChanges();
      fixture.nativeElement.querySelector('.menue-knopf').click();
      fixture.detectChanges();

      expect(document.querySelector('.mat-mdc-menu-panel .link-kopieren')).toBeNull();
    });
  });

  describe('Ohne Abstimmen', () => {
    it('zeigt ohne Abstimmen keine Daumen, Kopieren und Menue bleiben', () => {
      fixture.componentRef.setInput('abstimmenSichtbar', false);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.stimmen')).toBeNull();
      expect(fixture.nativeElement.querySelectorAll('.stimme-knopf').length).toBe(0);
      expect(fixture.nativeElement.querySelector('.kopieren-knopf')).not.toBeNull();
      expect(fixture.nativeElement.querySelector('.menue-knopf')).not.toBeNull();
    });

    it('zeigt die Daumen standardmaessig', () => {
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelectorAll('.stimme-knopf').length).toBe(2);
    });
  });

  describe('Stimm-Knöpfe mit Material-Umriss-Daumen (#641)', () => {
    it('zeigt schlanke Umriss-Daumen hoch und runter im Kreis-Knopf, nicht die Hand des Siegels', () => {
      fixture.detectChanges();

      const knoepfe: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.stimme-knopf'));
      expect(knoepfe.map((k) => k.querySelector('mat-icon')!.textContent!.trim())).toEqual([
        'thumb_up_off_alt',
        'thumb_down_off_alt',
      ]);
      expect(knoepfe.every((k) => k.hasAttribute('mat-icon-button'))).toBeTrue();
      expect(knoepfe.some((k) => k.querySelector('svg path'))).toBeFalse();
    });

    it('verbirgt die Daumen vor Screenreadern, der Knopf behält seinen Namen', () => {
      fixture.detectChanges();

      const knoepfe: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.stimme-knopf'));
      expect(knoepfe.map((k) => k.querySelector('mat-icon')!.getAttribute('aria-hidden'))).toEqual(['true', 'true']);
      expect(knoepfe.map((k) => k.getAttribute('aria-label'))).toEqual(['Hilfreich', 'Nicht hilfreich']);
    });
  });

  describe('Als Vorlage nehmen (#356)', () => {
    it('fuehrt angemeldet ins Formular des Typs mit der Vorlage', () => {
      const navigieren = (TestBed.inject(Router) as jasmine.SpyObj<Router>).navigate;

      expect(component.kannAlsVorlage).toBeTrue();
      component.alsVorlageNehmen();

      expect(navigieren).toHaveBeenCalledOnceWith(['/workflow/add-commentary'], {
        queryParams: { vorlage: INHALT_ID },
      });
    });

    it('gibt es an der Hintergrundinfo, nicht an Post und Bild', () => {
      for (const [typ, erwartet] of [['generictext', true], ['post', false], ['image', false]] as const) {
        component.typ = typ;
        expect(component.kannAlsVorlage).withContext(typ).toBe(erwartet);
      }
    });

    it('gibt es nicht fuer Besucher und nicht in der Vorschau', () => {
      const authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      authService.getUserInfo.and.returnValue(null);
      expect(component.kannAlsVorlage).toBeFalse();

      authService.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' } as any);
      component.vorschau = true;
      expect(component.kannAlsVorlage).toBeFalse();
    });
  });

  describe('Vorschau', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('vorschau', true);
      fixture.detectChanges();
    });

    it('zeigt die Leiste sichtbar gesperrt, ohne Reaktion auf Zeiger und Fokus (#616)', () => {
      const leiste: HTMLElement = fixture.nativeElement.querySelector('.aktionen');
      const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('button'));

      expect(getComputedStyle(leiste).pointerEvents).toBe('none');
      expect(Number(getComputedStyle(leiste).opacity)).toBeLessThan(1);
      expect(knoepfe.length).toBe(5); // zwei Daumen, Kopieren, Teilen, Menue
      knoepfe.forEach((knopf) => {
        expect(knopf.getAttribute('aria-disabled')).toBe('true');
        expect(knopf.getAttribute('tabindex')).toBe('-1');
        expect(knopf.disabled).toBeFalse();
      });
    });

    it('kopiert auch die zweite Variante nicht und zaehlt keine Nutzung', () => {
      const clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      const usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      fixture.componentRef.setInput('zweiteKopie', { text: 'Test text\n\nHerkunft: https://example.org', wort: 'Mit Herkunft kopieren' });
      fixture.detectChanges();

      component.zweiteKopieren();

      expect(clipboard.copy).not.toHaveBeenCalled();
      expect(usage.trackContentUsage).not.toHaveBeenCalled();
    });

    it('stimmt nicht ab, kopiert nicht und meldet nicht', fakeAsync(() => {
      const clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      const dialog = TestBed.inject(MatDialog) as jasmine.SpyObj<MatDialog>;

      component.toggleLike();
      component.kopieren();
      component.openReportDialog();
      tick(50);

      expect(component.isLiked).toBeFalse();
      expect(votingService.setLike).not.toHaveBeenCalled();
      expect(clipboard.copy).not.toHaveBeenCalled();
      expect(dialog.open).not.toHaveBeenCalled();
    }));
  });
});
