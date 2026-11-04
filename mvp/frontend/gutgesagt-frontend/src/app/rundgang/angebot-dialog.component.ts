import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { Angebot } from './rundgang-daten';

export type AngebotWahl = 'starten' | 'spaeter';

/**
 * Bietet einen Rundgang an: Willkommen beim ersten Besuch, Mitmachen nach der ersten
 * Anmeldung (#389, Variante B: gelbes Band mit Daumen, zwei gleichwertige
 * Rahmen-Knöpfe). Nichts ist vorbelegt: Der Fokus liegt auf dem Fenster, nicht auf
 * einem Knopf. Escape schließt wie „Später“.
 */
@Component({
  selector: 'app-angebot-dialog',
  standalone: true,
  imports: [MatDialogModule],
  template: `
    <div class="band"><img src="marke/daumen.svg" alt="" width="104" height="104"></div>
    <div class="koerper">
      <h2 id="angebot-titel">{{ angebot.titel }}</h2>
      <p id="angebot-satz" class="satz">{{ angebot.satz }}</p>
      <div class="knoepfe">
        <button type="button" class="rundgang-knopf umriss" [mat-dialog-close]="'starten'">Rundgang starten</button>
        <button type="button" class="rundgang-knopf umriss" [mat-dialog-close]="'spaeter'">Später</button>
      </div>
    </div>
  `,
  styleUrls: ['./rundgang-knoepfe.css', './angebot-dialog.component.css'],
})
export class AngebotDialogComponent {
  readonly angebot = inject<Angebot>(MAT_DIALOG_DATA);
}

export function angebotOeffnen(dialog: MatDialog, angebot: Angebot): MatDialogRef<AngebotDialogComponent, AngebotWahl> {
  return dialog.open<AngebotDialogComponent, Angebot, AngebotWahl>(AngebotDialogComponent, {
    data: angebot,
    autoFocus: 'dialog',
    // Kein Select o. Ae. im Fenster, das sich mit aria-modal stoeren koennte
    ariaModal: true,
    ariaLabelledBy: 'angebot-titel',
    ariaDescribedBy: 'angebot-satz',
    width: '520px',
    maxWidth: 'calc(100vw - 32px)',
    panelClass: 'angebot-fenster',
    backdropClass: 'angebot-schleier',
    // Bleibt offen, wenn die App nach der Anmeldung weiterleitet
    closeOnNavigation: false,
  });
}
