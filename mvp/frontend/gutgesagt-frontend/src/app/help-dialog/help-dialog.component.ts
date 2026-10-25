import { Component } from '@angular/core';
import { NgFor } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { Router, RouterModule } from '@angular/router';
import { CONTENT_TYPE_REGISTRY } from '../shared/content-type-registry';

@Component({
  selector: 'app-help-dialog',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    RouterModule,
    NgFor
  ],
  templateUrl: './help-dialog.component.html',
  styleUrls: ['./help-dialog.component.css']
})
export class HelpDialogComponent {
  readonly typen = (['commentary', 'generictext', 'image'] as const).map((key) => ({
    ...CONTENT_TYPE_REGISTRY[key],
    artikel: key === 'generictext' ? 'eine' : 'ein',
  }));

  constructor(
    private dialogRef: MatDialogRef<HelpDialogComponent>,
    private router: Router
  ) {}

  navigateToAbout(): void {
    this.dialogRef.close();
    this.router.navigate(['/about']);
  }
}
