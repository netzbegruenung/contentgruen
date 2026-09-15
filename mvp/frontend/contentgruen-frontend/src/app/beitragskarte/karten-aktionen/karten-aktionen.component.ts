import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { AuthService } from '../../auth/auth.service';
import { LoggingService } from '../../services/logging.service';
import { UsageTrackingService } from '../../services/usage-tracking.service';
import { VotingService } from '../../services/voting.service';
import { ReportDialogComponent } from '../../shared/components/report-dialog/report-dialog.component';

/**
 * Die Aktionsleiste der vollen Beitragskarte: abstimmen, kopieren, melden.
 *
 * Die Logik stammt 1:1 aus BaseResultItemComponent (optimistisches Abstimmen mit
 * Entprellung und Ruecknahme, 401/403/429-Behandlung). Sie sitzt in einer eigenen
 * Komponente, damit kompakte Karten und Rohlinge, die als Ganzes antippbar sind,
 * keine Knoepfe und keine Dienste mitschleppen.
 *
 * In der Formular-Vorschau ist die Leiste sichtbar wie in der Suche, reagiert aber
 * nicht: kein Zeiger, kein Fokus, aria-disabled. Ausgegraut wird sie bewusst nicht,
 * die Vorschau soll zeigen, wie der Beitrag aussehen wird.
 */
@Component({
  selector: 'app-karten-aktionen',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatMenuModule, MatTooltipModule],
  templateUrl: './karten-aktionen.component.html',
  styleUrls: ['./karten-aktionen.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class.ist-vorschau]': 'vorschau' },
})
export class KartenAktionenComponent implements OnInit, OnChanges, OnDestroy {
  @Input({ required: true }) inhaltId!: string;
  /** Registry-Schluessel, geht an den Melde-Dialog. */
  @Input() typ: string | null = null;
  @Input() kopierText = '';
  @Input() kopierBeschriftung = 'Kopieren';
  @Input() stimme?: 'like' | 'dislike';
  @Input() vorschau = false;
  /** Aus beim eigenen Beitrag (Album-Sheet in Meine Beitraege); Kopieren und Melden bleiben. */
  @Input() abstimmenSichtbar = true;

  @Output() likeToggled = new EventEmitter<string>();
  @Output() dislikeToggled = new EventEmitter<string>();
  /** Nach erfolgreichem Kopieren; die Karte zaehlt daraufhin ihre Nutzung hoch. */
  @Output() kopiert = new EventEmitter<void>();

  isLiked = false;
  isDisliked = false;
  isVoting = false;
  copyAnimationActive = false;

  // Traegt den Zustand vor dem Umschalten, danach entscheidet die Entprellung.
  private likeSubject = new Subject<boolean>();
  private dislikeSubject = new Subject<boolean>();
  private abonniert = false;

  constructor(
    private clipboard: Clipboard,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef,
    private usageTrackingService: UsageTrackingService,
    private votingService: VotingService,
    private authService: AuthService,
    private logger: LoggingService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void {
    this.initializeVoteState();

    if (this.abonniert) {
      return;
    }
    this.abonniert = true;
    this.likeSubject
      .pipe(debounceTime(50), distinctUntilChanged())
      .subscribe((wasLiked) => this.performLikeVote(wasLiked));
    this.dislikeSubject
      .pipe(debounceTime(50), distinctUntilChanged())
      .subscribe((wasDisliked) => this.performDislikeVote(wasDisliked));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['stimme'] || changes['inhaltId']) {
      this.initializeVoteState();
    }
  }

  ngOnDestroy(): void {
    this.likeSubject.complete();
    this.dislikeSubject.complete();
  }

  toggleLike(): void {
    if (this.vorschau || this.isVoting) {
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

  toggleDislike(): void {
    if (this.vorschau || this.isVoting) {
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

  kopieren(): void {
    if (this.vorschau || !this.kopierText) {
      return;
    }
    this.clipboard.copy(this.kopierText);
    this.snackBar.open('Erfolgreich kopiert!', 'Schließen', { duration: 1500 });

    this.copyAnimationActive = true;
    setTimeout(() => {
      this.copyAnimationActive = false;
      this.cdr.markForCheck();
    }, 600);

    if (this.inhaltId) {
      this.usageTrackingService.trackContentUsage(this.inhaltId);
      this.kopiert.emit();
    }
    this.cdr.markForCheck();
  }

  openReportDialog(): void {
    if (this.vorschau) {
      return;
    }
    this.dialog.open(ReportDialogComponent, {
      width: '500px',
      data: { contentId: this.inhaltId, contentType: this.typ ?? '' },
    });
  }

  private initializeVoteState(): void {
    this.isLiked = this.stimme === 'like';
    this.isDisliked = this.stimme === 'dislike';
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

    const contentId = this.inhaltId;
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

    const contentId = this.inhaltId;
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
}
