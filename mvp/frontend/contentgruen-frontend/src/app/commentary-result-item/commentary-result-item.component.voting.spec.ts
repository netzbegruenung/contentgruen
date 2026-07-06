import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { CommentaryResultItemComponent } from './commentary-result-item.component';
import { VotingService } from '../services/voting.service';
import { LoggingService } from '../services/logging.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Clipboard } from '@angular/cdk/clipboard';
import { of, throwError } from 'rxjs';
import { NO_ERRORS_SCHEMA, ChangeDetectorRef } from '@angular/core';

describe('CommentaryResultItemComponent - Voting Functionality', () => {
  let component: CommentaryResultItemComponent;
  let fixture: ComponentFixture<CommentaryResultItemComponent>;
  let votingService: jasmine.SpyObj<VotingService>;
  let loggingService: jasmine.SpyObj<LoggingService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    const votingSpy = jasmine.createSpyObj('VotingService', ['setLike', 'removeLike', 'setDislike', 'removeDislike']);
    const loggingSpy = jasmine.createSpyObj('LoggingService', ['logInteraction', 'logError', 'error', 'debug', 'info', 'warn']);
    const snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);
    const clipboardSpy = jasmine.createSpyObj('Clipboard', ['copy']);
    const usageTrackingSpy = jasmine.createSpyObj('UsageTrackingService', ['trackUsage']);
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);

    const mockResult = {
      score: 0.85,
      statement_text: 'Test statement',
      statement_similarity_score: 0.8,
      reply_relevance: 0.9,
      commentary_result: {
        id: '123e4567-e89b-12d3-a456-426614174000',
        text: 'Test text',
        content_type: 'commentary',
        created: '2024-01-01',
        last_modified: '2024-01-01',
        original_author: 'Test Author',
        last_modified_by: 'Test Author',
        authors: [],
        edit_history: [],
        status: 'approved' as any,
        origin: 'user' as any,
        most_similar_similarity_score: 0,
        most_similar_content_id: '',
        report_count: 0,
        is_archived: false,
        report_flagged: false,
        rejection_reason: '',
        block_reason: '',
        visibility: 'public' as any,
        title: 'Test title',
        long_text: 'Long test text',
        short_text: 'Short text',
        style: 'default',
        short_title: 'Short title',
        keywords: [],
        speaker: 'Test Speaker',
        context: 'Test context',
        claim: 'Test claim',
        usage_count: 0,
        references: [] // Add references array
      },
      user_vote: null
    } as any;

    // Mock authenticated user by default
    authServiceSpy.getUserInfo.and.returnValue({ isAuthenticated: true, userId: 'test-user' });

    await TestBed.configureTestingModule({
      imports: [ CommentaryResultItemComponent, HttpClientTestingModule ],
      providers: [
        { provide: 'RESULT', useValue: mockResult },
        { provide: VotingService, useValue: votingSpy },
        { provide: LoggingService, useValue: loggingSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: Clipboard, useValue: clipboardSpy },
        { provide: UsageTrackingService, useValue: usageTrackingSpy },
        { provide: AuthService, useValue: authServiceSpy }
      ],
      schemas: [NO_ERRORS_SCHEMA]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CommentaryResultItemComponent);
    component = fixture.componentInstance;
    votingService = TestBed.inject(VotingService) as jasmine.SpyObj<VotingService>;
    loggingService = TestBed.inject(LoggingService) as jasmine.SpyObj<LoggingService>;
    snackBar = TestBed.inject(MatSnackBar) as jasmine.SpyObj<MatSnackBar>;

    // Initialize the component's result property (injected via constructor)
    component.result = mockResult;

    // Setup default component input
    component.result_input = {
      score: 0.85,
      statement_text: 'Test statement',
      statement_similarity_score: 0.8,
      reply_relevance: 0.9,
      commentary_result: {
        id: '123e4567-e89b-12d3-a456-426614174000',
        text: 'Test text',
        content_type: 'commentary',
        created: '2024-01-01',
        last_modified: '2024-01-01',
        original_author: 'Test Author',
        last_modified_by: 'Test Author',
        authors: [],
        edit_history: [],
        status: 'approved' as any,
        origin: 'user' as any,
        most_similar_similarity_score: 0,
        most_similar_content_id: '',
        report_count: 0,
        is_archived: false,
        report_flagged: false,
        rejection_reason: '',
        block_reason: '',
        visibility: 'public' as any,
        title: 'Test title',
        long_text: 'Long test text',
        short_text: 'Short text',
        style: 'default',
        short_title: 'Short title',
        keywords: [],
        speaker: 'Test Speaker',
        context: 'Test context',
        claim: 'Test claim',
        usage_count: 0,
        references: [] // Add references array
      },
      user_vote: null
    } as any;

    // Initialize the component to set up debounce subscriptions
    component.ngOnInit();
  });

  describe('Vote Initialization', () => {
    it('should initialize with no votes', () => {
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    });

    it('should initialize with like from search results', () => {
      (component.result_input as any).user_vote = 'like';
      component.ngOnInit();
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    });

    it('should initialize with dislike from search results', () => {
      (component.result_input as any).user_vote = 'dislike';
      component.ngOnInit();
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    });
  });

  describe('Like Functionality', () => {
    it('should set like when not voted', fakeAsync(() => {
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: 'like',
        message: 'Like set successfully'
      };
      votingService.setLike.and.returnValue(of(mockResponse));

      component.toggleLike();
      tick(50); // Wait for debounce

      expect(votingService.setLike).toHaveBeenCalledWith(
        component.result_input.commentary_result.id
      );
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should remove like when already liked', fakeAsync(() => {
      component.isLiked = true;
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: null,
        message: 'Like removed successfully'
      };
      votingService.removeLike.and.returnValue(of(mockResponse));

      component.toggleLike();
      tick(50); // Wait for debounce

      expect(votingService.removeLike).toHaveBeenCalledWith(
        component.result_input.commentary_result.id
      );
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should change from dislike to like', fakeAsync(() => {
      component.isDisliked = true;
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: 'like',
        message: 'Like set successfully'
      };
      votingService.setLike.and.returnValue(of(mockResponse));

      component.toggleLike();
      tick(50); // Wait for debounce

      expect(votingService.setLike).toHaveBeenCalledWith(
        component.result_input.commentary_result.id
      );
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should handle error when setting like', fakeAsync(() => {
      const error = { status: 500, message: 'Server error' };
      votingService.setLike.and.returnValue(throwError(() => error));

      // Initial state
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();

      component.toggleLike();
      // After optimistic update, before API call
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();

      tick(50); // Wait for debounce and error handling

      expect(snackBar.open).toHaveBeenCalledWith(
        'Fehler beim Abstimmen',
        'Schließen',
        { duration: 3000 }
      );
      // After error, state should be rolled back
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));
  });

  describe('Vote Button State Management', () => {
    it('should prevent multiple simultaneous vote requests', fakeAsync(() => {
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: 'like',
        message: 'Like set successfully'
      };
      votingService.setLike.and.returnValue(of(mockResponse));

      // Set isVoting to true to simulate ongoing vote
      component.isVoting = true;
      const initialLikedState = component.isLiked;
      const initialDislikedState = component.isDisliked;

      component.toggleLike();
      tick(50);

      // Should not make API call when isVoting is true
      expect(votingService.setLike.calls.count()).toBe(0);
      // State should remain unchanged when isVoting is true
      expect(component.isLiked).toBe(initialLikedState);
      expect(component.isDisliked).toBe(initialDislikedState);
    }));

    it('should maintain correct button states after rapid toggling', fakeAsync(() => {
      const mockLikeResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: 'like',
        message: 'Like set successfully'
      };
      votingService.setLike.and.returnValue(of(mockLikeResponse));
      votingService.removeLike.and.returnValue(of({
        content_id: component.result_input.commentary_result.id,
        vote_type: 'none',
        message: 'Like removed'
      }));

      // Rapid toggling
      component.toggleLike(); // Set like
      component.toggleLike(); // Remove like
      component.toggleLike(); // Set like again

      tick(50); // Wait for debounce

      // Should end up with like set
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
      // Only the last action should be executed due to debouncing
      expect(votingService.setLike.calls.count()).toBe(1);
    }));

    it('should reset vote states for non-authenticated users', fakeAsync(() => {
      // Mock non-authenticated user
      const authService = TestBed.inject(AuthService) as jasmine.SpyObj<AuthService>;
      authService.getUserInfo.and.returnValue(null);

      // Create a mock for snackBar.open that returns an observable with onAction
      const snackBarRef = {
        onAction: jasmine.createSpy('onAction').and.returnValue(of())
      };
      snackBar.open.and.returnValue(snackBarRef as any);

      // Start with liked state to verify it gets reset
      component.isLiked = false;
      component.isDisliked = false;

      component.toggleLike();
      tick(50); // Wait for debounce

      // States should be reset to false after auth check fails
      expect(component.isLiked).toBeFalsy();
      expect(component.isDisliked).toBeFalsy();
      expect(snackBar.open).toHaveBeenCalledWith(
        'Bitte melde dich an, um abzustimmen',
        'Anmelden',
        { duration: 5000 }
      );
    }));
  });

  describe('Dislike Functionality', () => {
    it('should set dislike when not voted', fakeAsync(() => {
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: 'dislike',
        message: 'Dislike set successfully'
      };
      votingService.setDislike.and.returnValue(of(mockResponse));

      component.toggleDislike();
      tick(50); // Wait for debounce

      expect(votingService.setDislike).toHaveBeenCalledWith(
        component.result_input.commentary_result.id
      );
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    }));

    it('should remove dislike when already disliked', fakeAsync(() => {
      component.isDisliked = true;
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: null,
        message: 'Dislike removed successfully'
      };
      votingService.removeDislike.and.returnValue(of(mockResponse));

      component.toggleDislike();
      tick(50); // Wait for debounce

      expect(votingService.removeDislike).toHaveBeenCalledWith(
        component.result_input.commentary_result.id
      );
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should change from like to dislike', fakeAsync(() => {
      component.isLiked = true;
      const mockResponse = {
        content_id: component.result_input.commentary_result.id,
        vote_type: 'dislike',
        message: 'Dislike set successfully'
      };
      votingService.setDislike.and.returnValue(of(mockResponse));

      component.toggleDislike();
      tick(50); // Wait for debounce

      expect(votingService.setDislike).toHaveBeenCalledWith(
        component.result_input.commentary_result.id
      );
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    }));

    it('should handle error when setting dislike', fakeAsync(() => {
      const error = { status: 500, message: 'Server error' };
      votingService.setDislike.and.returnValue(throwError(() => error));

      // Initial state
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();

      component.toggleDislike();
      // After optimistic update, before API call
      expect(component.isDisliked).toBeTrue();
      expect(component.isLiked).toBeFalse();

      tick(50); // Wait for debounce and error handling

      expect(snackBar.open).toHaveBeenCalledWith(
        'Fehler beim Abstimmen',
        'Schließen',
        { duration: 3000 }
      );
      // After error, state should be rolled back
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    }));
  });

  describe('Vote State Management', () => {
    it('should update vote state when input changes with like', () => {
      component.result_input = {
        ...component.result_input
      };
      (component.result_input as any).user_vote = 'like';
      component.ngOnChanges({
        result_input: {
          currentValue: component.result_input,
          previousValue: null,
          firstChange: true,
          isFirstChange: () => true
        }
      });

      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    });

    it('should update vote state when input changes with dislike', () => {
      component.result_input = {
        ...component.result_input
      };
      (component.result_input as any).user_vote = 'dislike';
      component.ngOnChanges({
        result_input: {
          currentValue: component.result_input,
          previousValue: null,
          firstChange: true,
          isFirstChange: () => true
        }
      });

      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeTrue();
    });

    it('should reset vote state when input changes to no vote', () => {
      // Set initial vote state
      component.isLiked = true;
      component.isDisliked = false;

      // Create new input with no vote
      const newInput = {
        ...component.result_input,
        user_vote: undefined  // Use undefined instead of null for TypeScript compatibility
      };

      // Update component input
      component.result_input = newInput;

      // Trigger change detection
      component.ngOnChanges({
        result_input: {
          currentValue: newInput,
          previousValue: component.result_input,
          firstChange: false,
          isFirstChange: () => false
        }
      });

      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    });
  });

  describe('Vote Button State', () => {
    beforeEach(() => {
      // Ensure component is properly initialized before each test
      component.ngOnInit();
      fixture.detectChanges(); // Initial change detection
    });

    it('should apply active-button class when liked', () => {
      // Set up the result with user_vote to simulate a liked state
      (component.result_input as any).user_vote = 'like';
      // Also set on result for backward compatibility
      (component.result as any).user_vote = 'like';
      // Call ngOnInit to properly initialize the component
      component.ngOnInit();
      // Force change detection for OnPush strategy
      fixture.componentRef.changeDetectorRef.markForCheck();
      fixture.detectChanges();

      const buttons = fixture.nativeElement.querySelectorAll('.commentary-vote-button');
      const likeButton = buttons[0]; // First button is like (thumb_up)
      expect(likeButton?.classList.contains('active-button')).toBeTrue();
    });

    it('should apply active-button class when disliked', () => {
      // Set up the result with user_vote to simulate a disliked state
      (component.result_input as any).user_vote = 'dislike';
      // Also set on result for backward compatibility
      (component.result as any).user_vote = 'dislike';
      // Call ngOnInit to properly initialize the component
      component.ngOnInit();
      // Force change detection for OnPush strategy
      fixture.componentRef.changeDetectorRef.markForCheck();
      fixture.detectChanges();

      const buttons = fixture.nativeElement.querySelectorAll('.commentary-vote-button');
      const dislikeButton = buttons[1]; // Second button is dislike (thumb_down)
      expect(dislikeButton?.classList.contains('active-button')).toBeTrue();
    });

    it('should not apply active-button class when not voted', () => {
      fixture.detectChanges();

      const buttons = fixture.nativeElement.querySelectorAll('.commentary-vote-button');
      buttons.forEach((button: any) => {
        expect(button?.classList.contains('active-button')).toBeFalse();
      });
    });
  });

  describe('Rate Limiting', () => {
    it('should handle rate limit error gracefully for like', fakeAsync(() => {
      const error = {
        status: 429,
        headers: {
          get: (header: string) => header === 'Retry-After' ? '30' : null
        }
      };
      votingService.setLike.and.returnValue(throwError(() => error));

      component.toggleLike();
      tick(50); // Wait for debounce

      expect(snackBar.open).toHaveBeenCalledWith(
        'Zu viele Anfragen. Bitte warte 30 Sekunden.',
        'OK',
        { duration: 5000 }
      );
    }));

    it('should handle rate limit error gracefully for dislike', fakeAsync(() => {
      const error = {
        status: 429,
        headers: {
          get: (header: string) => header === 'Retry-After' ? '30' : null
        }
      };
      votingService.setDislike.and.returnValue(throwError(() => error));

      component.toggleDislike();
      tick(50); // Wait for debounce

      expect(snackBar.open).toHaveBeenCalledWith(
        'Zu viele Anfragen. Bitte warte 30 Sekunden.',
        'OK',
        { duration: 5000 }
      );
    }));
  });
});
