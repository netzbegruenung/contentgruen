import { Component } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { RouterModule } from '@angular/router';
import { HelpDialogComponent } from '../help-dialog/help-dialog.component';

@Component({
  selector: 'app-footer',
  standalone: true,
  imports: [RouterModule],
  templateUrl: './footer.component.html',
  styleUrls: ['./footer.component.css']
})
export class FooterComponent {
  constructor(
    private dialog: MatDialog) {
  }
    openHelpDialog() {
      this.dialog.open(HelpDialogComponent, {
        width: '80vw',
        maxWidth: '80vw',
        data: {} // Pass any data you need here
      });
    }
}
