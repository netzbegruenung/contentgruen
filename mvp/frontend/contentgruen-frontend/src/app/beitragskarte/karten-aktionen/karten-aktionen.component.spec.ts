import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NO_ERRORS_SCHEMA, SimpleChange } from '@angular/core';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { KartenAktionenComponent } from './karten-aktionen.component';
import { AuthService } from '../../auth/auth.service';
import { LoggingService } from '../../services/logging.service';
import { UsageTrackingService } from '../../services/usage-tracking.service';
import { VotingService } from '../../services/voting.service';

/**
 * Portiert aus commentary-result-item.component.voting.spec.ts. Die Abstimmlogik
 * ist unveraendert aus BaseResultItemComponent umgezogen; statt eines Suchpakets
 * mit user_vote bekommt die Leiste nur noch die ID und die Stimme.
 */
describe('KartenAktionenComponent - Abstimmen', () => {
  const INHALT_ID = '123e4567-e89b-12d3-a456-426614174000';

  let component: KartenAktionenComponent;
  let fixture: ComponentFixture<KartenAktionenComponent>;
  let votingService: jasmine.SpyObj<VotingService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  function stimmeAendern(stimme: 'like' | 'dislike' | undefined, vorher?: 'like' | 'dislike'): void {
    component.stimme = stimme;
    component.ngOnChanges({ stimme: new SimpleChange(vorher, stimme, false) });
  }

  beforeEach(async () => {
    const votingSpy = jasmine.createSpyObj('VotingService', ['setLike', 'removeLike', 'setDislike', 'removeDislike']);
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['logInteraction', 'logError', 'error', 'debug', 'info', 'warn']);
    const snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);
    const clipboardSpy = jasmine.createSpyObj('Clipboard', ['copy']);
    const usageTrackingSpy = jasmine.createSpyObj('UsageTrackingService', ['trackContentUsage']);
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
  });

  describe('Kopieren', () => {
    it('kopiert den Text, zaehlt die Nutzung und meldet es der Karte', () => {
      const clipboard = TestBed.inject(Clipboard) as jasmine.SpyObj<Clipboard>;
      const usage = TestBed.inject(UsageTrackingService) as jasmine.SpyObj<UsageTrackingService>;
      const kopiert = jasmine.createSpy('kopiert');
      component.kopiert.subscribe(kopiert);

      component.kopieren();

      expect(clipboard.copy).toHaveBeenCalledWith('Test text');
      expect(usage.trackContentUsage).toHaveBeenCalledWith(INHALT_ID);
      expect(kopiert).toHaveBeenCalled();
    });

    it('oeffnet den Melde-Dialog mit ID und Typ', () => {
      const dialog = TestBed.inject(MatDialog) as jasmine.SpyObj<MatDialog>;

      component.openReportDialog();

      expect(dialog.open.calls.mostRecent().args[1]!.data).toEqual({ contentId: INHALT_ID, contentType: 'commentary' });
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

  describe('Vorschau', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('vorschau', true);
      fixture.detectChanges();
    });

    it('zeigt die Leiste unveraendert, aber ohne Reaktion auf Zeiger und Fokus', () => {
      const leiste: HTMLElement = fixture.nativeElement.querySelector('.aktionen');
      const knoepfe: HTMLButtonElement[] = Array.from(fixture.nativeElement.querySelectorAll('button'));

      expect(getComputedStyle(leiste).pointerEvents).toBe('none');
      expect(getComputedStyle(leiste).opacity).toBe('1');
      expect(knoepfe.length).toBe(4);
      knoepfe.forEach((knopf) => {
        expect(knopf.getAttribute('aria-disabled')).toBe('true');
        expect(knopf.getAttribute('tabindex')).toBe('-1');
        expect(knopf.disabled).toBeFalse();
      });
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
