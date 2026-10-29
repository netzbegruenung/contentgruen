import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { HelpDialogComponent } from '../help-dialog/help-dialog.component';
import { NICHT_JEDE_AUSSAGE } from '../shared/schreibregeln';
import { ORGANISATION } from '../shared/organisation';

/** Die Über-Seite: wofür Gut gesagt da ist, für wen und wie man mitmacht (docs/VISION.md, #345). */
@Component({
  selector: 'app-about',
  standalone: true,
  imports: [
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

  constructor(private dialog: MatDialog) {}

  openHelpDialog(): void {
    this.dialog.open(HelpDialogComponent, {
      width: '80vw',
      maxWidth: '80vw',
      maxHeight: '80vh'
    });
  }
}
