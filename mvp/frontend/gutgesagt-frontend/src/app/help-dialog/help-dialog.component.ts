import { Component } from '@angular/core';
import { NgFor } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { Router, RouterModule } from '@angular/router';
import { CONTENT_TYPE_REGISTRY } from '../shared/content-type-registry';
import { ERFUNDENES_MELDEN, NICHT_JEDE_AUSSAGE, SCHREIBREGELN } from '../shared/schreibregeln';

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
  readonly typen = (['commentary', 'generictext', 'image', 'post'] as const).map((key) => ({
    ...CONTENT_TYPE_REGISTRY[key],
    artikel: key === 'generictext' ? 'eine' : 'ein',
  }));

  // Dieselben Saetze wie in der Formularhilfe
  readonly schreibregeln = SCHREIBREGELN;
  readonly nichtJedeAussage = NICHT_JEDE_AUSSAGE;
  readonly erfundenesMelden = ERFUNDENES_MELDEN;

  constructor(
    private dialogRef: MatDialogRef<HelpDialogComponent>,
    private router: Router
  ) {}

  navigateToAbout(): void {
    this.dialogRef.close();
    this.router.navigate(['/about']);
  }
}

/**
 * Oeffnet die Hilfe als Seitenleiste rechts in voller Hoehe, 560 px breit; schmaler
 * als 560 px wird daraus ein Vollbild (#512). Fokus auf dem Dialog selbst: Sonst
 * fokussierte Material den ersten Link und scrollte ans Ende.
 */
export function hilfeOeffnen(dialog: MatDialog): MatDialogRef<HelpDialogComponent> {
  return dialog.open(HelpDialogComponent, {
    autoFocus: 'dialog',
    position: { top: '0', right: '0' },
    width: '560px',
    maxWidth: '100vw',
    height: '100%',
    maxHeight: '100%',
    panelClass: 'hilfe-seitenleiste',
  });
}
