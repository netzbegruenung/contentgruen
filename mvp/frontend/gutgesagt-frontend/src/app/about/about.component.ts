import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { RouterModule } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { HelpDialogComponent } from '../help-dialog/help-dialog.component';

@Component({
  selector: 'app-about',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatDividerModule,
    RouterModule
  ],
  templateUrl: './about.component.html',
  styleUrls: ['./about.component.scss']
})
export class AboutComponent {
  constructor(private dialog: MatDialog) {}

  openHelpDialog(): void {
    this.dialog.open(HelpDialogComponent, {
      width: '80vw',
      maxWidth: '80vw',
      maxHeight: '80vh'
    });
  }
}
