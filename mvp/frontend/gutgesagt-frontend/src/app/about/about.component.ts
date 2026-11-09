import { Component } from '@angular/core';
import { NgFor } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { hilfeOeffnen } from '../help-dialog/help-dialog.component';
import { feedbackDialogOeffnen } from '../shared/feedback/feedback-dialog.component';
import { NICHT_JEDE_AUSSAGE } from '../shared/schreibregeln';
import { ORGANISATION } from '../shared/organisation';
import { SiegelComponent } from '../shared/components/siegel/siegel.component';

/** Die Über-Seite: wofür Gut gesagt da ist, für wen und wie man mitmacht (docs/VISION.md, #345). */
@Component({
  selector: 'app-about',
  standalone: true,
  imports: [
    NgFor,
    SiegelComponent,
    MatButtonModule,
    MatIconModule,
    RouterModule
  ],
  templateUrl: './about.component.html',
  styleUrls: ['./about.component.scss']
})
export class AboutComponent {
  readonly nichtJedeAussage = NICHT_JEDE_AUSSAGE;
  readonly organisation = ORGANISATION;
  /** Beispielsiegel unter „Bewerten“: neu, dann Güte 1 bis 10 (#427). */
  readonly beispielGueten: (number | null)[] = [null, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  constructor(private dialog: MatDialog) {}

  openHelpDialog(): void {
    hilfeOeffnen(this.dialog);
  }

  openFeedbackDialog(): void {
    feedbackDialogOeffnen(this.dialog);
  }
}
