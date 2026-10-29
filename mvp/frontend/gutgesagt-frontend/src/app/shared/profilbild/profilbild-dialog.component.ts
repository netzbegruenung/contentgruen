import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatDialog, MatDialogConfig, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ProfilbildService } from '../../services/profilbild.service';

/**
 * "Profilbild wählen" aus dem Profilmenü: ein Raster aller 40 Bilder. Echte Radioknöpfe, damit Tab und Pfeiltasten wie gewohnt gehen.
 * Gespeichert wird erst beim Übernehmen (#437).
 */
@Component({
  selector: 'app-profilbild-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  templateUrl: './profilbild-dialog.component.html',
  styleUrls: ['./profilbild-dialog.component.css'],
})
export class ProfilbildDialogComponent {
  readonly auswahl = this.profilbild.auswahl;
  readonly gewaehlt = this.profilbild.gewaehlt;

  /** Vorbelegt mit dem Bild, das gerade im Kopf steht, ob gewählt oder abgeleitet. */
  ausgewaehlt: string | null =
    this.profilbild.gewaehlt() ??
    this.profilbild.auswahl.find((option) => option.url === this.profilbild.bild())?.id ??
    null;

  constructor(
    public dialogRef: MatDialogRef<ProfilbildDialogComponent>,
    private profilbild: ProfilbildService
  ) {}

  uebernehmen(): void {
    if (this.ausgewaehlt) {
      this.profilbild.waehlen(this.ausgewaehlt);
    }
    this.dialogRef.close();
  }

  zuruecksetzen(): void {
    this.profilbild.zuruecksetzen();
    this.dialogRef.close();
  }
}

/**
 * Oeffnet den Dialog so, wie Kopf und Mobil-Menue ihn brauchen. Der Fokus liegt
 * zuerst auf dem Dialog selbst, nicht auf dem gewaehlten Bild: sonst scrollte der
 * Dialog auf schmalen Bildschirmen zu ihm und Ueberschrift und erste Reihen waeren
 * weg. Tab fuehrt von dort zum gewaehlten Radioknopf.
 */
export function profilbildDialogOeffnen(
  dialog: MatDialog,
  konfig: MatDialogConfig = {}
): MatDialogRef<ProfilbildDialogComponent> {
  return dialog.open(ProfilbildDialogComponent, {
    width: '560px',
    maxWidth: '95vw',
    autoFocus: 'dialog',
    ...konfig,
  });
}
