import {
  Component,
  Input,
  Inject,
  ChangeDetectorRef,
  ChangeDetectionStrategy,
} from '@angular/core';
import { GenerictextSearchResult } from '../services/dtos/searchDtos';
import { BaseContentResult } from '../services/dtos/commonDtos';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
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
  selector: 'app-generictext-result-item',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
    RelativeTimePipe,
  ],
  templateUrl: './generictext-result-item.component.html',
  styleUrls: ['./generictext-result-item.component.scss'],
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
export class GenerictextResultItemComponent extends BaseResultItemComponent<GenerictextSearchResult> {
  @Input() isPreview = false;

  protected readonly contentType = 'generictext';

  get content(): BaseContentResult {
    return this.result.generictext_result;
  }

  constructor(
    @Inject('RESULT') result: GenerictextSearchResult,
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

  /** Template hook (kept for compatibility with the existing template). */
  copyGenerictext(): void {
    this.copyContent();
  }
}
