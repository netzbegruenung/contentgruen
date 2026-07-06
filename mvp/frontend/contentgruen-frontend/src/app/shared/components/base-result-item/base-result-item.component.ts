import {
  Directive,
  EventEmitter,
  Output,
  Input,
  SimpleChanges,
  ChangeDetectorRef,
  OnDestroy,
  OnInit,
  OnChanges,
} from '@angular/core';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { UsageTrackingService } from '../../../services/usage-tracking.service';
import { VotingService } from '../../../services/voting.service';
import { AuthService } from '../../../auth/auth.service';
import { LoggingService } from '../../../services/logging.service';
import { ReportDialogComponent } from '../report-dialog/report-dialog.component';
import { BaseContentResult, BaseSearchResult } from '../../../services/dtos/commonDtos';

/**
 * Shared mechanism for every content-type result item, written once (CONTENT_MODEL.md,
 * frontend Seam contract). Owns voting (optimistic update + debounce + rollback),
 * 401/403/429 + auth handling, badges, usage-count animation, copy, statement display,
 * and score formatting. Per-type components extend this and supply only:
 *   - the `content` getter (the type's nested result, Seam 2)
 *   - their own template (Seam 3)
 *   - `contentType` (for the report dialog) and optionally `getCopyText()`.
 *
 * This is a `@Directive()` (not `@Component`) so subclasses keep their own template,
 * selector, and `@Inject('RESULT')` constructor while inheriting all behavior.
 */
@Directive()
export abstract class BaseResultItemComponent<TResult extends BaseSearchResult>
  implements OnInit, OnChanges, OnDestroy
{
  @Output() likeToggled = new EventEmitter<string>();
  @Output() dislikeToggled = new EventEmitter<string>();
  @Input() result_input!: TResult;

  /** The per-type nested content result (Seam 2). */
  abstract get content(): BaseContentResult;
  /** Identifier passed to the report dialog. */
  protected abstract readonly contentType: string;
  /** Text copied to clipboard; overridable (e.g. commentary copies the displayed variant). */
  protected getCopyText(): string {
    return this.content.text || '';
  }
  /** Hook for subclasses to derive extra cached values after the shared ones. */
  protected afterCachedValues(): void {}

  isLiked = false;
  isDisliked = false;
  showScoreDetails = false;
  isVoting = false; // Prevent multiple simultaneous votes

  // Debouncing subjects - carry the 'was' state for decision making
  private likeSubject = new Subject<boolean>(); // true if was liked before toggle
  private dislikeSubject = new Subject<boolean>(); // true if was disliked before toggle
  private destroy$ = new Subject<void>();

  // Cached computed properties
  relevanceColor = '';
  scoreTooltip = '';

  // Badge visibility flags
  showNewBadge = false;
  showTrendingBadge = false;

  // Badge label expansion state (for mobile)
  expandedNewBadge = false;
  expandedTrendingBadge = false;

  // Animation states
  copyAnimationActive = false;
  usageCountAnimated = false;
  currentUsageCount = 0;

  // Statement expansion
  isStatementExpanded = false;
  hasStatement = false;
  statementPreviewText = '';
  statementFullText = '';
  statementSimilarity = 0;
  replyRelevance = 0;

  constructor(
    public result: TResult,
    protected clipboard: Clipboard,
    protected snackBar: MatSnackBar,
    protected cdr: ChangeDetectorRef,
    protected usageTrackingService: UsageTrackingService,
    protected votingService: VotingService,
    protected authService: AuthService,
    protected logger: LoggingService,
    protected dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    // If result_input is provided via @Input, use it
    if (this.result_input) {
      this.result = this.result_input;
    }

    this.updateCachedValues();
    this.initializeVoteState();

    // Setup debounced vote handlers with reduced delay for responsiveness
    this.likeSubject
      .pipe(debounceTime(50), distinctUntilChanged())
      .subscribe((wasLiked) => this.performLikeVote(wasLiked));

    this.dislikeSubject
      .pipe(debounceTime(50), distinctUntilChanged())
      .subscribe((wasDisliked) => this.performDislikeVote(wasDisliked));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['result_input']) {
      this.result = changes['result_input'].currentValue;
      this.updateCachedValues();
      this.initializeVoteState();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.likeSubject.complete();
    this.dislikeSubject.complete();
  }

  private initializeVoteState(): void {
    if (this.result) {
      if (this.result.user_vote) {
        this.isLiked = this.result.user_vote === 'like';
        this.isDisliked = this.result.user_vote === 'dislike';
      } else {
        this.isLiked = false;
        this.isDisliked = false;
      }
    }
  }

  protected updateCachedValues(): void {
    if (!this.result) return;
    this.updateBadgeVisibility();
    this.currentUsageCount = this.content.usage_count || 0;
    this.updateStatementData();
    this.afterCachedValues();
  }

  private updateBadgeVisibility(): void {
    if (!this.result) return;

    // New: less than 24 hours old
    const created = this.content.created;
    if (created) {
      const createdDate = new Date(created);
      const now = new Date();
      const diffHours = (now.getTime() - createdDate.getTime()) / (1000 * 60 * 60);
      this.showNewBadge = diffHours < 24;
    }

    // Trending: 5+ uses
    const usageCount = this.content.usage_count || 0;
    this.showTrendingBadge = usageCount >= 5;
  }

  toggleLike(): void {
    if (this.isVoting) {
      return;
    }
    const wasLiked = this.isLiked;
    this.isLiked = !wasLiked;
    if (this.isLiked) {
      this.isDisliked = false;
    }
    this.cdr.markForCheck();
    this.likeSubject.next(wasLiked);
  }

  private performLikeVote(wasLiked: boolean): void {
    const userInfo = this.authService.getUserInfo();
    if (!userInfo || !userInfo.isAuthenticated) {
      this.isLiked = wasLiked;
      this.isDisliked = false;
      this.cdr.markForCheck();
      this.promptLogin();
      return;
    }

    if (this.isVoting) {
      return;
    }

    const contentId = this.content.id;
    this.isVoting = true;

    const voteObservable = wasLiked
      ? this.votingService.removeLike(contentId)
      : this.votingService.setLike(contentId);

    voteObservable.subscribe({
      next: () => {
        this.likeToggled.emit(contentId);
        this.isVoting = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        this.logger.error('Failed to submit like:', error);
        this.isLiked = wasLiked;
        this.isDisliked = false;
        this.isVoting = false;
        this.handleVoteError(error);
        this.cdr.markForCheck();
      },
    });
  }

  toggleDislike(): void {
    if (this.isVoting) {
      return;
    }
    const wasDisliked = this.isDisliked;
    this.isDisliked = !wasDisliked;
    if (this.isDisliked) {
      this.isLiked = false;
    }
    this.cdr.markForCheck();
    this.dislikeSubject.next(wasDisliked);
  }

  private performDislikeVote(wasDisliked: boolean): void {
    const userInfo = this.authService.getUserInfo();
    if (!userInfo || !userInfo.isAuthenticated) {
      this.isLiked = false;
      this.isDisliked = wasDisliked;
      this.cdr.markForCheck();
      this.promptLogin();
      return;
    }

    if (this.isVoting) {
      return;
    }

    const contentId = this.content.id;
    this.isVoting = true;

    const voteObservable = wasDisliked
      ? this.votingService.removeDislike(contentId)
      : this.votingService.setDislike(contentId);

    voteObservable.subscribe({
      next: () => {
        this.dislikeToggled.emit(contentId);
        this.isVoting = false;
        this.cdr.markForCheck();
      },
      error: (error) => {
        this.logger.error('Failed to submit dislike:', error);
        this.isLiked = false;
        this.isDisliked = wasDisliked;
        this.isVoting = false;
        this.handleVoteError(error);
        this.cdr.markForCheck();
      },
    });
  }

  private promptLogin(): void {
    this.snackBar
      .open('Bitte melde dich an, um abzustimmen', 'Anmelden', { duration: 5000 })
      .onAction()
      .subscribe(() => {
        this.authService.login();
      });
  }

  private handleVoteError(error: any): void {
    if (error.status === 401 || error.status === 403) {
      this.promptLogin();
    } else if (error.status === 429) {
      const retryAfter = error.headers?.get('Retry-After') || '60';
      this.snackBar.open(`Zu viele Anfragen. Bitte warte ${retryAfter} Sekunden.`, 'OK', {
        duration: 5000,
      });
    } else {
      this.snackBar.open('Fehler beim Abstimmen', 'Schließen', { duration: 3000 });
    }
  }

  protected copyContent(): void {
    const textToCopy = this.getCopyText();
    if (!textToCopy) {
      return;
    }
    this.clipboard.copy(textToCopy);
    this.snackBar.open('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });

    this.copyAnimationActive = true;
    setTimeout(() => {
      this.copyAnimationActive = false;
      this.cdr.markForCheck();
    }, 600);

    const contentId = this.content.id;
    if (contentId) {
      this.usageTrackingService.trackContentUsage(contentId);
      this.animateUsageCountIncrement();
    }

    this.cdr.markForCheck();
  }

  private animateUsageCountIncrement(): void {
    this.currentUsageCount++;
    this.usageCountAnimated = true;
    setTimeout(() => {
      this.usageCountAnimated = false;
      this.cdr.markForCheck();
    }, 300);
    this.cdr.markForCheck();
  }

  protected calculateRelevanceColor(score: number): string {
    if (score <= 0.5) {
      return `rgb(220, 0, 0)`;
    } else if (score <= 0.75) {
      const t = (score - 0.5) / 0.25;
      const green = Math.round(220 * t);
      return `rgb(220, ${green}, 0)`;
    } else {
      const t = (score - 0.75) / 0.25;
      const red = Math.round(220 * (1 - t));
      return `rgb(${red}, 220, 0)`;
    }
  }

  getRelevanceColor(score: number): string {
    return this.relevanceColor || this.calculateRelevanceColor(score);
  }

  toggleScoreDetails(): void {
    this.showScoreDetails = !this.showScoreDetails;
    this.cdr.markForCheck();
  }

  toggleNewBadge(event: Event): void {
    event.stopPropagation();
    this.expandedNewBadge = !this.expandedNewBadge;
    if (this.expandedNewBadge) {
      setTimeout(() => {
        this.expandedNewBadge = false;
        this.cdr.markForCheck();
      }, 3000);
    }
    this.cdr.markForCheck();
  }

  toggleTrendingBadge(event: Event): void {
    event.stopPropagation();
    this.expandedTrendingBadge = !this.expandedTrendingBadge;
    if (this.expandedTrendingBadge) {
      setTimeout(() => {
        this.expandedTrendingBadge = false;
        this.cdr.markForCheck();
      }, 3000);
    }
    this.cdr.markForCheck();
  }

  getScoreTooltip(): string {
    return this.scoreTooltip;
  }

  getScoreFontSize(): string {
    const score = Math.round(this.result.score * 100);
    if (score === 100) {
      return '16px';
    } else if (score >= 10) {
      return '18px';
    } else {
      return '20px';
    }
  }

  private updateStatementData(): void {
    this.hasStatement =
      !!this.result.statement_text && this.result.statement_text.trim().length > 0;
    this.statementFullText = this.result.statement_text || '';
    this.statementPreviewText = this.truncateText(this.statementFullText, 50);
    this.statementSimilarity = Math.round((this.result.statement_similarity_score || 0) * 100);
    this.replyRelevance = Math.round((this.result.reply_relevance || 0) * 100);
  }

  toggleStatementExpanded(): void {
    this.isStatementExpanded = !this.isStatementExpanded;
    this.cdr.markForCheck();
  }

  protected truncateText(text: string, maxLength: number): string {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength).trim() + '...';
  }

  openReportDialog(): void {
    this.dialog.open(ReportDialogComponent, {
      width: '500px',
      data: {
        contentId: this.content.id,
        contentType: this.contentType,
      },
    });
  }
}
