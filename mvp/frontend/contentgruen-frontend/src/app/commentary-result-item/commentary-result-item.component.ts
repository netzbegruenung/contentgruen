import {
  Component,
  Inject,
  ChangeDetectorRef,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommentarySearchResult } from '../services/dtos/searchDtos';
import { BaseContentResult } from '../services/dtos/commonDtos';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDialog } from '@angular/material/dialog';
import { Clipboard } from '@angular/cdk/clipboard';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { UsageTrackingService } from '../services/usage-tracking.service';
import { VotingService } from '../services/voting.service';
import { AuthService } from '../auth/auth.service';
import { LoggingService } from '../services/logging.service';
import { RelativeTimePipe } from '../shared/pipes/relative-time.pipe';
import { trigger, transition, style, animate } from '@angular/animations';
import { BaseResultItemComponent } from '../shared/components/base-result-item/base-result-item.component';

@Component({
  selector: 'app-commentary-result-item',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
    RelativeTimePipe,
  ],
  templateUrl: './commentary-result-item.component.html',
  styleUrls: ['./commentary-result-item.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [
    trigger('expandCollapse', [
      transition(':enter', [
        style({ height: '0', opacity: 0 }),
        animate('300ms cubic-bezier(0.4, 0, 0.2, 1)', style({ height: '*', opacity: 1 })),
      ]),
      transition(':leave', [
        animate('200ms cubic-bezier(0.4, 0, 0.2, 1)', style({ height: '0', opacity: 0 })),
      ]),
    ]),
  ],
})
export class CommentaryResultItemComponent extends BaseResultItemComponent<CommentarySearchResult> {
  protected readonly contentType = 'commentary';

  // Commentary-specific: short/standard/long text variants
  textMode: 'short' | 'standard' | 'long' = 'standard';
  hasShortText = false;
  hasLongText = false;
  displayedText = '';

  get content(): BaseContentResult {
    return this.result.commentary_result;
  }

  constructor(
    @Inject('RESULT') result: CommentarySearchResult,
    clipboard: Clipboard,
    snackBar: MatSnackBar,
    cdr: ChangeDetectorRef,
    usageTrackingService: UsageTrackingService,
    votingService: VotingService,
    authService: AuthService,
    logger: LoggingService,
    dialog: MatDialog,
  ) {
    super(
      result,
      clipboard,
      snackBar,
      cdr,
      usageTrackingService,
      votingService,
      authService,
      logger,
      dialog,
    );
  }

  protected override afterCachedValues(): void {
    const commentary = this.result.commentary_result;
    this.hasShortText = !!commentary.short_text;
    this.hasLongText = !!commentary.long_text;
    this.updateDisplayedText();
  }

  protected override getCopyText(): string {
    return this.displayedText || this.result.commentary_result.text || '';
  }

  updateDisplayedText(): void {
    if (!this.result) return;
    const commentary = this.result.commentary_result;
    switch (this.textMode) {
      case 'short':
        this.displayedText = commentary.short_text || commentary.text;
        break;
      case 'long':
        this.displayedText = commentary.long_text || commentary.text;
        break;
      case 'standard':
      default:
        this.displayedText = commentary.text;
        break;
    }
    this.cdr.markForCheck();
  }

  onTextModeChange(mode: 'short' | 'standard' | 'long'): void {
    this.textMode = mode;
    this.updateDisplayedText();
  }

  /** Template hook (kept for compatibility with the existing template). */
  copyCommentary(): void {
    this.copyContent();
  }
}
