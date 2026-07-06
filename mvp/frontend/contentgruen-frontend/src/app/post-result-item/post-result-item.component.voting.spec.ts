import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { PostResultItemComponent } from './post-result-item.component';
import { VotingService } from '../services/voting.service';
import { LoggingService } from '../services/logging.service';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { AuthService } from '../auth/auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Clipboard } from '@angular/cdk/clipboard';
import { of, throwError } from 'rxjs';
import { NO_ERRORS_SCHEMA } from '@angular/core';

/**
 * Step 6 gate (frontend, "test 8"): a Post is rendered and votable through exactly
 * the same shared mechanism as every other content type. PostResultItemComponent adds
 * only the `content` getter (post_result) + its template; voting/badges/copy are
 * inherited from BaseResultItemComponent. This pins that the registry-driven Post
 * presentation works end-to-end under headless Chrome.
 */
describe('PostResultItemComponent - Render & Voting', () => {
  let component: PostResultItemComponent;
  let fixture: ComponentFixture<PostResultItemComponent>;
  let votingService: jasmine.SpyObj<VotingService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  const POST_ID = '123e4567-e89b-12d3-a456-426614174999';

  function buildResult(): any {
    return {
      score: 0.91,
      statement_text: 'Test statement',
      statement_similarity_score: 0.8,
      reply_relevance: 0.9,
      post_result: {
        id: POST_ID,
        text: 'Erneuerbare Energien konsequent ausbauen',
        content_type: 'post',
        created: '2024-01-01',
        last_modified: '2024-01-01',
        original_author: 'importer',
        last_modified_by: 'importer',
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
        title: 'Klimapost',
        references: [],
        references_count: 0,
        usage_count: 0,
        platform: 'mastodon',
        author: '@gruen',
        url: 'https://social.example/posts/1',
        engagement: 42,
      },
      user_vote: null,
    };
  }

  beforeEach(async () => {
    const votingSpy = jasmine.createSpyObj('VotingService', [
      'setLike',
      'removeLike',
      'setDislike',
      'removeDislike',
    ]);
    const loggingSpy = jasmine.createSpyObj('LoggingService', [
      'logInteraction',
      'logError',
      'error',
      'debug',
      'info',
      'warn',
    ]);
    const snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);
    const clipboardSpy = jasmine.createSpyObj('Clipboard', ['copy']);
    const usageTrackingSpy = jasmine.createSpyObj('UsageTrackingService', [
      'trackContentUsage',
    ]);
    const authServiceSpy = jasmine.createSpyObj('AuthService', ['getUserInfo', 'login']);
    authServiceSpy.getUserInfo.and.returnValue({
      isAuthenticated: true,
      userId: 'test-user',
    });

    await TestBed.configureTestingModule({
      imports: [PostResultItemComponent, HttpClientTestingModule],
      providers: [
        { provide: 'RESULT', useValue: buildResult() },
        { provide: VotingService, useValue: votingSpy },
        { provide: LoggingService, useValue: loggingSpy },
        { provide: MatSnackBar, useValue: snackBarSpy },
        { provide: Clipboard, useValue: clipboardSpy },
        { provide: UsageTrackingService, useValue: usageTrackingSpy },
        { provide: AuthService, useValue: authServiceSpy },
      ],
      schemas: [NO_ERRORS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(PostResultItemComponent);
    component = fixture.componentInstance;
    votingService = TestBed.inject(VotingService) as jasmine.SpyObj<VotingService>;
    snackBar = TestBed.inject(MatSnackBar) as jasmine.SpyObj<MatSnackBar>;

    component.result = buildResult();
    component.result_input = buildResult();
    component.ngOnInit();
  });

  describe('Rendering', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should expose the post_result as the shared content', () => {
      expect(component.content.id).toBe(POST_ID);
      expect(component.content.content_type).toBe('post');
    });

    it('should render the post title, body and platform/author', () => {
      fixture.detectChanges();
      const text: string = fixture.nativeElement.textContent;
      expect(text).toContain('Klimapost');
      expect(text).toContain('Erneuerbare Energien konsequent ausbauen');
      expect(text).toContain('@gruen');
      expect(text).toContain('mastodon');
    });

    it('should render two vote buttons', () => {
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.post-vote-button');
      expect(buttons.length).toBe(2);
    });
  });

  describe('Voting', () => {
    it('should initialize with no votes', () => {
      expect(component.isLiked).toBeFalse();
      expect(component.isDisliked).toBeFalse();
    });

    it('should set like when not voted', fakeAsync(() => {
      votingService.setLike.and.returnValue(of({} as any));

      component.toggleLike();
      tick(50);

      expect(votingService.setLike).toHaveBeenCalledWith(POST_ID);
      expect(component.isLiked).toBeTrue();
      expect(component.isDisliked).toBeFalse();
    }));

    it('should remove like when already liked', fakeAsync(() => {
      component.isLiked = true;
      votingService.removeLike.and.returnValue(of({} as any));

      component.toggleLike();
      tick(50);

      expect(votingService.removeLike).toHaveBeenCalledWith(POST_ID);
      expect(component.isLiked).toBeFalse();
    }));

    it('should set dislike when not voted', fakeAsync(() => {
      votingService.setDislike.and.returnValue(of({} as any));

      component.toggleDislike();
      tick(50);

      expect(votingService.setDislike).toHaveBeenCalledWith(POST_ID);
      expect(component.isDisliked).toBeTrue();
      expect(component.isLiked).toBeFalse();
    }));

    it('should roll back and notify on vote error', fakeAsync(() => {
      votingService.setLike.and.returnValue(throwError(() => ({ status: 500 })));

      component.toggleLike();
      expect(component.isLiked).toBeTrue(); // optimistic
      tick(50);

      expect(snackBar.open).toHaveBeenCalledWith(
        'Fehler beim Abstimmen',
        'Schließen',
        { duration: 3000 },
      );
      expect(component.isLiked).toBeFalse(); // rolled back
    }));

    it('should apply active-button class when liked', () => {
      (component.result_input as any).user_vote = 'like';
      (component.result as any).user_vote = 'like';
      component.ngOnInit();
      fixture.componentRef.changeDetectorRef.markForCheck();
      fixture.detectChanges();

      const buttons = fixture.nativeElement.querySelectorAll('.post-vote-button');
      expect(buttons[0]?.classList.contains('active-button')).toBeTrue();
    });
  });
});
