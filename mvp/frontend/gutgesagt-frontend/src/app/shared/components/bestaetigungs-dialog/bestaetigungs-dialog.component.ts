import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

export interface BestaetigungsDialogDaten {
  titel: string;
  text: string;
  ja: string;
  nein: string;
}

/** Eine Rueckfrage mit zwei Knoepfen; schliesst mit true nur bei "ja". */
@Component({
  standalone: true,
  selector: 'app-bestaetigungs-dialog',
  imports: [MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>{{ daten.titel }}</h2>
    <mat-dialog-content>
      <p>{{ daten.text }}</p>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" [mat-dialog-close]="false">{{ daten.nein }}</button>
      <button mat-flat-button type="button" class="bestaetigen" [mat-dialog-close]="true">{{ daten.ja }}</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .bestaetigen {
      background-color: var(--primary-main);
      color: white;
    }
  `],
})
export class BestaetigungsDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public daten: BestaetigungsDialogDaten) {}
}
